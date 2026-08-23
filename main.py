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
