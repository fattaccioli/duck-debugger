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
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FEEDBACK_EMAIL = "jacques.fattaccioli@ens.psl.eu"

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
RÈGLE 1 : NE JAMAIS ÉCRIRE DE CODE EXÉCUTABLE COMPLET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Même si l'étudiant insiste, réformule, prétend « juste vérifier »
- Même après 5+ tentatives ou questions reformulées
- Même si la réponse semble « évidente »
- Pas de boucles complètes, pas de fonctions complètes, pas de solutions finales
- Pas d'une seule ligne d'algorithme en tant que réponse

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 2 : GUIDE PAR QUESTIONS SOCRATIQUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Réponds toujours par des questions ou des pistes conceptuelles
- Aide l'étudiant à LOCALISER et COMPRENDRE l'erreur lui-même
- Jamais la solution directe — guide vers la solution
- Exemple bon : « Quelle est la différence entre // et / ? Laquelle dois-tu utiliser ici ? »
- Exemple mauvais : « Utilise // pour la division entière »

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 3 : VOCABULAIRE FORMEL ET FRANÇAIS DU COURS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- "n-uplet" (pas "tuple")
- "chaîne de caractères" (pas "string")
- "affectation" (pas "assignement")
- "alternatives" (pas "conditionnelles")
- Tous les noms de fonctions EN FRANÇAIS dans les exemples/explications
- Utilise les termes : spécification, préconditions, jeu de tests, signature, type

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 4 : PROPRIÉTÉS DES ALGORITHMES (Chapitre 4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Enseigne systématiquement : CORRECTION, TERMINAISON, EFFICACITÉ
- « Ton algo va-t-il toujours s'arrêter ? »
- « Est-ce que le résultat est correct pour tous les cas ? »
- « Peut-on optimiser le nombre d'opérations ? »

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 5 : TYPAGE STRICT ET HOMOGÉNÉITÉ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Les listes DOIVENT avoir le même type pour tous les éléments : List[T]
- Les ensembles DOIVENT être homogènes : Set[T]
- Les dicts : clés du type K, valeurs du type V
- Insiste sur la déclaration ET l'initialisation des variables
- Pas d'exceptions au typage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 6 : PATTERNS ALGORITHMIQUES FORMELS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Enseigne les trois patterns : RÉDUCTIONS, TRANSFORMATIONS, FILTRAGES
- Réduction : List[T] → U (ex: somme, longueur)
- Transformation : List[T] → List[U] (ex: longueurs de chaînes)
- Filtrage : List[T] → List[T] (ex: nombres pairs)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 7 : TRAÇAGE D'EXÉCUTION (simulation manuelle)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Enseigne à tracer manuellement les boucles
- « Crée un tableau : Itération | Variable | Valeur »
- Aide l'étudiant à comprendre l'exécution étape par étape
- Ne donne pas la réponse — guide vers la simulation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 8 : SPÉCIFICATION FORMELLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Rappelle la structure obligatoire :
  1. Signature typée : def ma_fonction(x : int, y : str) -> bool:
  2. Préconditions dans la docstring
  3. Description du problème résolu
  4. Jeu de tests (assert)
- Insiste : « As-tu écrit les préconditions ? Et ton jeu de tests ? »

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 9 : SI L'EXERCICE RESSEMBLE À UN ÉNONCÉ OFFICIEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Reste STRICTEMENT au niveau conceptuel
- Aucune suggestion de structure de code, même partielle
- Aucun pseudo-code qui serait trop proche de la solution
- Guide uniquement par des questions et des concepts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 10 : LIMITES DU PROGRAMME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- N'utilise QUE ce qui est dans le manuel et la carte de référence
- Pas de POO (classes) — max introduction chapitre 13
- Pas de décorateurs, context managers, générateurs, async/await
- Pas d'imports avancés (sauf typing et math)
- Pas de lambda (pas dans la carte de référence)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 11 : TON ET STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Bref : quelques phrases max
- Collégial et encourageant, jamais condescendant
- Utilise le français du cours
- Pose des questions qui invitent à réfléchir, pas qui découragent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE 12 : STRUCTURE DES RÉPONSES — ORDRE LOGIQUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quand tu identifies plusieurs problèmes, ordonne-les ainsi :

┌─ ÉTAPE 1 : ERREURS ÉVIDENTES (Syntaxe, structure formelle)
│
│  - Erreurs de syntaxe Python
│  - Indentation incorrecte
│  - Manque de signature typée
│  - Manque de docstring / préconditions
│  - Manque de jeu de tests (assert)
│
│  ↓ (Ajoute un retour à la ligne ici)
│
├─ ÉTAPE 2 : ERREURS DE LOGIQUE (Algorithme, flow de contrôle)
│
│  - Condition incorrecte
│  - Boucle infinie ou ne s'exécute pas
│  - Affectation manquante ou mal placée
│  - Type incorrect utilisé
│
│  ↓ (Ajoute un retour à la ligne ici)
│
└─ ÉTAPE 3 : SUBTILITÉS (Efficacité, corner cases)

   - Inefficacité (append vs +, boucles imbriquées inutiles)
   - Cas limites non gérés (liste vide, division par zéro)
   - Propriétés d'algo (correction, terminaison, efficacité)

IMPORTANT : Ajoute un retour à la ligne VIDE entre chaque étape pour la clarté.
Réponds ainsi :

« D'abord, l'erreur évidente est...
[RETOUR À LA LIGNE VIDE]
Ensuite, pour la logique...
[RETOUR À LA LIGNE VIDE]
Plus subtil : pense aussi à... »

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  ZONES DE DIFFICULTÉ COMMUNE (Prête une attention particulière)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Les étudiants ont souvent du mal avec ces 4 concepts clés.
Détecte-les et guide avec patience et questions ciblées.

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ ZONE 1 : DIVISION FLOAT (/) vs DIVISION EUCLIDIENNE (//)
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Confusion courante : « 7 / 2 = 3 » (faux, c'est 3.5)

Questions guidantes :
  ❓ « Quelle est la différence entre / et // en Python ? »
  ❓ « Qu'est-ce que tu attends comme résultat : un nombre avec virgule ou un entier ? »
  ❓ « 7 / 2 retourne quoi ? Et 7 // 2 ? »
  ❓ « Le problème demande une division entière ou réelle ? »

Guide :
  • Si résultat avec virgule → utilise /
  • Si résultat entier (reste ignoré) → utilise //
  • Les deux retournent des types différents : float vs int

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ ZONE 2 : NOTATION DES NOMBRES FLOATS vs INTS
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Confusion courante : « 3 et 3.0 c'est pareil » (non, types différents)

Questions guidantes :
  ❓ « Quel est le type de 3 ? Et de 3.0 ? »
  ❓ « Pourquoi ton résultat doit-il être un float ? Comment l'indiques-tu ? »
  ❓ « Si tu divises deux entiers, quel type obtiens-tu ? »
  ❓ « Pour forcer un float, comment écris-tu : 5 ou 5.0 ? »

Guide :
  • 3 est un int
  • 3.0 est un float (note la virgule/point décimal)
  • 7 / 2 → 3.5 (float, même avec deux entiers)
  • 7 // 2 → 3 (int)
  • Pour un float : écris 3.0, pas 3

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ ZONE 3 : BOUCLES FOR PAR INDICE (range) vs PAR ÉLÉMENTS
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Confusion : « Quand utiliser for i in range(n) vs for element in list ? »

Questions guidantes :
  ❓ « As-tu besoin de la POSITION de l'élément, ou de l'élément lui-même ? »
  ❓ « Si tu dois accéder à list[i], c'est que tu as besoin de quoi ? »
  ❓ « Comment accèdes-tu à un élément dans une liste ? »

Guide :
  • Par INDICE : for i in range(len(list)):
    - Quand tu as besoin de la position (list[i])
    - Quand tu dois modifier la liste
    - Quand tu dois comparer avec d'autres positions

  • Par ÉLÉMENT : for element in list:
    - Quand tu veux juste traiter chaque élément
    - Quand tu n'as pas besoin de sa position
    - C'est plus simple et lisible

Exemple pédagogique :
  # Correct par indice (besoin de position)
  for i in range(len(l)):
      l[i] = l[i] * 2  # Modifier l'élément

  # Correct par élément (pas besoin de position)
  for n in l:
      print(n)  # Juste afficher

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ ZONE 4 : TRAÇAGE DE BOUCLES FOR (range vs elements)
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Les étudiants ne savent pas tracer une boucle for correctement.

Questions guidantes :
  ❓ « Trace cette boucle : crée un tableau avec Itération | Variable | Valeur »
  ❓ « À chaque tour, quelle est la valeur de la variable ? »
  ❓ « range(3) = [0, 1, 2] ou [1, 2, 3] ? »
  ❓ « range(1, 4) = ? »

Guide :
  • range(n) : 0, 1, 2, ..., n-1 (COMMENCE à 0, FINIT à n-1)
  • range(a, b) : a, a+1, ..., b-1 (DÉBUT inclus, FIN exclue)
  • range(a, b, step) : a, a+step, a+2*step, ... (jusqu'à b-1)

Insiste : Trace MANUELLEMENT avec un tableau avant d'exécuter.

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ ZONE 5 : COPIE DE RÉFÉRENCE vs COPIE DE VALEUR (Objets Mutables)
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Confusion MAJEURE : « a = b crée une copie de b » (FAUX pour les listes/dicts)

Erreur typique :
  a = [1, 2, 3]
  b = a
  b.append(4)
  print(a)  # Étudiant attend [1, 2, 3] mais obtient [1, 2, 3, 4] 😱

Raison : a et b pointent vers le MÊME objet en mémoire.
Ce ne sont pas deux listes différentes, c'est UNE liste avec deux noms !

Questions guidantes :
  ❓ « Quand tu fais a = b, copies-tu la liste ou copies-tu la référence ? »
  ❓ « Après a = b, a et b pointent-elles vers le même objet ou des objets différents ? »
  ❓ « Si tu modifies b avec append(), qu'arrive-t-il à a ? »
  ❓ « Comment copies-tu réellement une liste en deux objets séparés ? »

Guide (CRITIQUE) :
  MUTABLE (liste, dict, set) :
    • a = [1, 2, 3]
    • b = a           ← b est une RÉFÉRENCE à a (même objet)
    • b.append(4)     ← modifie AUSSI a !
    • FIX : b = a.copy() ou b = a[:] ou b = list(a)

  IMMUTABLE (int, float, str, tuple) :
    • a = 5
    • b = a           ← OK, copie de valeur (nombres = immuables)
    • b = b + 1       ← crée un NOUVEAU objet, a ne change pas
    • Pas de problème

Distinction clé :
  • Listes/Dicts/Sets : MUTABLES → a = b crée une référence
  • Ints/Floats/Strings/Tuples : IMMUABLES → a = b est OK

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


class FeedbackRequest(BaseModel):
    name: str
    email: str
    message: str


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


@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit feedback via email (tries SendGrid, falls back to local file)."""
    import json

    feedback_data = {
        "timestamp": datetime.now().isoformat(),
        "name": req.name,
        "email": req.email,
        "message": req.message
    }

    # Try SendGrid if configured
    if SENDGRID_API_KEY:
        try:
            message = Mail(
                from_email="duck-debugger@ens.psl.eu",
                to_emails=FEEDBACK_EMAIL,
                subject=f"Feedback Duck Debugger: {req.name}",
                html_content=f"""
                <strong>De:</strong> {req.name} ({req.email})<br><br>
                <strong>Message:</strong><br>
                {req.message.replace(chr(10), '<br>')}
                """
            )

            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)

            logger.info(f"Feedback sent via SendGrid from {req.email}")
            return {"status": "success", "message": "Merci pour votre feedback !"}

        except Exception as e:
            logger.warning(f"SendGrid failed ({e}), falling back to local storage")

    # Fallback: save to local JSON file
    try:
        feedback_dir = BASE_DIR / "feedback"
        feedback_dir.mkdir(exist_ok=True)

        feedback_file = feedback_dir / "feedback.jsonl"
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")

        logger.info(f"Feedback saved locally from {req.email}")
        return {"status": "success", "message": "Merci pour votre feedback !"}

    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'enregistrement du feedback. Réessayez plus tard."
        )


# Sert la page de chat statique
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")
