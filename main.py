"""
Duck debugger pour Python 101 (Sorbonne) — backend FastAPI + Mistral API.

Design pédagogique :
- Ne fournit jamais de code exécutable complet.
- Guide par questions socratiques, ancrées sur le manuel du cours.
- Rate limiting simple par session pour contenir les coûts / le rate limit Mistral.
"""

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from mistralai.client import Mistral
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

load_dotenv()

MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]
CLASS_PASSWORD = os.environ.get("CLASS_PASSWORD", "changeme")
MODEL_NAME = os.environ.get("MODEL_NAME", "ministral-8b-latest")
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "mistral-small-latest")

MAX_REQUESTS_PER_DAY_PER_SESSION = int(os.environ.get("MAX_REQUESTS_PER_DAY_PER_SESSION", "50"))
MAX_REQUESTS_PER_DAY_GLOBAL = int(os.environ.get("MAX_REQUESTS_PER_DAY_GLOBAL", "500"))
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

SYSTEM_PROMPT = f"""Tu es un assistant de débogage socratique (« canard en plastique ») pour le cours
« Éléments de Programmation » – Python 101 de Sorbonne Université (LU1IN001).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLES STRICTES (non négociables)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **NE JAMAIS ÉCRIRE DE CODE EXÉCUTABLE COMPLET**
   - Même si l'étudiant insiste, réformule, prétend « juste vérifier »
   - Même après 5+ tentatives ou questions reformulées
   - Même si la réponse semble « évidente »
   - Pas de boucles complètes, pas de fonctions complètes, pas de solutions finales
   - Pas d'une seule ligne d'algorithme en tant que réponse

2. **GUIDE PAR QUESTIONS SOCRATIQUES**
   - Réponds toujours par des questions ou des pistes conceptuelles
   - Aide l'étudiant à LOCALISER et COMPRENDRE l'erreur lui-même
   - Jamais la solution directe — guide vers la solution
   - Exemple bon : « Quelle est la différence entre // et / ? Laquelle dois-tu utiliser ici ? »
   - Exemple mauvais : « Utilise // pour la division entière »

3. **VOCABULAIRE FORMEL ET FRANÇAIS DU COURS**
   - "n-uplet" (pas "tuple")
   - "chaîne de caractères" (pas "string")
   - "affectation" (pas "assignement")
   - "alternatives" (pas "conditionnelles")
   - Tous les noms de fonctions EN FRANÇAIS dans les exemples/explications
   - Utilise les termes : spécification, préconditions, jeu de tests, signature, type

4. **PROPRIÉTÉS DES ALGORITHMES (Chapitre 4 du cours)**
   - Enseigne systématiquement : **Correction, Terminaison, Efficacité**
   - « Ton algo va-t-il toujours s'arrêter ? »
   - « Est-ce que le résultat est correct pour tous les cas ? »
   - « Peut-on optimiser le nombre d'opérations ? »

5. **TYPAGE STRICT ET HOMOGÉNÉITÉ**
   - Les listes DOIVENT avoir le même type pour tous les éléments : List[T]
   - Les ensembles DOIVENT être homogènes : Set[T]
   - Les dicts : clés du type K, valeurs du type V
   - Insiste sur la déclaration ET l'initialisation des variables
   - Pas d'exceptions au typage

6. **PATTERNS ALGORITHMIQUES FORMELS**
   - Enseigne les trois patterns : RÉDUCTIONS, TRANSFORMATIONS, FILTRAGES
   - Réduction : List[T] → U (ex: somme, longueur)
   - Transformation : List[T] → List[U] (ex: longueurs de chaînes)
   - Filtrage : List[T] → List[T] (ex: nombres pairs)

7. **TRAÇAGE D'EXÉCUTION (simulation manuelle)**
   - Enseigne à tracer manuellement les boucles
   - « Crée un tableau : Itération | Variable | Valeur »
   - Aide l'étudiant à comprendre l'exécution étape par étape
   - Ne donne pas la réponse — guide vers la simulation

8. **SPÉCIFICATION FORMELLE**
   - Rappelle la structure obligatoire :
     1. Signature typée : def ma_fonction(x : int, y : str) -> bool:
     2. Préconditions dans la docstring
     3. Description du problème résolu
     4. Jeu de tests (assert)
   - Insiste : « As-tu écrit les préconditions ? Et ton jeu de tests ? »

9. **SI L'EXERCICE RESSEMBLE À UN ÉNONCÉ OFFICIEL**
   - Reste STRICTEMENT au niveau conceptuel
   - Aucune suggestion de structure de code, même partielle
   - Aucun pseudo-code qui serait trop proche de la solution
   - Guide uniquement par des questions et des concepts

10. **LIMITES DU PROGRAMME**
    - N'utilise QUE ce qui est dans le manuel et la carte de référence
    - Pas de POO (classes) — max introduction chapitre 13
    - Pas de décorateurs, context managers, générateurs, async/await
    - Pas d'imports avancés (sauf typing et math)
    - Pas de lambda (pas dans la carte de référence)

11. **TON ET STYLE**
    - Bref : quelques phrases max
    - Collégial et encourageant, jamais condescendant
    - Utilise le français du cours
    - Pose des questions qui invitent à réfléchir, pas qui découragent

12. **STRUCTURE DES RÉPONSES : ORDRE LOGIQUE**
    Quand tu identifies plusieurs problèmes, ordonne-les ainsi :

    **ÉTAPE 1 : ERREURS ÉVIDENTES (Syntax, structure formelle)**
    - Erreurs de syntaxe Python
    - Indentation incorrecte
    - Manque de signature typée
    - Manque de docstring / préconditions
    - Manque de jeu de tests (assert)

    **ÉTAPE 2 : ERREURS DE LOGIQUE (Algorithme, flow de contrôle)**
    - Condition incorrecte
    - Boucle infinie ou ne s'exécute pas
    - Affectation manquante ou mal placée
    - Type incorrect utilisé

    **ÉTAPE 3 : SUBTILITÉS (Efficacité, corner cases)**
    - Inefficacité (append vs +, boucles imbriquées inutiles)
    - Cas limites non gérés (liste vide, division par zéro)
    - Propriétés d'algo (correction, terminaison, efficacité)

    Format ta réponse avec retours à la ligne pour chaque étape :
    « D'abord, tu dois... [NEWLINE] [NEWLINE]
      Ensuite, pour la logique... [NEWLINE] [NEWLINE]
      Plus subtil : pense aussi à... »

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE PÉDAGOGIQUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Le cours couvre :
- Chapitre 1 : Premiers pas, expressions, types simples
- Chapitre 2 : Variables, affectations, alternatives (if/elif/else)
- Chapitre 3 : Boucles (while, for), simulation
- Chapitre 4 : Correction, Terminaison, Efficacité, Récursion
- Chapitre 5 : Intervalles (range), chaînes de caractères
- Chapitre 6 : Listes (homogènes), réductions/transformations/filtrages
- Chapitre 7 : N-uplets (tuples immuables), retours multiples
- Chapitre 8 : Compréhensions de listes
- Chapitre 9 : Ensembles (Set[T], homogènes, opérations ensemblistes)
- Chapitre 10 : Dictionnaires (Dict[K, V])
- Chapitre 11 : Itérables, compréhensions avancées

Distinctions critiques :
- Division : / (réelle, retourne float) vs // (euclidienne, retourne int)
- Listes homogènes : tous éléments même type T
- Modification in-place (efficace) : append(), vs reconstruction : +
- Immutabilité des n-uplets vs mutabilité des listes

--- MANUEL DE RÉFÉRENCE ---
{MANUEL_TEXT}

--- FEUILLET D'EXERCICES ---
{EXERCICES_TEXT}
"""

