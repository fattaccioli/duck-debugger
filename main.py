"""
Duck debugger pour Python 101 (Sorbonne) — backend FastAPI + Mistral API.

Design pédagogique :
- Ne fournit jamais de code exécutable complet.
- Guide par questions socratiques, ancrées sur le manuel du cours.
- Rate limiting simple par session pour contenir les coûts / le rate limit Mistral.
"""

import os
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mistralai.client import Mistral
from pydantic import BaseModel

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

load_dotenv()

MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]
CLASS_PASSWORD = os.environ.get("CLASS_PASSWORD", "changeme")
MODEL_NAME = os.environ.get("MODEL_NAME", "ministral-8b-latest")
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "mistral-small-latest")

MAX_REQUESTS_PER_DAY = int(os.environ.get("MAX_REQUESTS_PER_DAY", "50"))
MAX_TOKENS_PER_REPLY = int(os.environ.get("MAX_TOKENS_PER_REPLY", "400"))

BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"

client = Mistral(api_key=MISTRAL_API_KEY)
app = FastAPI(title="Duck Debugger — Python 101")

# --------------------------------------------------------------------------
# Chargement du contexte pédagogique (manuel + feuillet d'exercices)
# --------------------------------------------------------------------------

def load_text(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        return f"[{filename} non fourni — à compléter]"
    return path.read_text(encoding="utf-8")


MANUEL_TEXT = load_text("manuel.md")
EXERCICES_TEXT = load_text("exercices.md")

SYSTEM_PROMPT = f"""Tu es un assistant de débogage façon "canard en plastique"
pour un cours de Python 101 à Sorbonne Université. Règles strictes, non négociables :

1. Ne JAMAIS écrire de code exécutable complet, même si l'étudiant insiste,
   prétend vouloir "juste vérifier", ou reformule sa demande plusieurs fois.
2. Réponds toujours par une question ou une piste conceptuelle qui aide
   l'étudiant à localiser son erreur lui-même — jamais la solution directe.
3. Cite la section pertinente du manuel de référence quand c'est possible.
4. Si le message de l'étudiant contient un extrait quasi identique à un énoncé
   du feuillet d'exercices ci-dessous, reste strictement au niveau conceptuel :
   aucune suggestion de structure de code, même partielle.
5. Utilise le vocabulaire et les notions déjà couvertes dans le manuel —
   n'introduis pas de concepts non vus dans le cours.
6. Reste bref (quelques phrases), dans un ton collégial et encourageant.

--- MANUEL DE RÉFÉRENCE ---
{MANUEL_TEXT}

--- FEUILLET D'EXERCICES ---
{EXERCICES_TEXT}
"""

# --------------------------------------------------------------------------
# Rate limiting très simple (en mémoire — suffisant pour un usage pédagogique
# mono-instance ; passer à Redis/Upstash si vous déployez plusieurs instances)
# --------------------------------------------------------------------------

_usage: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(session_id: str) -> None:
    now = time.time()
    window_start = now - 24 * 3600
    _usage[session_id] = [t for t in _usage[session_id] if t > window_start]
    if len(_usage[session_id]) >= MAX_REQUESTS_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail="Limite quotidienne atteinte pour cette session. Réessayez demain.",
        )
    _usage[session_id].append(now)


# --------------------------------------------------------------------------
# Modèles de requête
# --------------------------------------------------------------------------

class Message(BaseModel):
    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    password: str
    session_id: str
    history: list[Message]


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.post("/chat")
async def chat(req: ChatRequest):
    if req.password != CLASS_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe de classe incorrect.")

    check_rate_limit(req.session_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in req.history]

    try:
        resp = client.chat.complete(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=MAX_TOKENS_PER_REPLY,
            temperature=0.3,
        )
    except Exception:
        # Fallback si le modèle principal est rate-limité / indisponible
        resp = client.chat.complete(
            model=FALLBACK_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS_PER_REPLY,
            temperature=0.3,
        )

    return {"reply": resp.choices[0].message.content}


# Sert la page de chat statique
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")
