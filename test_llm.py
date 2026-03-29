from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

response = client.chat.completions.create(
    model="openai/gpt-3.5-turbo",  # ✅ FIXED
    messages=[
        {"role": "user", "content": "Say hello in one sentence"}
    ],
)

print(response.choices[0].message.content)