import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
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
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": str(e)}

async def exec_python(cell, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(output)

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_content = update.message.text
    if user_content.lower() == config["exit_command"]:
        await update.message.reply_text("Exiting.")
        return  # End the command

    if user_content.startswith("/exec"):
        await exec_python(user_content[6:], update, context)
    else:
        result = execute_command(user_content)
        response = f"Command execution result: {result['output']}" if result['success'] else f"Error: {result['error']}"
        await update.message.reply_text(response)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome to the bot. Use /exec <code> to execute Python code, or type a command to execute.')

def main():
    app = ApplicationBuilder().token(telegram_token).build()

    # Adding handlers for different types of messages
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=handle_command))

    app.run_polling()

if __name__ == "__main__":
    main()
