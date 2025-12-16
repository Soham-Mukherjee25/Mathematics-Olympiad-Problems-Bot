import os
import random
import logging
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration ---
app = Flask(__name__)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# --- Path Logic ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS_DIR = os.path.join(BASE_DIR, 'problems')

# --- Bot Handlers (Logic) ---

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
        command_text = update.message.text.split(' ')[0]      
        command_no_slash = command_text.lstrip('/')           
        exam_type = command_no_slash.split('@')[0]            
        
        # Adjust casing just in case
        exam_type = exam_type.lower()
        exam_folder = os.path.join(PROBLEMS_DIR, exam_type)

        if not os.path.exists(exam_folder):
            await update.message.reply_text(f"Setup Error: Folder '{exam_type}' not found at {exam_folder}.")
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

# --- Helper to process updates properly on Serverless ---
async def process_telegram_update(data):
    # 1. Initialize Application strictly inside this async function
    ptb_application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 2. Add Handlers
    ptb_application.add_handler(CommandHandler("start", start))
    problem_commands = ["rmo", "inmo", "amc8", "amc10", "amc12", "aime", "usamo", "imo"]
    for cmd in problem_commands:
        ptb_application.add_handler(CommandHandler(cmd, send_problem))
    
    # 3. Initialize the application manually (Required for serverless)
    await ptb_application.initialize()
    
    # 4. Decode the update
    # We must use the bot attached to the application
    update = Update.de_json(data, ptb_application.bot)
    
    # 5. Process Update
    await ptb_application.process_update(update)
    
    # 6. Shutdown ensures the session is closed cleanly so no 'loop closed' errors happen next time
    await ptb_application.shutdown()


# --- Flask Webhook Route ---

@app.route("/", methods=["GET"])
def index():
    return "Bot is running on Vercel!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json(force=True)
            # Run the async logic in a fresh run
            asyncio.run(process_telegram_update(data))
            return "OK"
        except Exception as e:
            logger.error(f"Failed to process update: {e}")
            return "Error", 500
    return "Invalid"
