# 🚀 Duck Debugger — Checklist de Déploiement (Render.com)

**Version:** MVP v1.0  
**Date de dernier test:** 2026-08-23  
**Statut:** ✅ Prêt pour déploiement

---

## 📋 Pré-requis Render.com

- [x] Compte Render.com créé
- [ ] GitHub repository pushé avec tous les fichiers
- [ ] Secrets d'environnement préparés

---

## 🔧 Étape 1 : Préparer les secrets (Render Dashboard)

### Variables d'environnement à configurer:

```env
MISTRAL_API_KEY=your_mistral_api_key_here
CLASS_PASSWORD=Python101SU
MODEL_NAME=ministral-8b-latest
FALLBACK_MODEL=mistral-small-latest
MAX_REQUESTS_PER_DAY_PER_SESSION=50
MAX_REQUESTS_PER_DAY_GLOBAL=500
MAX_TOKENS_PER_REPLY=400
SENDGRID_API_KEY=  # Leave empty, use local fallback
```

⚠️ **IMPORTANT:** 
- Les clés API ne doivent JAMAIS être en git
- Générer une clé SendGrid valide depuis https://app.sendgrid.com/settings/api_keys
- La clé doit avoir les permissions "Mail Send"

---

## 🐳 Étape 2 : Créer le service sur Render

1. **Aller sur** https://dashboard.render.com/new/webservice
2. **Connecter** votre repository GitHub (duck-debugger)
3. **Configurer le service:**

   | Champ | Valeur |
   |-------|--------|
   | **Name** | duck-debugger |
   | **Region** | Oregon (us-west) ou Paris (eu-central) |
   | **Runtime** | Python 3 |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | Free (ou Starter si budget) |

4. **Ajouter les Environment Variables** depuis le champ "Environment"
   - Copier-coller toutes les variables ci-dessus

5. **Cliquer** "Create Web Service"

---

## ✅ Étape 3 : Vérifier le déploiement

Une fois déployé sur Render (URL: `https://duck-debugger-xxxxx.onrender.com`):

```bash
# 1. Health check
curl https://duck-debugger-xxxxx.onrender.com/health

# Réponse attendue:
{
  "status": "healthy",
  "global_requests_today": 0,
  "global_limit": 500
}

# 2. Tester l'authentification
curl -X POST https://duck-debugger-xxxxx.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"password":"Agris154", "session_id":"test", "history":[]}'

# 3. Tester le feedback (devrait sauvegarder en local ou envoyer email)
curl -X POST https://duck-debugger-xxxxx.onrender.com/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Test", 
    "email":"test@example.com", 
    "message":"Ceci est un test"
  }'
```

---

## 🌐 Étape 4 : Configurer un domaine personnalisé (optionnel)

1. Aller à **Settings** → **Custom Domains**
2. Ajouter `duck-debugger.ens.psl.eu` (si vous avez accès au DNS)
3. Configurer les enregistrements DNS chez votre hébergeur

---

## 📊 Architecture déployée

```
┌─────────────────────────────────────────────────────────────┐
│                    Render.com (Dyno)                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Server (main.py)                            │  │
│  │  - Chat endpoint (POST /chat) → Mistral API          │  │
│  │  - Feedback endpoint (POST /feedback) → Fallback     │  │
│  │  - Health check (GET /health)                        │  │
│  │  - Static files (GET / → static/index.html)          │  │
│  │  - Rate limiting (in-memory per session)             │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  File Storage (Feedback, Logs)                       │  │
│  │  - feedback/feedback.jsonl                           │  │
│  │  - logs/ (optionnel, pour analytics futures)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ⚠️ NOTE: Render fournit 50GB de stockage ephemeral        │
│  Les fichiers persistants (feedback) disparaîtront         │
│  au redémarrage du dyno. Pour persister, utiliser:         │
│  - Render PostgreSQL ($7/mois)                              │
│  - AWS S3 (gratuit avec tier étudiant)                     │
│  - Upstash Redis (rate limiting)                           │
└─────────────────────────────────────────────────────────────┘

                           ↓
                           
┌─────────────────────────────────────────────────────────────┐
│              Mistral API (tierce partie)                    │
│  Modèles: ministral-8b-latest, mistral-small-latest         │
│  Streaming en SSE + fallback intelligent                    │
└─────────────────────────────────────────────────────────────┘

                           ↓
                           
┌─────────────────────────────────────────────────────────────┐
│         Client (Navigateur étudiant)                        │
│  static/index.html                                          │
│  - Chat interface                                           │
│  - Lien vers carte de référence                             │
│  - Lien vers CS50.ai                                        │
│  - Formulaire feedback (POST → /feedback)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Troubleshooting déploiement

### Erreur: "Module not found"
→ Vérifier `requirements.txt` complète

### Erreur: "MISTRAL_API_KEY not found"
→ Ajouter la variable dans Render Environment

### Timeout lors de chat
→ Augmenter le timeout (`Web Service Settings` → `Timeout`)
→ Ou augmenter les ressources (passer de Free à Starter)

### Feedback ne s'envoie pas
→ SendGrid API key invalide (HTTP 403)
→ Solution: vérifier la clé sur https://app.sendgrid.com
→ OU utiliser le fallback local (fichier `feedback/feedback.jsonl`)

### "Health check failed"
→ Render essaie `GET /` mais le répertoire `static/` doit exister
→ Vérifier que `static/index.html` est bien en git

---

## 📱 Documentation pour les étudiants

URL de l'application une fois déployée:  
**https://duck-debugger-xxxxx.onrender.com**

Mot de passe: `Agris154` (à fournir en cours)

### Utilisation:
1. Ouvrir l'URL dans un navigateur
2. Entrer le mot de passe de classe
3. Décrire le bug ou coller le code + message d'erreur
4. Duck posera des questions pour vous aider
5. Optionnel: envoyer des suggestions via le formulaire

---

## 🔐 Sécurité

- [x] Mot de passe de classe requis pour chat
- [x] Pas d'exposition des clés API côté client
- [x] Rate limiting par session + global
- [x] Logging des requêtes
- [ ] HTTPS (gratuit via Render)
- [ ] CORS limitée (à configurer si API tierce)

---

## 📈 Monitoring post-déploiement

Chaque jour, checker:
1. `/health` endpoint
2. `curl https://duck-debugger-xxx/admin/status?password=Agris154`
   → Voir % d'utilisation du quota Mistral
3. Fichier `feedback/feedback.jsonl` pour suggestions étudiants

---

## 🚨 Limites connues (MVP)

- **Stockage ephemeral:** Feedback disparaît au redémarrage Render
- **Rate limiting simple:** En mémoire, pas entre plusieurs instances
- **Pas de persistance:** Pas de base de données
- **Pas de dashboard:** Les stats doivent être consultées manuellement

Prochaine version: PostgreSQL + Redis + Dashboard analytics

---

## ✨ Checklist finale avant production

- [x] `.env` configuré localement et testé
- [x] `static/index.html` élégant et responsive
- [x] Lien vers carte de référence (artifact)
- [x] Lien vers CS50.ai
- [x] Formulaire feedback fonctionnel
- [x] Chat streaming avec fallback Mistral
- [x] Health check et admin status endpoint
- [ ] Repository pushé sur GitHub
- [ ] Secrets Render configurés
- [ ] Service créé et déployé
- [ ] Domaine personnalisé configuré (optionnel)
- [ ] Documentation partagée avec étudiants

---

**Questions?** Email: jacques.fattaccioli@ens.psl.eu

🦆 Bon débogage!
