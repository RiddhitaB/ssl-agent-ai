# ai_agent.py - Clean Groq Setup
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()  # Load .env file

# Get Groq API key
groq_key = os.getenv("GROQ_API_KEY")

if not groq_key:
    raise ValueError("GROQ_API_KEY not found in .env file. Please add it.")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",   # Fast and reliable model
    temperature=0.1,
    max_tokens=900,
    api_key=groq_key,                  # Explicitly pass key
)

print("LLM successfully loaded: Groq - llama-3.3-70b-versatile")