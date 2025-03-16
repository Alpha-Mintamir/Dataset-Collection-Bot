import asyncio
import logging
import os
from dotenv import load_dotenv
from bot.telegram_scrapper import main as scrapper_main, setup_mongodb
from bot.bot_handler import setup_bot
from telegram import Update
from telegram.ext import Application

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables at the entry point
load_dotenv()

async def run_bot_and_scraper():
    """Run both the bot and scraper together"""
    # Get the event loop
    loop = asyncio.get_running_loop()
    telegram_client = None
    application = None

    try:
        logger.info("Starting Telegram data collection bot...")
        
        # Verify MongoDB connection first
        messages_collection, metadata_collection, mongo_client = setup_mongodb()
        if messages_collection is None or metadata_collection is None or mongo_client is None:
            raise RuntimeError("Failed to connect to MongoDB")
        
        # Start the scraper first
        telegram_client = await scrapper_main(loop)
        
        # Setup the bot
        application = await setup_bot()
        
        # Start the bot
        await application.initialize()
        await application.start()
        
        # Start the bot's polling in the background
        async def run_polling():
            try:
                await application.updater.start_polling(drop_pending_updates=True)
            except Exception as e:
                logger.error(f"Polling error: {e}")
        
        polling_task = asyncio.create_task(run_polling())
        
        logger.info("Bot is ready to receive commands!")
        
        # Keep the script running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in main process: {e}", exc_info=True)
    finally:
        # Cleanup
        if application:
            try:
                await application.stop()
            except Exception as e:
                logger.error(f"Error stopping application: {e}")
        
        if telegram_client:
            try:
                await telegram_client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting Telegram client: {e}")
        
        # Close MongoDB connection
        if 'mongo_client' in locals() and mongo_client:
            mongo_client.close()

def main():
    """Entry point"""
    try:
        asyncio.run(run_bot_and_scraper())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
