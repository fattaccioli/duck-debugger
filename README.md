# 🦆 Duck Debugger — Assistant de Débogage Socratique

Un outil pédagogique pour le cours **Python 101** (Éléments de Programmation, Sorbonne Université) qui guide les étudiants à déboguer leur code via des questions socratiques, inspiré par la méthode du canard en plastique (*rubber duck debugging*).

---

## 🎯 Objectif

Duck Debugger aide les étudiants à :
- **Localiser** les bugs sans donner directement la solution
- **Comprendre** les concepts fondamentaux (division, boucles, listes, etc.)
- **Progresser** via des questions guidées plutôt que des réponses toutes faites
- **Apprendre** les bonnes pratiques (typage strict, spécification, tests)

### Pédagogie

L'outil applique la méthode socratique : **"Je ne te donne jamais la réponse. Je t'aide à la trouver toi-même."**

Zones pédagogiques couvertes :
1. **Division entière** (/ vs //)
2. **Notation décimale** (3 vs 3.0)
3. **Boucles** (for par indice vs par élément)
4. **Traçage** (simulation manuelle d'algorithmes)
5. **Copie de référence** (mutable objects comme listes)

---

## ⚡ Démarrage rapide

### Localement

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API Mistral et SendGrid

# 3. Lancer le serveur
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 4. Ouvrir http://127.0.0.1:8000 dans un navigateur
```

### Sur Render.com (Production)

Voir [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) pour la procédure complète.

**Résumé rapide :**
1. Push le repo sur GitHub
2. Créer un Web Service sur Render
3. Ajouter les variables d'environnement
4. Cliquer "Deploy"

---

## 🛠️ Configuration

### Variables d'environnement (.env)

```env
# Mistral API
MISTRAL_API_KEY=your_mistral_key_here
MODEL_NAME=ministral-8b-latest          # Modèle principal
FALLBACK_MODEL=mistral-small-latest     # Fallback en cas de rate limit

# Classe
CLASS_PASSWORD=Agris154                 # Mot de passe d'accès

# Rate limiting
MAX_REQUESTS_PER_DAY_PER_SESSION=50    # Par étudiant
MAX_REQUESTS_PER_DAY_GLOBAL=500        # Total quotidien
MAX_TOKENS_PER_REPLY=400               # Chars max par réponse

# Email (optionnel)
SENDGRID_API_KEY=your_sendgrid_key      # Pour les emails de feedback
```

---

## 📚 Architecture

```
duck-debugger/
├── main.py                      # Backend FastAPI
├── static/
│   └── index.html              # Frontend (chat + feedback)
├── prompts/
│   ├── manuel.md               # Manuel du cours (injecté)
│   └── exercices.md            # Feuille d'exercices (injectée)
├── feedback/                    # Suggestions étudiants (auto)
├── logs/                        # Analytics d'erreurs (futur)
├── requirements.txt             # Dépendances Python
├── .env                         # Secrets (ne jamais committer)
├── .gitignore                   # Fichiers ignorés
├── DEPLOYMENT_CHECKLIST.md     # Guide de déploiement complet
├── ROADMAP_ANALYTICS.md        # Feuille de route analytics
└── README.md                    # Ce fichier
```

---

## 🚀 Endpoints

### Pour les étudiants

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/` | Page de chat |
| `POST` | `/chat` | Envoyer un message (streaming) |
| `POST` | `/feedback` | Envoyer une suggestion |

### Pour l'admin

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| `GET` | `/health` | — | Vérifier la santé |
| `GET` | `/admin/status` | PASSWORD | Voir le quota |

### Exemple : Requête chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "password": "Agris154",
    "session_id": "student-001",
    "history": [
      {"role": "user", "content": "7 / 2 retourne 3.5 mais je veux 3"}
    ]
  }'
```

Réponse (streaming SSE) :
```
data: Quelle
data: est
data: la
data: différence
...
data: [DONE]
```

---

## 🔒 Sécurité

- ✅ Mot de passe requis pour le chat
- ✅ Pas d'exposition des clés API côté client
- ✅ Rate limiting (par session + global)
- ✅ Logging des requêtes
- ⚠️ Stockage ephemeral sur Render (ajoutez PostgreSQL pour persister)

---

## 📊 Monitoring

### Vérifier le quota

```bash
curl https://your-app.onrender.com/admin/status?password=Agris154 | python -m json.tool
```

### Lire les suggestions étudiants

```bash
cat feedback/feedback.jsonl | python -m json.tool
```

---

## 🎓 Pour les enseignants

### Déployer

Voir [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

### Personnaliser

1. Éditer `prompts/manuel.md` (votre manuel du cours)
2. Éditer `prompts/exercices.md` (votre feuille d'exercices)
3. Push sur GitHub → Render redéploie automatiquement

### Analytics (Roadmap Phase 2)

Voir [ROADMAP_ANALYTICS.md](ROADMAP_ANALYTICS.md) pour les statistiques sur les erreurs étudiantes.

---

## 🐛 Troubleshooting

| Problème | Solution |
|----------|----------|
| "Mot de passe incorrect" | Vérifier CLASS_PASSWORD dans .env |
| "Limite quotidienne atteinte" | Augmenter MAX_REQUESTS_PER_DAY_GLOBAL |
| Chat timeout | Vérifier la clé Mistral API |
| Feedback ne s'envoie pas | SendGrid key invalide (fallback local en place) |

---

## 📦 Stack

- **Backend:** FastAPI + Uvicorn
- **LLM:** Mistral API
- **Frontend:** Vanilla JS (pas de framework)
- **Streaming:** Server-Sent Events
- **Email:** SendGrid (+ fallback JSON)
- **Hosting:** Render.com

---

## ✨ Checklist Déploiement

- [x] Frontend avec feedback form
- [x] Backend avec streaming et fallback
- [x] Rate limiting
- [x] Documentation
- [ ] Push sur GitHub
- [ ] Déployer sur Render
- [ ] Configurer domaine personnalisé (optionnel)
- [ ] Tester avec les étudiants

---

**Version:** MVP 1.0  
**Dernière mise à jour:** 2026-08-23  
**Inspiré par:** CS50.ai

🦆 Bon débogage!
