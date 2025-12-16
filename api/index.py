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

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_ID_RAW = os.getenv('ADMIN_ID')

# Validate Env Vars
if not TELEGRAM_TOKEN or not ADMIN_ID_RAW:
    logger.critical("Missing env variables!")

try:
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW else 0
except ValueError:
    ADMIN_ID = 0

# --- File System Fix for Vercel ---
# On Vercel, we must calculate the absolute path to the problems folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS_DIR = os.path.join(BASE_DIR, 'problems')

# --- Logic (Removed User Logging for Vercel) ---
# NOTE: You cannot write to 'users.txt' on Vercel (Read-only filesystem).
# To track users, you must use a database (MongoDB/Supabase).
# I have removed the log_user call to prevent errors.

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "Welcome to the Mathematics Olympiad Problems Bot!\n\n"
        "**Available Commands:**\n"
        "/rmo   - Regional Mathematics Olympiad\n"
        "/inmo  - Indian National Mathematics Olympiad\n"
        "/aime  - American Invitational Mathematics Examination\n"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def send_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return
    
    try:
        command_text = update.message.text.split(' ')[0]      
        command_no_slash = command_text.lstrip('/')           
        exam_type = command_no_slash.split('@')[0]            
        
        exam_folder = os.path.join(PROBLEMS_DIR, exam_type)

        if not os.path.exists(exam_folder):
            await update.message.reply_text(f"Setup Error: The folder '{exam_type}' does not exist.")
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

async def user_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # This feature is disabled on Vercel unless you use a Database
    if update.message.from_user.id == ADMIN_ID:
        await update.message.reply_text("User counting is disabled on Vercel (Read-only filesystem).")

# --- Initialize Bot Application ---
# We build the app globally so it can be reused
ptb_application = Application.builder().token(TELEGRAM_TOKEN).build()

# Add Handlers
ptb_application.add_handler(CommandHandler("start", start))
ptb_application.add_handler(CommandHandler("users", user_count))

problem_commands = ["rmo", "inmo", "amc8", "amc10", "amc12", "aime", "usamo", "imo"]
for cmd in problem_commands:
    ptb_application.add_handler(CommandHandler(cmd, send_problem))

# --- Flask Routes (The Webhook Logic) ---

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """
    This function receives updates from Telegram and passes them to the bot.
    """
    if request.method == "POST":
        # Retrieve the JSON update
        update = Update.de_json(request.get_json(force=True), ptb_application.bot)
        
        # Run the async process_update inside the synchronous Flask route
        asyncio.run(ptb_application.process_update(update))
        
        return "OK"
    return "Invalid Method"

# Keep this for local testing only
if __name__ == '__main__':
    app.run(port=5000)
