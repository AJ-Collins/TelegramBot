import os
from dotenv import load_dotenv
import telebot

# Load environment variables from .env file
load_dotenv()

# Get the bot token from the environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Ensure the bot token is loaded
if BOT_TOKEN is None:
    raise ValueError("Bot token is not defined. Please set BOT_TOKEN in your .env file.")

bot = telebot.TeleBot(BOT_TOKEN)

# Create an uploads directory if it doesn't exist
os.makedirs('uploads', exist_ok=True)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Collins, how are you doing?")

@bot.message_handler(func=lambda message: True, content_types=['document'])
def handle_document(message):
    # Check if the uploaded file is a Word document
    if message.document.mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf']:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Save the downloaded file
        file_name = message.document.file_name
        file_path = os.path.join('uploads', file_name)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, f"Received and saved the document: {file_path}")
    else:
        bot.reply_to(message, "Please upload a Word document or PDF.")

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)

bot.infinity_polling()