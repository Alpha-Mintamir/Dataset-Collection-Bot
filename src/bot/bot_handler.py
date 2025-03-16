from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import os

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user = update.message.from_user
    logger.info(f"User {user.id} started the bot")
    welcome_message = (
        f"👋 Hi {user.first_name}!\n\n"
        "I'm a Telegram data collection bot. I can help you collect messages "
        "from various Telegram channels.\n\n"
        "Use /help to see available commands."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    help_text = (
        "Available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def setup_bot():
    """Initialize and configure the bot"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    return application 