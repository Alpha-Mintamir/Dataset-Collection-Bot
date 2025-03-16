from telethon import TelegramClient, events
import os
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Load environment variables
load_dotenv(dotenv_path='../../.env')
print("Environment variables:")
print(os.environ.get('TG_API_ID'))
print(os.environ.get('TG_API_HASH'))
print(os.environ.get('PHONE'))

api_id = int(os.getenv('TG_API_ID'))
api_hash = os.getenv('TG_API_HASH')
phone = os.getenv('PHONE')

print(f"API ID: {api_id}")
print(f"API Hash: {api_hash}")
print(f"Phone: {phone}")

# MongoDB setup with error handling
def setup_mongodb():
    try:
        # Get MongoDB URI from environment
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables")
            
        print(f"Connecting to MongoDB...")
        client_mongo = MongoClient(mongodb_uri, 
                                 serverSelectionTimeoutMS=5000,
                                 connectTimeoutMS=5000,
                                 retryWrites=True)
        
        # Test connection
        client_mongo.admin.command('ping')
        
        db = client_mongo['telegram_data']
        messages_collection = db['messages']
        metadata_collection = db['metadata']
        
        print("Successfully connected to MongoDB")
        return messages_collection, metadata_collection
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        if "bad auth" in str(e).lower():
            print("Authentication failed. Please check your MongoDB username and password.")
        return None, None

# Initialize MongoDB collections
messages_collection, metadata_collection = setup_mongodb()

# Initialize the Telegram client
client = TelegramClient('scraping_session', api_id, api_hash)

def cleanup_session_file():
    """Clean up any existing session files"""
    session_files = [
        'scraping_session.session',
        'scraping_session.session-journal'
    ]
    for file in session_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            print(f"Error cleaning up {file}: {e}")

async def join_channel(channel_username):
    """Join a channel if not already joined"""
    try:
        entity = await client.get_entity(channel_username)
        # Check if we're already in the channel
        participant = await client.get_participants(entity, limit=1)
        print(f"Already a member of {channel_username}")
        return entity
    except Exception as e:
        try:
            # Try to join the channel
            await client(JoinChannelRequest(channel_username))
            print(f"Successfully joined {channel_username}")
            return await client.get_entity(channel_username)
        except Exception as join_error:
            print(f"Failed to join {channel_username}: {join_error}")
            return None

async def get_last_message_id(channel_username):
    """Get the last processed message ID from metadata collection"""
    metadata = metadata_collection.find_one({"channel_username": channel_username})
    if metadata:
        return metadata.get("last_message_id", 0)
    return 0

async def update_metadata(channel_username, last_message_id, last_timestamp):
    """Update metadata with the last processed message"""
    metadata_collection.update_one(
        {"channel_username": channel_username},
        {"$set": {
            "last_message_id": last_message_id,
            "last_timestamp": last_timestamp,
            "last_updated": datetime.now()
        }},
        upsert=True
    )

async def extract_historical_messages(channel_username):
    """Extract all historical messages from a channel"""
    entity = await client.get_entity(channel_username)
    channel_title = entity.title
    
    # Get the last processed message ID
    last_message_id = await get_last_message_id(channel_username)
    print(f"Starting extraction from message ID: {last_message_id}")
    
    # Extract messages
    message_count = 0
    last_timestamp = None
    
    async for message in client.iter_messages(entity, min_id=last_message_id):
        if message.message:  # Only process messages with text content
            # Store message in MongoDB
            message_data = {
                "channel_name": channel_title,
                "channel_username": channel_username,
                "message_id": message.id,
                "timestamp": message.date,
                "sender": str(message.sender_id) if message.sender_id else None,
                "text": message.message
            }
            
            # Insert or update the message in MongoDB
            messages_collection.update_one(
                {"channel_username": channel_username, "message_id": message.id},
                {"$set": message_data},
                upsert=True
            )
            
            message_count += 1
            last_timestamp = message.date
            
            # Update the last message ID
            if message.id > last_message_id:
                last_message_id = message.id
    
    # Update metadata with the last processed message
    if last_timestamp:
        await update_metadata(channel_username, last_message_id, last_timestamp)
    
    print(f"Extracted {message_count} historical messages from {channel_username}")
    return last_message_id

async def setup_long_polling(channel_username):
    """Set up long polling for new messages"""
    @client.on(events.NewMessage(chats=channel_username))
    async def handler(event):
        message = event.message
        if message.message:  # Only process messages with text content
            entity = await client.get_entity(channel_username)
            channel_title = entity.title
            
            # Store message in MongoDB
            message_data = {
                "channel_name": channel_title,
                "channel_username": channel_username,
                "message_id": message.id,
                "timestamp": message.date,
                "sender": str(message.sender_id) if message.sender_id else None,
                "text": message.message
            }
            
            # Insert or update the message in MongoDB
            messages_collection.update_one(
                {"channel_username": channel_username, "message_id": message.id},
                {"$set": message_data},
                upsert=True
            )
            
            # Update metadata
            await update_metadata(channel_username, message.id, message.date)
            
            print(f"New message received from {channel_username}: {message.id}")

async def process_channel(channel_username):
    """Process a channel: join, extract historical data, and set up long polling"""
    # Join the channel if not already joined
    entity = await join_channel(channel_username)
    if not entity:
        print(f"Failed to process {channel_username}")
        return
    
    # Extract historical messages
    await extract_historical_messages(channel_username)
    
    # Set up long polling for new messages
    await setup_long_polling(channel_username)
    print(f"Now listening for new messages in {channel_username}")

async def main(loop=None):
    """Main function to run the scraper"""
    # Verify MongoDB connection
    if not messages_collection or not metadata_collection:
        raise RuntimeError("Failed to connect to MongoDB. Please check your connection string and ensure MongoDB is running.")
    
    # Clean up any existing session files
    cleanup_session_file()
    
    # Use the provided event loop or get the current one
    if loop is None:
        loop = asyncio.get_event_loop()
    
    try:
        # Initialize the client with the specific loop
        client = TelegramClient('scraping_session', api_id, api_hash, loop=loop)
        await client.start(phone)  # Add phone parameter here
        
        if not await client.is_user_authorized():
            print("You need to authorize this script to access your Telegram account.")
            await client.send_code_request(phone)
            code = input('Enter the code you received: ')
            await client.sign_in(phone, code)
        
        # List of channels to process
        channels = [
            '@sinayelj'
            # Add more channels here
        ]
        
        # Process each channel
        for channel in channels:
            await process_channel(channel)
        
        # Keep the client running
        print("Scraper is now running and listening for new messages...")
        return client
    except Exception as e:
        print(f"Error in scraper: {e}")
        if 'client' in locals():
            await client.disconnect()
        raise

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
