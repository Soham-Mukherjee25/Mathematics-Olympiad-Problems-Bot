import os
import random
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration ---
app = Flask(__name__)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Token from Vercel Environment Variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Validation
if not TELEGRAM_TOKEN:
    logger.critical("Error: TELEGRAM_TOKEN is missing!")

# --- File System Fix for Vercel ---
# This ensures we find the 'problems' folder correctly on Vercel's server
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS_DIR = os.path.join(BASE_DIR, 'problems')

# --- Bot Logic ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "Welcome to the Mathematics Olympiad Problems Bot!\n\n"
        "**Available Commands:**\n"
        "/rmo   - Regional Mathematics Olympiad\n"
        "/inmo  - Indian National Mathematics Olympiad\n"
        "/aime  - American Invitational Mathematics Examination\n"
        "/amc10 - American Math Comp 10\n"
        "/amc12 - American Math Comp 12\n"
        "/usamo - USA Math Olympiad\n"
        "/imo   - Int. Math Olympiad"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def send_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return
    
    try:
        # Extract exam name from command (e.g., /rmo -> rmo)
        command_text = update.message.text.split(' ')[0]      
        command_no_slash = command_text.lstrip('/')           
        exam_type = command_no_slash.split('@')[0]            
        
        exam_folder = os.path.join(PROBLEMS_DIR, exam_type)

        if not os.path.exists(exam_folder):
            await update.message.reply_text(f"Setup Error: Folder '{exam_type}' not found.")
            return

        question_files = [f for f in os.listdir(exam_folder) if not f.startswith('.')]
        
        if not question_files:
            await update.message.reply_text(f"No problems found in {exam_type.upper()}.")
            return

        random_question_file = random.choice(question_files)
        file_path = os.path.join(exam_folder, random_question_file)

        await update.message.reply_photo(
            photo=open(file_path, 'rb'),
            caption=f"Here is your {exam_type.upper()} problem."
        )

    except Exception as e:
        logger.error(f"Error sending problem: {e}")
        await update.message.reply_text("An error occurred. Please try again.")

# --- Build the Bot ---
# Initialize one global application instance
ptb_application = Application.builder().token(TELEGRAM_TOKEN).build()

ptb_application.add_handler(CommandHandler("start", start))

problem_commands = ["rmo", "inmo", "amc8", "amc10", "amc12", "aime", "usamo", "imo"]
for cmd in problem_commands:
    ptb_application.add_handler(CommandHandler(cmd, send_problem))

# --- Flask Webhook Route ---
# This is the entry point Vercel hits when Telegram sends a message

@app.route("/", methods=["GET"])
def index():
    return "Bot is running on Vercel!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Recieves the JSON update from Telegram"""
    if request.method == "POST":
        # Convert JSON -> Telegram Update Object
        update_json = request.get_json(force=True)
        update = Update.de_json(update_json, ptb_application.bot)
        
        # Process the update with asyncio
        asyncio.run(ptb_application.process_update(update))
        
        return "OK"
    return "Invalid"
