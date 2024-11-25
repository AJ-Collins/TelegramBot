import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from docx import Document
import fitz  # PyMuPDF
import shutil

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

# Dictionary to keep track of user states and document IDs
user_states = {}
user_documents = {}

# Initialize document ID counter file
COUNTER_FILE = 'uploads/counter.txt'

# Function to get the next document ID
def get_next_document_id():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, 'w') as f:
            f.write('1')
        return 1
    with open(COUNTER_FILE, 'r') as f:
        count = int(f.read().strip())
    count += 1
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(count))
    return count

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

def count_words_in_docx(file_path):
    """Counts the number of words in a DOCX file."""
    doc = Document(file_path)
    word_count = 0
    for para in doc.paragraphs:
        word_count += len(para.text.split())
    return word_count

def count_words_in_pdf(file_path):
    """Counts the number of words in a PDF file."""
    doc = fitz.open(file_path)
    word_count = 0
    for page in doc:
        text = page.get_text()
        word_count += len(text.split())
    return word_count

def count_words(file_path):
    """Determines the file type and counts words accordingly."""
    if file_path.endswith('.docx'):
        return count_words_in_docx(file_path)
    elif file_path.endswith('.pdf'):
        return count_words_in_pdf(file_path)
    else:
        raise ValueError("Unsupported file type. Please upload a DOCX or PDF file.")

# Command handler for /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"step": "start"}
    await message.reply("Enter your subscription region:", reply_markup=create_region_keyboard())

# Command handler for /help
@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {}).get("step")
    await message.reply("Help information provided. You can now select an option:", reply_markup=create_region_keyboard())

# Command handler for region selection
@dp.message_handler(lambda message: message.text.lower() == "\U0001F30D turnitin intl")
async def handle_region(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {}).get("step")

    if state == "start":
        user_states[user_id]["step"] = "bibliography_prompt"
        await message.reply("Do you want to exclude Bibliography?", reply_markup=create_yesNo_keyboard())
    else:
        await message.reply("Please follow the correct sequence: /start, /help, then select your region.")

# Handler for YES response for Bibliography
@dp.message_handler(lambda message: message.text.lower() == "yes")
async def handle_bibliography_yes(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {}).get("step")

    if state == "bibliography_prompt":
        user_states[user_id]["step"] = "quotes_prompt"
        await message.reply("Do you want to exclude Quotes?", reply_markup=create_yesNo_keyboard())
    elif state == "quotes_prompt":
        user_states[user_id]["step"] = "ready_for_document"
        await message.reply("You have chosen to exclude both Bibliography and Quotes. Please upload your document.")
    else:
        await message.reply("Unexpected state. Please follow the correct sequence.")

# Handler for NO response for Bibliography
@dp.message_handler(lambda message: message.text.lower() == "no")
async def handle_bibliography_no(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {}).get("step")

    if state == "bibliography_prompt":
        user_states[user_id]["step"] = "quotes_prompt"
        await message.reply("Do you want to exclude Quotes?", reply_markup=create_yesNo_keyboard())
    elif state == "quotes_prompt":
        user_states[user_id]["step"] = "ready_for_document"
        await message.reply("You have chosen to include Bibliography but exclude Quotes. Please upload your document.")
    else:
        await message.reply("Unexpected state. Please follow the correct sequence.")

# Handler for document submissions
@dp.message_handler(content_types=['document'])
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {}).get("step")

    if state == "ready_for_document":
        try:
            mime_type = message.document.mime_type
            if mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf']:
                file_info = await bot.get_file(message.document.file_id)
                file_path = file_info.file_path
                downloaded_file = await bot.download_file(file_path)

                # Generate a unique ID for the document
                document_id = get_next_document_id()
                file_name = f"{document_id}_{message.document.file_name}"
                file_save_path = os.path.join('uploads', file_name)

                # Save the user's document with the unique ID
                with open(file_save_path, 'wb') as new_file:
                    new_file.write(downloaded_file.getvalue())

                # Count words in the document
                word_count = count_words(file_save_path)

                # Define the name of the PDF document to send back
                response_file_name = "response.pdf"  # Ensure this is the correct file name for the response
                response_file_path = os.path.join('uploads', response_file_name)

                # Prepare the response message
                message_text = f"#Submitted\n#Turnitin Intl\nDocument ID: {document_id}\nFile name: {file_name}\nWord count: {word_count}"
                
                if os.path.exists(response_file_path):
                    message_text += "\nFile available ⬇️"
                else:
                    message_text += "\nThe document to send back is not available ❌"

                await message.reply(message_text)

                # Send the document back if it exists
                if os.path.exists(response_file_path):
                    # Create a temporary file with the document ID in its name
                    temp_response_file_name = f"{document_id}_response.pdf"
                    temp_response_file_path = os.path.join('uploads', temp_response_file_name)
                    
                    # Copy the response file to the new temporary file path
                    shutil.copy(response_file_path, temp_response_file_path)
    
                    # Open and send the new temporary file
                    with open(temp_response_file_path, 'rb') as response_file:
                        await bot.send_document(user_id, response_file, caption=f"Here is the document you requested with ID {document_id}.")
    
                    # Clean up the temporary file after sending
                    os.remove(temp_response_file_path)
                
            else:
                await message.reply("Unsupported file type. Please upload a Word document or PDF.")
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await message.reply("An error occurred while processing your document. Please try again.")
    else:
        await message.reply("You need to follow the correct sequence before uploading a document.")

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