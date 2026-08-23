# 🎯 Roadmap Analytics — Collecte & Analyse d'Erreurs

**Version:** Planifiée (post-MVP)  
**Priorité:** Haute (données pédagogiques essentielles)  
**Durée estimée:** 2-3 jours de développement

---

## 📊 Objectif

Collecter automatiquement les **types d'erreurs** que les étudiants font pour :
- Identifier les concepts mal compris
- Adapter le contenu des cours/TDs
- Mesurer l'efficacité du duck-debugger
- Identifier les erreurs les plus fréquentes par thème

---

## 🏗️ Architecture Proposée

### Phase 1 : Collecte Basique (Facile, ~1 jour)

**Logs côté serveur** :

```python
# Dans main.py, ajouter un logger spécialisé
LOG_DIR = Path("logs")
ERROR_LOG = LOG_DIR / "errors.jsonl"  # JSON Lines (une erreur par ligne)

# Structure de chaque log :
{
  "timestamp": "2025-01-24T14:32:15Z",
  "session_id": "user123",
  "error_type": "division_confusion",  # Catégorie détectée
  "error_detail": "Utilisé / au lieu de //",
  "concept": "division",
  "severity": "logic",  # syntax | logic | efficiency | pedagogical
  "student_code": "[troncated après 500 chars pour confidentialité]",
  "was_corrected": false  # true si l'étudiant l'a fixé après
}
```

**Intégration** :

```python
# Dans endpoint /chat, après détection d'erreur
def log_error(session_id, error_type, error_detail, code_snippet):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "error_type": error_type,
        "error_detail": error_detail,
        "concept": detect_concept(error_type),
        "severity": classify_severity(error_type),
        "student_code": code_snippet[:500],
        "was_corrected": False
    }
    ERROR_LOG.open("a").write(json.dumps(log_entry) + "\n")
```

### Phase 2 : Détection Structurée (Moyen, ~1 jour)

Ajouter des **marqueurs de détection** dans le system prompt :

Le modèle annote ses réponses :

```
[DETECTED: division_confusion]
Quelle est la différence entre / et // ?
```

**Parser côté serveur** :

```python
def extract_detection_markers(response_text):
    pattern = r"\[DETECTED: (\w+)\]"
    return re.findall(pattern, response_text)
```

### Phase 3 : Dashboard Analytics (Avancé, ~1 jour)

**Endpoint de statistiques** :

```python
@app.get("/admin/analytics")
async def analytics(password: str):
    # Authentifier admin (même password de classe)
    # Charger les logs
    # Générer statistiques
    return {
        "total_errors": 1247,
        "errors_by_type": {
            "division_confusion": 345,
            "indentation": 234,
            "loop_misunderstanding": 156,
            ...
        },
        "errors_by_concept": {
            "division": 345,
            "loops": 156,
            "functions": 89,
            ...
        },
        "trend": "division errors improving over time",
        "top_5": [...]
    }
```

**Dashboard HTML** :

- Graphique : Erreurs par type
- Graphique : Évolution temporelle
- Tableau : Concepts mal maîtrisés
- Ranking : Étudiants qui progressent

---

## 🔐 Considérations Importantes

### Confidentialité / RGPD

- ✅ Ne pas stocker le nom de l'étudiant (utiliser `session_id` anonyme)
- ✅ Tronquer le code après 500 caractères (pas de code complet)
- ✅ Supprimer les logs après X mois (rétention)
- ✅ Permettre aux étudiants d'opt-out

### Structure des Logs

```
logs/
  errors.jsonl          # Tous les logs (format JSON Lines)
  analytics/
    summary.json        # Stats agrégées
    by_date/
      2025-01-24.json
      2025-01-25.json
```

**Rotation** : Archiver les logs mensuels (gzip) pour ne pas avoir un fichier énorme

---

## 📈 Catégories d'Erreurs à Détecter

**Syntaxe :**
- `indentation_error`
- `missing_colon`
- `syntax_error_general`

