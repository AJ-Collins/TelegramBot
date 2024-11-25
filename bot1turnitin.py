import os
from dotenv import load_dotenv
import telebot
import requests

# Load environment variables from .env file
load_dotenv()

# Get the bot token from the environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
TURNITIN_API_KEY = os.getenv('TURNITIN_API_KEY')
TURNITIN_API_URL = os.getenv('TURNITIN_API_URL')  # Base URL for Turnitin API

# Ensure the bot token is loaded
if BOT_TOKEN is None:
    raise ValueError("Bot token is not defined. Please set BOT_TOKEN in your .env file.")

# Ensure Turnitin credentials are loaded
if TURNITIN_API_KEY is None or TURNITIN_API_URL is None:
    raise ValueError("Turnitin API credentials are not defined. Please set TURNITIN_API_KEY and TURNITIN_API_URL in your .env file.")

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Collins, how are you doing?")

@bot.message_handler(func=lambda message: True, content_types=['document'])
def handle_document(message):
    # Check if the uploaded file is a Word document
    if message.document.mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Save the downloaded file
        file_name = message.document.file_name
        file_path = os.path.join('uploads', file_name)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, f"Received and saved the document: {file_path}")

        # Upload the document to Turnitin and check for plagiarism
        try:
            report_url = check_plagiarism_with_turnitin(file_path)
            bot.reply_to(message, f"Turnitin Report URL: {report_url}")
        except Exception as e:
            bot.reply_to(message, f"Failed to check the document: {str(e)}")
    else:
        bot.reply_to(message, "Please upload a Word document.")

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)

def check_plagiarism_with_turnitin(file_path):
    headers = {
        'Authorization': f'Bearer {TURNITIN_API_KEY}',
        'Content-Type': 'application/json'
    }

    # Upload the file to Turnitin
    with open(file_path, 'rb') as file:
        response = requests.post(f'{TURNITIN_API_URL}/uploads', headers=headers, files={'file': file})

    if response.status_code != 200:
        raise Exception(f"Failed to upload document: {response.text}")

    submission_id = response.json().get('submission_id')

    # Check plagiarism report status
    report_url = None
    while not report_url:
        response = requests.get(f'{TURNITIN_API_URL}/submissions/{submission_id}/report', headers=headers)
        if response.status_code == 200:
            report_url = response.json().get('report_url')
        elif response.status_code == 202:  # 202 Accepted means the report is still being generated
            time.sleep(5)  # Wait for a few seconds before checking again
        else:
            raise Exception(f"Failed to retrieve report: {response.text}")

    return report_url

bot.infinity_polling()
