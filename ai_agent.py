from langchain_openai import ChatOpenAI
from tools import renew_certificate, verify_certificate
from dotenv import load_dotenv
import os

load_dotenv()

# 🔥 LLM (OpenRouter)
llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    model="deepseek/deepseek-chat",
    temperature=0
)


# ================================
# SIMPLE AGENT FUNCTION (NO BROKEN IMPORTS)
# ================================
def run_agent(prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Agent Error: {str(e)}"