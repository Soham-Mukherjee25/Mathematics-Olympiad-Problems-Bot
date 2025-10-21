import os
import random
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Logging Setup ---
# This helps in debugging by showing events and errors in the console/logs.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Bot Configuration ---
# These are read from your environment's secrets (Replit Secrets or Railway Variables).
try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    ADMIN_ID = int(os.environ['ADMIN_ID'])
except KeyError:
    logger.error("FATAL: TELEGRAM_TOKEN or ADMIN_ID not found in environment variables.")
    # Exit if secrets are not set, to prevent running with invalid config.
    exit()

# --- Constants ---
USER_FILE = "users.txt"
PROBLEMS_BASE_DIR = "problems" # The main folder for all your exam questions

# --- User Tracking Function ---

def log_user(user_id: int):
    """
    Checks if a user ID is new and saves it to the user file.
    This is a simple way to track unique users.
    """
    try:
        # Read the set of existing user IDs for efficient lookup.
        with open(USER_FILE, "r") as f:
            known_users = {int(line.strip()) for line in f}

        # If the user is not in the set, add them to the file.
        if user_id not in known_users:
            with open(USER_FILE, "a") as f:
                f.write(f"{user_id}\n")
    except FileNotFoundError:
        # If the file doesn't exist, create it and add the first user.
        with open(USER_FILE, "w") as f:
            f.write(f"{user_id}\n")

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for the /start command.
    Sends a welcome message and explains the bot's commands.
    """
    log_user(update.message.from_user.id)

    welcome_message = (
        "Welcome to the Mathematics Olympiad Problems Bot!\n\n"
        "I provide past problems from various prestigious math competitions. "
        "Just use one of the commands below to get a random problem image.\n\n"
        "**Available Commands:**\n"
        "/rmo   - Regional Mathematics Olympiad\n"
        "/inmo  - Indian National Mathematics Olympiad\n"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def send_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A generic handler to send a problem from a specified exam folder.
    This function powers all the exam-specific commands and works in groups.
    """
    log_user(update.message.from_user.id)

    # --- THIS IS THE CORRECTED PART FOR GROUP CHATS ---
    # Determine the exam type, correctly handling commands like /inmo@BotUsername
    command_text = update.message.text.split(' ')[0]      # Gets "/inmo@BotUsername"
    command_no_slash = command_text.lstrip('/')           # Gets "inmo@BotUsername"
    exam_type = command_no_slash.split('@')[0]            # Gets "inmo"
    # --- END OF CORRECTION ---

    exam_folder = os.path.join(PROBLEMS_BASE_DIR, exam_type)

    try:
        # Check if the directory for the exam exists.
        if not os.path.isdir(exam_folder):
            logger.warning(f"User requested problems from a non-existent folder: {exam_folder}")
            await update.message.reply_text(f"Sorry, I couldn't find any problems for {exam_type.upper()}.")
            return

        question_files = [f for f in os.listdir(exam_folder) if not f.startswith('.')] # Ignore hidden files
        if not question_files:
            logger.warning(f"Problem folder is empty: {exam_folder}")
            await update.message.reply_text(f"Sorry, the problem set for {exam_type.upper()} is currently empty.")
            return

        # Pick a random question and send it as a photo.
        random_question_file = random.choice(question_files)
        file_path = os.path.join(exam_folder, random_question_file)

        await update.message.reply_photo(
            photo=open(file_path, 'rb'),
            caption=f"Here is your {exam_type.upper()} problem. Good luck!"
        )

    except Exception as e:
        logger.error(f"An error occurred in send_problem for command '{exam_type}': {e}")
        await update.message.reply_text("An unexpected error occurred while fetching a problem. Please try again later.")


async def user_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A private handler for the /users command.
    Only the admin can use this to check the total number of unique users.
    """
    if update.message.from_user.id == ADMIN_ID:
        try:
            with open(USER_FILE, "r") as f:
                user_total = len(f.readlines())
            await update.message.reply_text(f"Total unique users: {user_total}")
        except FileNotFoundError:
            await update.message.reply_text("No users have been recorded yet.")
    else:
        # If a non-admin tries to use it, we don't send any message to avoid spam.
        logger.warning(f"Unauthorized user {update.message.from_user.id} tried to use /users.")


def main() -> None:
    """
    This is the main function that sets up the bot, registers the command handlers,
    and starts the bot polling for updates.
    """

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Register all command handlers ---
    application.add_handler(CommandHandler("start", start))

    # A list of all exam commands that will use the same send_problem function.
    problem_commands = ["rmo", "inmo", "amc8", "amc10", "amc12", "aime", "usamo", "imo"]
    for cmd in problem_commands:
        application.add_handler(CommandHandler(cmd, send_problem))

    # The private command for the owner.
    application.add_handler(CommandHandler("users", user_count))

    # Start the bot.
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
