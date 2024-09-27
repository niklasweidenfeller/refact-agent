from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
import os

# import project local dependencies
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

def get_ollama_llm():
    return OllamaLLM(model="llama3.1", temperature=0)


def get_gpt_llm():
    proxy_client = get_proxy_client('gen-ai-hub')
    return ChatOpenAI(deployment_id=os.getenv("DEPLOYMENT_ID"), proxy_client=proxy_client, temperature=0.0)
