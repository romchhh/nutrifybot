from os import getenv
from dotenv import load_dotenv

load_dotenv()

token = getenv('TOKEN')

administrators = [int(id) for id in getenv('ADMINISTRATORS')[1:-1].split(',')]

OPENAI_API_KEY = getenv('OPENAI_API_KEY')
OPENAI_MODEL = getenv('OPENAI_MODEL', 'gpt-4o')
OPENAI_TEMPERATURE = float(getenv('OPENAI_TEMPERATURE', '0.5'))
OPENAI_TOP_P = float(getenv('OPENAI_TOP_P', '0.9'))
OPENAI_FREQUENCY_PENALTY = float(getenv('OPENAI_FREQUENCY_PENALTY', '0.4'))
OPENAI_PRESENCE_PENALTY = float(getenv('OPENAI_PRESENCE_PENALTY', '0.1'))
OPENAI_MAX_COMPLETION_TOKENS = int(getenv('OPENAI_MAX_COMPLETION_TOKENS', '1600'))
OPENAI_SEED = int(getenv('OPENAI_SEED', '42'))
