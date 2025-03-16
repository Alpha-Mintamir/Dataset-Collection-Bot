from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
import os
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import logging

# Configure logger
logger = logging.getLogger(__name__)

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
            
        logger.info("Connecting to MongoDB...")
        client_mongo = MongoClient(mongodb_uri, 
                                 serverSelectionTimeoutMS=5000,
                                 connectTimeoutMS=5000,
                                 retryWrites=True)
        
        # Test connection
        client_mongo.admin.command('ping')
        
        db = client_mongo['telegram_data']
        messages_collection = db['messages']
        metadata_collection = db['metadata']
        
        logger.info("Successfully connected to MongoDB")
        return messages_collection, metadata_collection, client_mongo
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        if "bad auth" in str(e).lower():
            logger.error("Authentication failed. Please check your MongoDB username and password.")
        return None, None, None

# Initialize MongoDB collections and client
messages_collection, metadata_collection, client_mongo = setup_mongodb()

# Initialize the Telegram client
client = TelegramClient('scraping_session', api_id, api_hash)

# Store active channels and their handlers
active_channels = {}

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
    if channel_username not in active_channels:
        return
        
    entity = active_channels[channel_username]['entity']
    collection = active_channels[channel_username]['collection']
    
    message_count = 0
    last_message_id = 0
    
    async for message in client.iter_messages(entity):
        if message.message:  # Only process messages with text content
            message_data = {
                "message_id": message.id,
                "timestamp": message.date,
                "sender_id": str(message.sender_id) if message.sender_id else None,
                "text": message.message
            }
            
            # Insert or update the message (using synchronous operation)
            collection.update_one(
                {"message_id": message.id},
                {"$set": message_data},
                upsert=True
            )
            
            message_count += 1
            last_message_id = max(last_message_id, message.id)
    
    logger.info(f"Extracted {message_count} historical messages from {channel_username}")

async def setup_long_polling(channel_username):
    """Set up long polling for new messages"""
    if channel_username not in active_channels:
        return None
        
    collection = active_channels[channel_username]['collection']
    
    async def handler(event):
        message = event.message
        if message.message:  # Only process messages with text content
            message_data = {
                "message_id": message.id,
                "timestamp": message.date,
                "sender_id": str(message.sender_id) if message.sender_id else None,
                "text": message.message
            }
            
            # Insert or update the message (using synchronous operation)
            collection.update_one(
                {"message_id": message.id},
                {"$set": message_data},
                upsert=True
            )
            
            logger.info(f"New message received from {channel_username}: {message.id}")
    
    client.add_event_handler(handler, events.NewMessage(chats=channel_username))
    return handler

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
    global client
    
    if messages_collection is None or metadata_collection is None:
        raise RuntimeError("Failed to connect to MongoDB. Please check your connection string and ensure MongoDB is running.")
    
    cleanup_session_file()
    
    try:
        # Initialize the client with the specific loop
        client = TelegramClient('scraping_session', api_id, api_hash, loop=loop)
        await client.start(phone)
        
        if not await client.is_user_authorized():
            print("You need to authorize this script to access your Telegram account.")
            await client.send_code_request(phone)
            code = input('Enter the code you received: ')
            await client.sign_in(phone, code)
        
        channels = [
            '@sinayelj'
            # Add more channels here
        ]
        
        # Process each channel
        for channel in channels:
            await process_channel(channel)
        
        print("Scraper is now running and listening for new messages...")
        return client
    except Exception as e:
        print(f"Error in scraper: {e}")
        if 'client' in locals():
            await client.disconnect()
        raise

async def start_channel_scraping(channel_username: str) -> bool:
    """Start scraping a new channel"""
    try:
        if channel_username in active_channels:
            return True  # Already scraping this channel
        
        # Join the channel
        entity = await join_channel(channel_username)
        if not entity:
            return False
        
        # Create collection for this channel
        if client_mongo is None:
            raise RuntimeError("MongoDB client is not initialized")
            
        db = client_mongo['telegram_data']
        channel_collection = db[f"messages_{channel_username.replace('@', '')}"]
        
        # Store channel info
        active_channels[channel_username] = {
            'collection': channel_collection,
            'entity': entity,
            'handler': None
        }
        
        # Extract historical messages
        await extract_historical_messages(channel_username)
        
        # Set up long polling
        handler = await setup_long_polling(channel_username)
        active_channels[channel_username]['handler'] = handler
        
        logger.info(f"Successfully started scraping {channel_username}")
        return True
    except Exception as e:
        logger.error(f"Error starting channel scraping: {str(e)}")
        return False

async def stop_channel_scraping(channel_username: str) -> bool:
    """Stop scraping a channel"""
    try:
        if channel_username not in active_channels:
            return True  # Already not scraping
            
        # Remove event handler
        handler = active_channels[channel_username]['handler']
        if handler:
            client.remove_event_handler(handler)
        
        # Remove from active channels
        del active_channels[channel_username]
        return True
    except Exception as e:
        logger.error(f"Error stopping channel scraping: {e}")
        return False

async def get_channel_stats():
    """Get statistics for all channels"""
    stats = []
    for channel_username, info in active_channels.items():
        collection = info['collection']
        # Use synchronous operations
        message_count = collection.count_documents({})
        last_message = collection.find_one(
            sort=[('timestamp', -1)]
        )
        
        stats.append({
            'username': channel_username,
            'message_count': message_count,
            'last_update': last_message['timestamp'] if last_message else 'Never'
        })
    
    return stats
