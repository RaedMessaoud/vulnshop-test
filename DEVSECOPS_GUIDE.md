# 🔒 Pipeline DevSecOps - Guide Complet

## 📋 Vue d'ensemble

Cette pipeline DevSecOps simple et fonctionnelle automatise les tests de sécurité de votre application Flask. Elle comprend:

- **SAST (Static):** Analyse statique avec Bandit
- **SCA (Dépendances):** Vérification des packages vulnérables avec Safety
- **DAST (Dynamique):** Tests de sécurité en runtime (SQL injection, auth, etc.)
- **Rapport:** Génération automatique d'un rapport de sécurité avec recommandations

---

## 🚀 Démarrage Rapide

### 1. **Configuration initiale**

```bash
# Cloner/Initialiser le projet
cd ~/Desktop/projet\ dso

# Installer les dépendances
pip install -r requirements.txt
pip install bandit safety pytest requests
```

### 2. **Exécuter la pipeline localement**

#### Option A: Pipeline complète (via shell script)
```bash
# À venir: Script shell pour exécuter tous les scans localement
```

#### Option B: Tests individuels

```bash
# 1. SAST - Bandit
bandit -r shop_vuln.py -f json -o bandit-report.json

# 2. SCA - Safety
safety check -r requirements.txt > safety-output.txt

# 3. Démarrer l'application (terminal 1)
python shop_vuln.py
# → Accédez à http://localhost:5000

# 4. DAST - Tests dynamiques (terminal 2)
pytest .github/workflows/test_security.py -v

# 5. Générer le rapport
python generate_report.py
```

### 3. **Déclencher la pipeline sur GitHub**

La pipeline se déclenche automatiquement sur:
- ✅ Tout `push` sur les branches `main`, `master`, `develop`
- ✅ Toute `pull_request` vers `main`
- ✅ Manuellement via "Actions" > "DevSecOps Pipeline" > "Run workflow"

---

## 📊 Structure de la Pipeline

```
DevSecOps Pipeline
│
├─ 📥 Checkout & Setup
│  ├─ Clone repository
│  └─ Setup Python 3.11
│
├─ 🔍 PHASE 1: SAST (Bandit)
│  ├─ Scan du code Python
│  └─ Rapport JSON: bandit-report.json
│
├─ 📦 PHASE 2: SCA (Safety)
│  ├─ Vérif dépendances
│  └─ Rapport texte: safety-output.txt
│
├─ 🚀 PHASE 3: DAST (Tests Dynamiques)
│  ├─ Démarrage app Flask
│  ├─ Tests SQL injection
│  ├─ Tests authentication
│  └─ Rapport texte: dast-results.txt
│
├─ 📊 PHASE 4: Rapport Consolidé
│  ├─ Parse tous les résultats
│  ├─ Génère Markdown
│  └─ Affiche rapport: SECURITY_REPORT.md
│
└─ 📤 Upload Artefacts
   └─ GitHub Artifacts (7 jours rétention)
```

---

## 📁 Fichiers Clés

### Workflow GitHub Actions
- **[`.github/workflows/devsecops.yml`](.github/workflows/devsecops.yml)**
  - Orches tration complète de la pipeline
  - 6 phases: Setup, SAST, SCA, DAST, Rapport, Upload

### Scripts Python
- **[`generate_report.py`](generate_report.py)** ⭐ NOUVEAU
  - Classe `SecurityReportGenerator`
  - Parse Bandit, Safety, DAST
  - Génère rapport Markdown formaté
  - Inclut recommandations de correction

- **[`.github/workflows/test_security.py`](.github/workflows/test_security.py)** 🔄 AMÉLIORÉ
  - 9 tests DAST complets
  - Détection SQL injection (3 types)
  - Tests authentication & session
  - Tests input validation
  - Performance tests

### Configuration
- **[`requirements.txt`](requirements.txt)**
  - Flask, pytest, bandit, safety

- **[`shop_vuln.py`](shop_vuln.py)**
  - Application Flask intentionnellement vulnérable (pour démo)
  - ⚠️ À ne PAS utiliser en production

---

## 🎯 Cas d'Usage

### Cas 1: Vérifier la sécurité du code
```bash
# Avant de faire un commit
python generate_report.py

# Vérifier les vulnérabilités Bandit
cat SECURITY_REPORT.md
```

### Cas 2: Valider fix de vulnérabilité
```bash
# Après correction du code
git add .
git push  # Déclenche pipeline automatiquement

# Vérifier les résultats dans GitHub Actions
```

### Cas 3: Audit complet avec rapport
```bash
# Depuis votre poste (simule GitHub Actions):

# 1. Scans de sécurité
bandit -r shop_vuln.py -f json -o bandit-report.json
safety check -r requirements.txt > safety-output.txt

# 2. Tests DAST
python shop_vuln.py &  # Démarrer app
sleep 5
pytest .github/workflows/test_security.py -v
pkill -f shop_vuln.py

# 3. Générer rapport
python generate_report.py

# 4. Consulter le rapport
cat SECURITY_REPORT.md
```