# --------------------------------------------------------------------------
# Rate limiting (en mémoire — suffisant pour un usage pédagogique
# mono-instance ; passer à Redis/Upstash si vous déployez plusieurs instances)
# --------------------------------------------------------------------------

_session_usage: dict[str, list[float]] = defaultdict(list)
_global_usage: list[float] = []


def check_rate_limits(session_id: str) -> None:
    """Check both per-session and global rate limits."""
    now = time.time()
    window_start = now - 24 * 3600

    # Clean up old entries
    _session_usage[session_id] = [t for t in _session_usage[session_id] if t > window_start]
    _global_usage.clear()
    _global_usage.extend([t for t in _global_usage if t > window_start])

    # Check per-session limit
    if len(_session_usage[session_id]) >= MAX_REQUESTS_PER_DAY_PER_SESSION:
        logger.warning(
            f"Session {session_id} exceeded daily limit ({MAX_REQUESTS_PER_DAY_PER_SESSION})"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Limite quotidienne atteinte pour cette session ({MAX_REQUESTS_PER_DAY_PER_SESSION} requêtes/jour). Réessayez demain.",
        )

    # Check global limit
    if len(_global_usage) >= MAX_REQUESTS_PER_DAY_GLOBAL:
        logger.error(
            f"GLOBAL LIMIT REACHED: {len(_global_usage)} requests today (max: {MAX_REQUESTS_PER_DAY_GLOBAL})"
        )
        raise HTTPException(
            status_code=503,
            detail="Service temporairement indisponible. Le quota quotidien global a été atteint. Réessayez demain.",
        )

    # Record this request
    _session_usage[session_id].append(now)
    _global_usage.append(now)
    logger.info(
        f"Request allowed. Session {session_id}: {len(_session_usage[session_id])}/{MAX_REQUESTS_PER_DAY_PER_SESSION} | "
        f"Global: {len(_global_usage)}/{MAX_REQUESTS_PER_DAY_GLOBAL}"
    )


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
        logger.warning(f"Failed auth attempt from session {req.session_id}")
        raise HTTPException(status_code=401, detail="Mot de passe de classe incorrect.")

    check_rate_limits(req.session_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in req.history]

    logger.info(f"Attempting primary model ({MODEL_NAME}) for session {req.session_id}")

    # Return streaming response with primary model
    # Fallback will be attempted inside the generator if needed
    return StreamingResponse(
        _stream_with_fallback(MODEL_NAME, messages, req.session_id),
        media_type="text/event-stream"
    )


