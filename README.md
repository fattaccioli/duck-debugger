# Duck Debugger — Python 101

Assistant de débogage socratique pour l'enseignement Python 101, adossé à
l'API Mistral (tier gratuit "Experiment" ou payant à très bas coût).

## Local

```bash
pip install -r requirements.txt
cp .env.example .env   # puis éditer .env avec votre clé API
export $(cat .env | xargs)
uvicorn main:app --reload
```

Ouvrir http://localhost:8000

## Contenu pédagogique

- Coller le manuel dans `prompts/manuel.md`
- Coller le feuillet d'exercices dans `prompts/exercices.md`

Ces fichiers sont injectés tels quels dans le system prompt à chaque requête
(pas de RAG nécessaire vu la taille du contexte des modèles Mistral).

## Déploiement gratuit — Render.com

(Hugging Face Spaces exige désormais un compte payant pour tout Space qui
exécute du code — Docker ou Gradio — seuls les Spaces statiques restent
gratuits. Render reste gratuit pour un vrai service web Python.)

1. Pousser ce dossier dans un repo GitHub.
2. Sur render.com, "New" → "Web Service" → connecter le repo.
3. Runtime : Python 3. Build command : `pip install -r requirements.txt`.
   Start command : `uvicorn main:app --host 0.0.0.0 --port $PORT`
   (Render injecte `$PORT`, ne pas coder un port fixe).
4. Plan : Free.
5. Dans Environment → ajouter les secrets `MISTRAL_API_KEY` et
   `CLASS_PASSWORD`.
6. Déploiement automatique à chaque push. L'app est servie sur l'URL
   `https://<nom-du-service>.onrender.com`.

Note : le service gratuit se met en veille après 15 min d'inactivité
(redémarrage à froid ~30-60s au message suivant) — sans impact réel pour un
usage pédagogique.

## Réglages de coût / rate limiting

- `MAX_REQUESTS_PER_DAY` (défaut 50) : plafond par session, protège à la fois
  votre budget et le rate limit Mistral.
- `MAX_TOKENS_PER_REPLY` (défaut 400) : borne la longueur (donc le coût) de
  chaque réponse.
- `MODEL_NAME` / `FALLBACK_MODEL` : bascule automatique si le modèle
  principal échoue (rate limit, indisponibilité).

Le rate limiting actuel est en mémoire (dictionnaire Python) — suffisant pour
une seule instance. Si vous scalez à plusieurs instances (peu probable pour
un usage pédagogique), remplacer par Redis (Upstash a un tier gratuit).