**Types :**
- `division_confusion` (/ vs //)
- `float_int_notation` (3 vs 3.0)
- `type_mismatch`

**Boucles :**
- `loop_by_index_vs_element`
- `range_misunderstanding` (range(n) ne va pas jusqu'à n)
- `loop_never_executes`
- `infinite_loop`

**Logique :**
- `condition_inverted`
- `accumulator_not_initialized`
- `off_by_one`

**Structure :**
- `no_function_signature`
- `no_preconditions`
- `no_test_suite`

**Références :**
- `reference_vs_copy` (a = b sur listes)

**Efficacité :**
- `list_concat_inefficient` (+ vs append)

---

## 🎯 Cas d'Usage pour l'Enseignant

**Après 2 semaines de cours :**

```
Statistiques :

Erreurs les plus fréquentes :
1. division_confusion (23%)        ← Revoir la distinction / vs //
2. loop_by_index_vs_element (18%)  ← Revoir quand utiliser chaque type
3. indentation_error (15%)         ← C'est normal (débutants)
4. reference_vs_copy (12%)         ← NOUVEAU - ajouter à TD2

Concepts non maîtrisés :
- "division" (345 erreurs) → Faire un mini-quiz
- "loops" (156 erreurs) → Ajouter exercices d'entraînement
- "references" (120 erreurs) → Créer une séance dédiée

Progrès :
- Les erreurs d'indentation diminuent (6% semaine 1 → 3% semaine 2)
- Les erreurs de division stagnent (besoin d'intervention)
```

---

## 🛠️ Implementation Steps

### 1. Backend Logging (Simple)
```
- Ajouter logger JSON dans main.py
- Ajouter marqueurs [DETECTED: xxx] dans system prompt
- Parser les réponses pour extraire détections
```

### 2. Analytics Endpoint (Moyen)
```
- Créer /admin/analytics?password=XXX
- Charger errors.jsonl
- Agréger par type/concept/date
```

### 3. Dashboard Frontend (Complexe)
```
- HTML avec charts (Chart.js ou simple SVG)
- Filtres par date/concept
- Export CSV
```

---

## 📋 Checklist pour MVP Futur

- [ ] Ajouter logger JSON structure
- [ ] Ajouter marqueurs [DETECTED: ...] au system prompt
- [ ] Parser les réponses pour détections
- [ ] Créer endpoint /admin/analytics
- [ ] Créer dashboard HTML basique
- [ ] Tester la collecte sur 1 semaine réelle
- [ ] Ajouter documentation pour l'enseignant
- [ ] Cleanup/Archivage des logs anciens

---

## 💾 Données Brutes Example

```jsonl
{"timestamp": "2025-01-24T14:32:15Z", "session_id": "s123", "error_type": "division_confusion", "error_detail": "Used / instead of //", "concept": "division", "severity": "logic"}
{"timestamp": "2025-01-24T14:45:22Z", "session_id": "s124", "error_type": "loop_by_index_vs_element", "error_detail": "for i in list instead of for i in range(len(list))", "concept": "loops", "severity": "logic"}
{"timestamp": "2025-01-24T15:12:33Z", "session_id": "s125", "error_type": "no_test_suite", "error_detail": "No assert tests provided", "concept": "structure", "severity": "pedagogical"}
```

---

## 🚀 Priorité de Développement

1. **HIGH** : Logger basique + endpoint analytics (donne 80% de valeur)
2. **MEDIUM** : Dashboard HTML (visualisation)
3. **LOW** : Export CSV, tendances avancées, ML classification

---

## Notes Futures

- Considérer une **base de données** (SQLite) au lieu de JSON pour gros volumes
- Intégrer **Grafana** ou **Metabase** pour analytics avancée
- Ajouter **feedback automatique** : si une erreur dépasse 20%, notifier l'enseignant
- Étudier les **patterns** : certains erreurs arrivent-elles ensemble ?
