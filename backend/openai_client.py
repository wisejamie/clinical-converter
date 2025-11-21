import openai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('OPENAI_API_KEY')
client = openai.OpenAI(api_key=api_key)
