import json
import os
import subprocess
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext

# Load .env file
load_dotenv()

# Load OpenAI API key and Telegram bot token from environment variables
api_key = os.getenv("OPENAI_API_KEY")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")

# Load configuration from JSON file
with open("config.json", "r") as file:
    config = json.load(file)

# Define a 'tools' array specifying the tools that can be called within the OpenAI Completion
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

# Define the execute_command function
def execute_command(command):
    try:
        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        return {"success": True, "output": output or "done"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Modify get_response to include tools and handle sending results back
def exec_python(cell):
    ipython = get_ipython()
    if ipython is None:
        #hotfix for Mac M1
        from IPython.terminal.embed import InteractiveShellEmbed
        ipython = InteractiveShellEmbed()
    result = ipython.run_cell(cell)
    log = str(result.result)
    if result.error_before_exec is not None:
        log += f"\n{result.error_before_exec}"
    if result.error_in_exec is not None:
        log += f"\n{result.error_in_exec}"

    # Check the logs length
    if len(log) > 1000:
        log = log[:1000]
        log += "\n\n... truncated"
    return log

def get_response(client, messages):
    if config.get("debug", False):
        print(f"Debug: To AI messages = {messages}")
    # Make a request to the OpenAI API, providing the model, messages and tools
    return client.chat.completions.create(
        model=config["openai_model"],
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

# Define the function to handle incoming messages from Telegram
def handle_message(update: Update, context: CallbackContext):
    user_content = update.message.text
    chat_id = update.message.chat_id
    conversation = context.bot_data.get(chat_id, [{"role": "system", "content": f"Your operation system is {os.name}" + config["system_message"]}])

    # Append user message to conversation history
    conversation.append({"role": "user", "content": user_content})

    try:
        # Get response from OpenAI's ChatGPT
        client = OpenAI(api_key=api_key)
        response = get_response(client, conversation)
        if config.get("debug", False):
            print(f"Debug: AI RawResponse = {response}")

        if response.choices[0].message.content:
            bot_response = response.choices[0].message.content
            update.message.reply_text(bot_response)
            conversation.append({"role": "assistant", "content": bot_response})

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

                            # TODO conversation.append({"role": "tool", "content": result_message, "tool_call_id": tool_id})
                            update.message.reply_text(result_message)
                        else:
                            conversation.append(
                                {"role": "assistant", "name": "tool", "content": f"Invalid command format.={command}"})
                            update.message.reply_text(f"Invalid command format.={command}")
    except Exception as e:
        conversation.append({"role": "user", "name": "Exception", "content": str(e)})
        update.message.reply_text(f"Error: {str(e)}")

    context.bot_data[chat_id] = conversation

# Define the function 'main' which is the entry point of the script
def main():
    # Create the Bot and Updater instances
    bot = Bot(token=telegram_token)
    updater = Updater(bot=bot, use_context=True)
    dispatcher = updater.dispatcher

    # Add handler for incoming messages
    dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    updater.start_polling()
    updater.idle()

# Check if the script is the main module being executed, and if so, call main()
if __name__ == "__main__":
    main()
