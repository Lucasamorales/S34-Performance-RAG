from typing import List
from openai import OpenAI
from app.config import settings

_client = OpenAI(api_key=settings.openai_api_key)
_EMBED_MODEL = "text-embedding-3-small"

def _to_single_string(text:str) -> str:
    #basic normalization, expand later
    return (text or "").replace("\n", " ").strip()

def embed_text(text:str) -> List[float]:
    resp = _client.embeddings.create(model=_EMBED_MODEL, input=_to_single_string(text))
    return resp.data[0].embedding