def _stream_with_fallback(model: str, messages: list, session_id: str):
    """Try model, fallback to FALLBACK_MODEL on rate limit."""
    try:
        response_stream = client.chat.stream(
            model=model,
            messages=messages,
            max_tokens=MAX_TOKENS_PER_REPLY,
            temperature=0.3,
        )

        for chunk in response_stream:
            if chunk.data.choices[0].delta.content:
                content = chunk.data.choices[0].delta.content
                yield f"data: {content}\n\n"

        logger.info(f"Stream completed successfully with {model} for session {session_id}")
        yield "data: [DONE]\n\n"

    except Exception as e:
        error_str = str(e).lower()

        # Try fallback on rate limit
        if "429" in error_str or "rate" in error_str:
            logger.warning(
                f"Model {model} rate limited for session {session_id}. Trying fallback {FALLBACK_MODEL}"
            )
            try:
                response_stream = client.chat.stream(
                    model=FALLBACK_MODEL,
                    messages=messages,
                    max_tokens=MAX_TOKENS_PER_REPLY,
                    temperature=0.3,
                )

                for chunk in response_stream:
                    if chunk.data.choices[0].delta.content:
                        content = chunk.data.choices[0].delta.content
                        yield f"data: {content}\n\n"

                logger.info(f"Fallback stream completed for session {session_id}")
                yield "data: [DONE]\n\n"
                return

            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                yield f"data: [ERROR] Service Mistral temporairement saturé\n\n"

        # Auth/quota errors
        elif any(code in error_str for code in ["401", "402", "403", "auth", "quota", "billing"]):
            logger.error(f"Auth/Quota error for session {session_id}: {e}")
            yield f"data: [ERROR] Erreur de configuration (authentification ou quota)\n\n"

        # Other errors
        else:
            logger.error(f"Unexpected error for session {session_id}: {e}")
            yield f"data: [ERROR] Erreur du service Mistral\n\n"


@app.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    now = time.time()
    window_start = now - 24 * 3600

    # Count requests in the last 24h
    global_today = len([t for t in _global_usage if t > window_start])

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "global_requests_today": global_today,
        "global_limit": MAX_REQUESTS_PER_DAY_GLOBAL,
        "sessions_tracked": len(_session_usage),
    }


@app.get("/admin/status")
async def admin_status(password: str = None):
    """Admin status endpoint (requires CLASS_PASSWORD)."""
    if password != CLASS_PASSWORD:
        logger.warning(f"Failed admin auth attempt")
        raise HTTPException(status_code=401, detail="Invalid password")

    now = time.time()
    window_start = now - 24 * 3600

    # Calculate stats
    global_today = len([t for t in _global_usage if t > window_start])
    session_stats = {
        sid: len([t for t in times if t > window_start])
        for sid, times in _session_usage.items()
    }

    logger.info(f"Admin status check: {global_today}/{MAX_REQUESTS_PER_DAY_GLOBAL} global requests")

    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "global": {
            "requests_today": global_today,
            "limit": MAX_REQUESTS_PER_DAY_GLOBAL,
            "percentage": round(100 * global_today / MAX_REQUESTS_PER_DAY_GLOBAL, 1),
        },
        "per_session": {
            "limit": MAX_REQUESTS_PER_DAY_PER_SESSION,
            "active_sessions": len(_session_usage),
            "session_details": session_stats,
        },
        "models": {
            "primary": MODEL_NAME,
            "fallback": FALLBACK_MODEL,
        },
    }


# Sert la page de chat statique
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")
