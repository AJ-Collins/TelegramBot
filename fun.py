import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the bot token from the environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Ensure the bot token is loaded
if BOT_TOKEN is None:
    raise ValueError("Bot token is not defined. Please set BOT_TOKEN in your .env file.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Create an uploads directory if it doesn't exist
os.makedirs('uploads', exist_ok=True)

# Dictionary to keep track of user states
user_states = {}

# Helper function to create the custom keyboard
def create_initial_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("/start"), KeyboardButton("/help"))
    return keyboard

def create_region_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("\U0001F30D Turnitin Intl"))
    return keyboard

def create_yesNo_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("YES"), KeyboardButton("NO"))
    return keyboard

# Command handler for /help
@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    help_text = (
        "Here are the commands you can use:\n"
        "/start - Start the bot\n"
        "/help - Get help information\n"
        "/menu - Display menu\n"
        "Upload a Word or PDF document for processing.\n"
        "For other queries, just send a message and I'll reply!"
    )
    await message.answer(help_text, reply_markup=create_initial_keyboard())

# Handler for text messages
@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text.lower().strip()

    # Initialize user state if not present
    if user_id not in user_states:
        user_states[user_id] = {"step": None}

    # Handle /start command
    if text == "/start":
        user_states[user_id]["step"] = "start"
        await message.reply("Your Subscription Region:\n Please select your region:", reply_markup=create_region_keyboard())
    
    # Handle region selection
    elif text == "\U0001F30D turnitin intl":
        user_states[user_id]["step"] = "include_quotes_prompt"
        await message.reply("Include Quotes?", reply_markup=create_yesNo_keyboard())
    
    # Handle yes or no responses for quotes inclusion
    elif text == "yes":
        user_states[user_id]["include_quotes"] = True
        user_states[user_id]["step"] = "exclude_titles_prompt"
        await message.reply("Exclude Titles?", reply_markup=create_yesNo_keyboard())
    
    elif text == "no":
        user_states[user_id]["include_quotes"] = False
        user_states[user_id]["step"] = "exclude_titles_prompt"
        await message.reply("Exclude Titles?", reply_markup=create_yesNo_keyboard())
    
    elif text == "yes":
        user_states[user_id]["exclude_titles"] = True
        user_states[user_id]["step"] = "ready_for_document"
        await message.reply("You selected YES. Please upload your document.")
    
    elif text == "no":
        user_states[user_id]["exclude_titles"] = False
        user_states[user_id]["step"] = "ready_for_document"
        await message.reply("You selected NO. Please upload your document.")
    
    # Handle help command
    elif text == "help":
        help_text = (
            "Here are the commands you can use:\n"
            "/start - Start the bot\n"
            "/help - Get help information\n"
            "/menu - Display menu\n"
            "Upload a Word or PDF document for processing.\n"
            "For other queries, just send a message and I'll reply!"
        )
        await message.reply(help_text, reply_markup=create_initial_keyboard())
        
    else:
        await message.reply(f"You said: {message.text}")

# Handler for documents
async def handle_document(message: types.Message, user_id: int):
    try:
        if message.document.mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf']:
            file_info = await bot.get_file(message.document.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            # Save the downloaded file
            file_name = message.document.file_name
            file_path = os.path.join('uploads', file_name)
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            await message.reply(message, f"Received and saved the document: {file_path}")
        else:
            await message.reply("Unsupported file type. Please upload a Word document or PDF.")
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await message.reply("An error occurred while processing your document. Please try again.")

async def on_startup(dp: Dispatcher):
    logging.info("Starting bot...")
    
    # Set custom bot commands with descriptions
    commands = [
        {"command": "start", "description": "Start the bot"},
        {"command": "help", "description": "Help on use"}
    ]
    await bot.set_my_commands([types.BotCommand(command['command'], command['description']) for command in commands])

# Start polling
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)