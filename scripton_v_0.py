import json
import os
import subprocess
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Load .env file and API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
telegram_token = os.getenv("TELEGRAM_TOKEN")

# Load configuration from JSON file
with open("config.json", "r") as file:
    config = json.load(file)

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Define tools array specifying the tools that can be called within the OpenAI Completion
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a system command line with shell subprocess module",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute",
                    }
                },
                "required": ["command"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exec_python",
            "description": "This tool takes a python cell and executes it in the ipython kernel. The output of the cell is returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cell": {
                        "type": "string",
                        "description": "Valid Python cell to execute."
                    }
                },
                "required": ["cell"]
            }
        }
    }
]

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

def get_response(client, messages):
    if config.get("debug", False):
        print(f"Debug: To AI messages = {messages}")
    return client.chat.completions.create(
        model=config["openai_model"],
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_content = update.message.text
    chat_id = update.message.chat_id
    bot = context.bot

    conversation = [{"role": "system", "content": f"Your operation system is {os.name}" + config["system_message"]}]
    conversation.append({"role": "user", "content": user_content})

    if user_content.lower() == config["exit_command"]:
        await update.message.reply_text("Exiting.")
        return  # End the command

    try:
        # Get response from OpenAI's ChatGPT
        response = get_response(client, conversation)
        if config.get("debug", False):
            print(f"Debug: AI RawResponse = {response}")

        if response.choices[0].message.content:
            await update.message.reply_text(response.choices[0].message.content)
            conversation.append({"role": "assistant", "content": response.choices[0].message.content})

        # Check if 'tool_calls' attribute exists and is not None
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls is not None:
            for tool_call in response.choices[0].message.tool_calls:
                if getattr(tool_call, 'type', None) == 'function':
                    function_name = getattr(tool_call.function, 'name', None)
                    arguments = getattr(tool_call.function, 'arguments', "{}")

                    if function_name == 'execute_command':
                        # Ensure that arguments are properly formatted as a string
                        command = json.loads(arguments).get('command', '')
                        if isinstance(command, str):
                            # Execute the command and print the result
                            result = execute_command(command)
                            result_message = f"Command execution result: {result['output']}" if result['success'] else f"Error: {result['error']}"

                            # Send the tool result back to the model for further conversation
                            conversation.append({"role": "assistant", "name": "tool", "content": result_message})

                            await update.message.reply_text(result_message)
                        else:
                            conversation.append(
                                {"role": "assistant", "name": "tool", "content": f"Invalid command format.={command}"})
                            await update.message.reply_text(f"Invalid command format.={command}")
    except Exception as e:
        conversation.append({"role": "user", "name": "Exception", "content": str(e)})
        await update.message.reply_text(f"Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome to the bot. Use /exec <code> to execute Python code, or type a command to execute.')

def main():
    app = ApplicationBuilder().token(telegram_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=handle_command))

    app.run_polling()

if __name__ == "__main__":
    main()
