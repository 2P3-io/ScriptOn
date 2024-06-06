# SriptOn
To install please copy the link to the repository https://github.com/2P3-io/ScriptOn.git
Go to the terminal in you operating system.

Go to the folder where you want to install.

For linux:
  git clone https://github.com/2P3-io/ScriptOn.git

For other: 
  use chat gpt, anthropic or other free llm to help you recreate in your system.

nano .env

paste the following 

OPENAI_API_KEY=YourKey
TELEGRAM_TOKEN=yourTocken
#replace with your api key and telegram tocken 
control o, yes, control x

please activate virtual enviornment of your choice for your peace of mind

python3 -m venv main_env
source main_env/bin/activate

pip install python-dotenv
pip install openai

python3 scripton

python3 scripton_v_0.py





This is where the simplest scripts with AI integration live. People call them agents. The simplest most general of which are scriptons.

