# Telegram Dataset Collector Bot

A Telegram bot designed to collect and store messages from Amharic Telegram channels into a MongoDB database. This bot is specifically built to create datasets for Amharic language processing, research, and analysis purposes.

## Features

- 🤖 Automated message collection from Amharic Telegram channels
- 📊 Stores messages in MongoDB for easy access and analysis
- 🔄 Real-time updates through long polling
- 📱 Supports both historical message extraction and new message collection
- 🔐 Secure authentication with Telegram and MongoDB
- 🌍 Focused on Amharic language content

## Prerequisites

- Python 3.8 or higher
- MongoDB Atlas account
- Telegram API credentials
- Active Telegram account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Alpha-mintamir/Dataset_Collector_bot.git
cd Dataset_Collector_bot
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your credentials:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash
PHONE=your_phone_number
MONGODB_URI=your_mongodb_uri
```

## Configuration

### Telegram Setup
1. Get your Telegram API credentials:
   - Visit https://my.telegram.org/auth
   - Create a new application
   - Note down the `api_id` and `api_hash`

2. Create a Telegram bot:
   - Talk to [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot and get the bot token

### MongoDB Setup
1. Create a MongoDB Atlas account
2. Create a new cluster
3. Set up database access (username and password)
4. Whitelist your IP address
5. Get your MongoDB connection string

## Usage

1. Start the bot:
```bash
python src/main.py
```

2. The bot will:
   - Connect to MongoDB
   - Authenticate with Telegram
   - Start collecting messages from specified Amharic channels
   - Listen for new messages in real-time

3. Available bot commands:
   - `/start` - Start the bot
   - `/help` - Show help message

## Project Structure

```
Dataset_Collector_bot/
├── src/
│   ├── bot/
│   │   ├── telegram_scrapper.py  # Handles message collection
│   │   └── bot_handler.py       # Manages bot commands
│   └── main.py                  # Entry point
├── requirements.txt
├── .env
└── README.md
```

## Data Collection

The bot collects the following data from messages:
- Channel name
- Channel username
- Message ID
- Timestamp
- Sender ID (if available)
- Message text (focusing on Amharic content)

Data is stored in two MongoDB collections:
- `messages`: Stores the actual message data
- `metadata`: Stores processing metadata and tracking information

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) for the Telegram client
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for bot functionality
- [PyMongo](https://github.com/mongodb/mongo-python-driver) for MongoDB integration

## Support

For support, please open an issue in the [GitHub repository](https://github.com/Alpha-mintamir/Dataset_Collector_bot) or contact the maintainer [@Alpha-mintamir](https://github.com/Alpha-mintamir).

## Author

- **Alpha Mintamir** - [GitHub](https://github.com/Alpha-mintamir)