---

## 📋 Format du Rapport

Le rapport `SECURITY_REPORT.md` inclut:

### Header
- 🕐 Date/heure génération
- 🏷️ Repository, branche, commit
- 📌 État global

### Summary
- 🔴 Vulnérabilités critiques (count)
- 🟠 Vulnérabilités hautes
- 🟡 Vulnérabilités moyennes
- 🟢 Vulnérabilités basses
- **Tableau récapitulatif**

### Findings
- ✅ Groupées par sévérité
- 📝 Détails pour chaque issue
- 📄 Code preview (si applicable)

### Recommendations
- 🔴 Actions immédiates pour critiques
- 🟠 Actions urgentes pour hautes
- 🟡 Planification sprint pour moyennes
- 📋 Bonnes pratiques de sécurité

### Tools Info
- 🛠️ Liste des outils utilisés
- 📖 Ressources (OWASP, documentation)

---

## 🔧 Configuration

### Ajouter des tests SAST supplémentaires

Dans `.github/workflows/devsecops.yml`, ajouter:
```yaml
- name: 🔍 SAST - Pylint Security
  run: |
    pip install pylint
    pylint shop_vuln.py --load-plugins=pylint.extensions.security || true
```

### Modifier le timeout des DAST tests
Dans `test_security.py`:
```python
TIMEOUT = 15  # Augmenter de 10 à 15 secondes
```

### Activer l'échec sur vulnérabilités critiques
Dans `.github/workflows/devsecops.yml`:
```yaml
- name: 🎯 Fail on Critical Issues
  run: |
    if grep -q '"severity": "HIGH"' bandit-report.json; then
      echo "❌ Critical issues found"
      exit 1
    fi
```

---

## ✅ Validation Checklist

- [ ] Fichiers créés/modifiés:
  - [x] `generate_report.py` ✅
  - [x] `.github/workflows/devsecops.yml` ✅
  - [x] `.github/workflows/test_security.py` ✅

- [ ] Workflow fonctionne:
  - [ ] Push sur branche test → Pipeline démarre
  - [ ] Tous les outils s'exécutent sans erreur
  - [ ] Rapport généré et visible dans les logs

- [ ] Artefacts uploadés:
  - [ ] `bandit-report.json` disponible ✅
  - [ ] `SECURITY_REPORT.md` disponible ✅
  - [ ] `dast-results.txt` disponible ✅

- [ ] Rapport affiché:
  - [ ] Format Markdown clair
  - [ ] Statistiques visuelles (emojis)
  - [ ] Recommandations présentes

---

## 🐛 Troubleshooting

### Erreur: "Application failed to start"
```bash
# Vérifier que le port 5000 est disponible
lsof -i :5000

# Tuer le processus occupant le port
kill -9 <PID>
```

### Erreur: "Bandit not found"
```bash
pip install bandit
```

### Rapport vide
```bash
# Vérifier que les fichiers de résultats existent
ls -la *.json *.txt

# Vérifier les permissions
chmod +x generate_report.py
```

### Tests DAST timeouts
```bash
# Augmenter le timeout dans test_security.py
# et aussi dans devsecops.yml
TIMEOUT = 15
```

---

## 📚 Ressources

- 📖 **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- 🔐 **Bandit Docs**: https://bandit.readthedocs.io/
- 🛡️ **Safety Docs**: https://github.com/pyupio/safety
- 🧪 **Pytest Docs**: https://docs.pytest.org/

---

## 📞 Support

En cas de problème:
1. Vérifier que Python 3.11+ est installé
2. Vérifier que pip dependencies sont à jour
3. Consulter les logs GitHub Actions
4. Vérifier les chemins des fichiers (paths abs vs rel)

---

## ✨ Points Clés pour la Démo au Professeur

1. **Pipeline Automatique** 🤖
   - Se déclenche à chaque push
   - Aucune intervention manuelle

2. **3 Outils de Sécurité** 🔧
   - SAST (Bandit) pour analyse statique
   - SCA (Safety) pour dépendances
   - DAST (Tests Python) pour dynamique

3. **Rapport Clair et Professionnel** 📊
   - Format Markdown lisible
   - Statistiques visuelles avec emojis
   - Recommandations concrètes

4. **Intégration GitHub Complète** 🔗
   - Workflow GitHub Actions
   - Artefacts téléchargeables
   - Logs visibles en temps réel

5. **Facile à Reproduire** ✅
   - Scripts fournis
   - Documentation complète
   - Fonctionnement sans dépendances externes

---

**🎯 Objectif:** Une pipeline DevSecOps simple, fonctionnelle et professionnelle pour démontrer:
- Automatisation de la sécurité
- Scan continu du code
- Reporting structuré
- Branding DevSecOps
