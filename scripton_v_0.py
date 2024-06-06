import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, Filters
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler
import subprocess

# Load .env file and API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
telegram_token = os.getenv("TELEGRAM_TOKEN")

# Load configuration from JSON file
with open("config.json", "r") as file:
    config = json.load(file)

def execute_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return {"success": True, "output": result.stdout.strip() or "done"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def exec_python(cell, bot, chat_id):
    ipython = get_ipython()
    if ipython is None:
        from IPython.terminal.embed import InteractiveShellEmbed
        ipython = InteractiveShellEmbed()
    result = ipython.run_cell(cell)
    output = str(result.result)
    if result.error_before_exec:
        output += f"\n{result.error_before_exec}"
    if result.error_in_exec:
        output += f"\n{result.error_in_exec}"
    if len(output) > 1000:
        output = output[:1000] + "\n\n... truncated"
    bot.send_message(chat_id=chat_id, text=output)

def handle_command(update: Update, context: CallbackContext):
    user_content = update.message.text
    chat_id = update.message.chat_id
    bot = context.bot

    if user_content.lower() == config["exit_command"]:
        bot.send_message(chat_id=chat_id, text="Exiting.")
        return  # End the command

    if user_content.startswith("/exec"):
        exec_python(user_content[6:], bot, chat_id)
    else:
        result = execute_command(user_content)
        response = f"Command execution result: {result['output']}" if result['success'] else f"Error: {result['error']}"
        bot.send_message(chat_id=chat_id, text=response)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Welcome to the bot. Use /exec <code> to execute Python code, or type a command to execute.')

def main():
    updater = Updater(telegram_token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_command))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
