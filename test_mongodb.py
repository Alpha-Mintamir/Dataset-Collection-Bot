from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

def test_mongodb_connection():
    uri = os.getenv('MONGODB_URI')
    print(f"Testing connection to MongoDB...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Test the connection
        client.admin.command('ping')
        print("MongoDB connection successful!")
        
        # Test database access
        db = client['telegram_data']
        collections = db.list_collection_names()
        print(f"Available collections: {collections}")
        
    except Exception as e:
        print(f"MongoDB connection failed: {str(e)}")
        if "bad auth" in str(e).lower():
            print("\nAuthentication failed. Please check:")
            print("1. Username and password are correct")
            print("2. IP address is whitelisted in MongoDB Atlas")
            print("3. Database user has correct permissions")

if __name__ == "__main__":
    test_mongodb_connection() 