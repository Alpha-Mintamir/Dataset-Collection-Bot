from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import logging
import os
from .telegram_scrapper import start_channel_scraping, stop_channel_scraping, get_channel_stats

logger = logging.getLogger(__name__)

# Store user states
user_states = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user = update.message.from_user
    logger.info(f"User {user.id} started the bot")
    welcome_message = (
        f"👋 Hi {user.first_name}!\n\n"
        "I'm an Amharic Dataset Collector Bot. I can help you collect messages "
        "from Telegram channels for research purposes.\n\n"
        "Available commands:\n"
        "🔹 /add_channel - Add a new channel to scrape\n"
        "🔹 /list_channels - List all channels being scraped\n"
        "🔹 /stats - Get statistics for scraped channels\n"
        "🔹 /stop_channel - Stop scraping a channel\n"
        "🔹 /help - Show this help message"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    help_text = (
        "Here's how to use me:\n\n"
        "1️⃣ /add_channel - Start scraping a new channel\n"
        "   • Send the channel username (e.g., @channel)\n"
        "   • I'll join and start collecting messages\n\n"
        "2️⃣ /list_channels - See all channels I'm scraping\n"
        "   • View active channels\n"
        "   • Check collection status\n\n"
        "3️⃣ /stats - Get collection statistics\n"
        "   • Total messages collected\n"
        "   • Messages per channel\n"
        "   • Last update time\n\n"
        "4️⃣ /stop_channel - Stop scraping a channel\n"
        "   • Choose which channel to stop\n"
        "   • Data remains stored\n\n"
        "5️⃣ /help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /add_channel command"""
    user_states[update.effective_user.id] = "waiting_for_channel"
    await update.message.reply_text(
        "Please send me the channel username you want to scrape.\n"
        "Format: @channelname\n\n"
        "Make sure:\n"
        "✓ The channel is public\n"
        "✓ The username starts with @\n"
        "✓ You have the correct username"
    )

async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle channel username input"""
    user_id = update.effective_user.id
    if user_id in user_states and user_states[user_id] == "waiting_for_channel":
        channel_username = update.message.text.strip()
        
        if not channel_username.startswith('@'):
            await update.message.reply_text(
                "❌ Channel username must start with @\n"
                "Please try again with the correct format (e.g., @channelname)"
            )
            return

        # Show processing message
        processing_msg = await update.message.reply_text(
            "🔄 Processing your request...\n"
            "• Verifying channel...\n"
            "• Attempting to join...\n"
            "• Setting up scraping..."
        )

        try:
            success = await start_channel_scraping(channel_username)
            if success:
                await processing_msg.edit_text(
                    f"✅ Successfully added {channel_username}!\n\n"
                    "I will now collect:\n"
                    "📝 All historical messages\n"
                    "🔄 Any new messages\n\n"
                    "Use /stats to check collection progress."
                )
            else:
                await processing_msg.edit_text(
                    f"❌ Failed to add {channel_username}\n"
                    "Please check:\n"
                    "• Channel exists and is public\n"
                    "• You provided the correct username\n"
                    "• The channel has messages"
                )
        except Exception as e:
            await processing_msg.edit_text(
                f"❌ Error: {str(e)}\n"
                "Please try again later or contact support."
            )
        
        # Clear user state
        del user_states[user_id]

async def list_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /list_channels command"""
    channels = await get_channel_stats()
    
    if not channels:
        await update.message.reply_text(
            "📝 No channels are currently being scraped.\n"
            "Use /add_channel to start collecting data!"
        )
        return

    message = "📊 Currently scraping these channels:\n\n"
    for channel in channels:
        message += (
            f"📌 {channel['username']}\n"
            f"   • Messages: {channel['message_count']}\n"
            f"   • Last update: {channel['last_update']}\n\n"
        )
    
    await update.message.reply_text(message)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /stats command"""
    stats = await get_channel_stats()
    
    if not stats:
        await update.message.reply_text(
            "📊 No statistics available.\n"
            "Start collecting data with /add_channel!"
        )
        return

    total_messages = sum(channel['message_count'] for channel in stats)
    message = "📊 Collection Statistics\n\n"
    message += f"📑 Total Messages: {total_messages}\n\n"
    message += "By Channel:\n"
    
    for channel in stats:
        message += (
            f"🔹 {channel['username']}\n"
            f"   • Messages: {channel['message_count']}\n"
            f"   • Last Update: {channel['last_update']}\n\n"
        )
    
    await update.message.reply_text(message)

async def stop_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /stop_channel command"""
    channels = await get_channel_stats()
    
    if not channels:
        await update.message.reply_text(
            "❌ No channels are currently being scraped.\n"
            "Use /add_channel to start collecting data!"
        )
        return

    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(
            channel['username'], 
            callback_data=f"stop_{channel['username']}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select a channel to stop scraping:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('stop_'):
        channel = query.data[5:]  # Remove 'stop_' prefix
        success = await stop_channel_scraping(channel)
        
        if success:
            await query.edit_message_text(
                f"✅ Stopped scraping {channel}\n"
                "Data collected so far remains stored in the database."
            )
        else:
            await query.edit_message_text(
                f"❌ Failed to stop scraping {channel}\n"
                "Please try again or contact support."
            )

async def setup_bot():
    """Initialize and configure the bot"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_channel", add_channel_command))
    application.add_handler(CommandHandler("list_channels", list_channels_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("stop_channel", stop_channel_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for channel input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))

    return application 