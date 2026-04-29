import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def get_gemini_client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


MODEL_PRO = "gemini-2.5-pro"
MODEL_FLASH = "gemini-2.5-flash"
MODEL_FLASH_LITE = "gemini-2.0-flash-lite"
EMBEDDING_MODEL = "text-embedding-004"


def get_embedding(text: str) -> list[float]:
    client = get_gemini_client()
    text = text[:2000] if len(text) > 2000 else text
    result = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
    return result.embeddings[0].values
