import os
import random
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Logging Setup ---
# 1. We set the basic config.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. IMPORTANT: Silence the 'httpx' logger.
# Without this, your logs will be flooded with network requests, making it hard to see real errors.
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- Bot Configuration & Safety Checks ---

# Use os.getenv instead of os.environ[] to avoid immediate KeyErrors.
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_ID_RAW = os.getenv('ADMIN_ID')

# Check 1: Is the Token missing?
if not TELEGRAM_TOKEN:
    logger.critical("ERROR: 'TELEGRAM_TOKEN' is missing in Environment Variables/Secrets.")
    exit(1) # Exit with error code

# Check 2: Is the Admin ID missing or invalid?
if not ADMIN_ID_RAW:
    logger.critical("ERROR: 'ADMIN_ID' is missing in Environment Variables/Secrets.")
    exit(1)

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    logger.critical(f"ERROR: 'ADMIN_ID' must be a number. You provided: '{ADMIN_ID_RAW}'")
    exit(1)

# --- Constants ---
USER_FILE = "users.txt"
PROBLEMS_BASE_DIR = "problems" 

# --- User Tracking Function ---
def log_user(user_id: int):
    try:
        # Create file if it doesn't exist
        if not os.path.exists(USER_FILE):
            with open(USER_FILE, "w") as f:
                f.write(f"{user_id}\n")
            return

        with open(USER_FILE, "r") as f:
            known_users = {line.strip() for line in f}

        if str(user_id) not in known_users:
            with open(USER_FILE, "a") as f:
                f.write(f"{user_id}\n")
    except Exception as e:
        logger.error(f"Failed to log user: {e}")

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message: return # Safety check
    log_user(update.message.from_user.id)

    welcome_message = (
        "Welcome to the Mathematics Olympiad Problems Bot!\n\n"
        "**Available Commands:**\n"
        "/rmo   - Regional Mathematics Olympiad\n"
        "/inmo  - Indian National Mathematics Olympiad\n"
        "/aime  - American Invitational Mathematics Examination\n"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def send_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return # Safety check for edits/media
    
    user_id = update.message.from_user.id
    log_user(user_id)

    # Command parsing logic
    try:
        command_text = update.message.text.split(' ')[0]      
        command_no_slash = command_text.lstrip('/')           
        exam_type = command_no_slash.split('@')[0]            
        
        exam_folder = os.path.join(PROBLEMS_BASE_DIR, exam_type)

        # Check if folder exists
        if not os.path.exists(exam_folder):
            await update.message.reply_text(f"Setup Error: The folder '{exam_type}' does not exist on the server.")
            return

        question_files = [f for f in os.listdir(exam_folder) if not f.startswith('.')]
        
        if not question_files:
            await update.message.reply_text(f"No problems found in the {exam_type.upper()} folder yet.")
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
    if not update.message: return
    
    if update.message.from_user.id == ADMIN_ID:
        try:
            if not os.path.exists(USER_FILE):
                await update.message.reply_text("No users recorded yet.")
                return
                
            with open(USER_FILE, "r") as f:
                # Filter out empty lines just in case
                lines = [line for line in f.readlines() if line.strip()]
                user_total = len(lines)
            await update.message.reply_text(f"Total unique users: {user_total}")
        except Exception as e:
            logger.error(f"Error reading user file: {e}")
            await update.message.reply_text("Error reading user database.")
    else:
        # Silently ignore non-admins
        pass

def main() -> None:
    # Final check before starting
    logger.info("Starting bot... Press Ctrl+C to stop.")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    problem_commands = ["rmo", "inmo", "amc8", "amc10", "amc12", "aime", "usamo", "imo"]
    for cmd in problem_commands:
        application.add_handler(CommandHandler(cmd, send_problem))

    application.add_handler(CommandHandler("users", user_count))

    # Using allowed_updates helps performance/logging by ignoring edits/chats/etc if not needed
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
