import asyncio
import logging
import os
from dotenv import load_dotenv
from bot.telegram_scrapper import main as scrapper_main, setup_mongodb
from bot.bot_handler import setup_bot
from telegram import Update

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

async def main():
    # Get the event loop
    loop = asyncio.get_running_loop()
    telegram_client = None
    application = None

    try:
        logger.info("Starting Telegram data collection bot...")
        
        # Verify MongoDB connection first
        messages_collection, metadata_collection = setup_mongodb()
        if not messages_collection or not metadata_collection:
            raise RuntimeError("Failed to connect to MongoDB")
        
        # Setup and start the bot first
        application = await setup_bot()
        await application.initialize()
        await application.start()
        
        # Start the scraper in background
        telegram_client = await scrapper_main(loop)
        
        # Run the bot's polling in the main thread
        logger.info("Bot is ready to receive commands!")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error in main process: {e}", exc_info=True)
    finally:
        # Cleanup in reverse order
        if telegram_client:
            try:
                await telegram_client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting Telegram client: {e}")
        
        if application:
            try:
                await application.stop()
            except Exception as e:
                logger.error(f"Error stopping application: {e}")

if __name__ == "__main__":
    # Force cleanup of any existing session files before starting
    asyncio.run(main())
