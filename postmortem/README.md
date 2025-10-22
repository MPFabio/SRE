# Interface Post-Mortems SRE

Interface web Flask pour la gestion et visualisation des post-mortems d'incidents avec un format structuré et professionnel.

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.8+
- pip3

### Installation et Démarrage

```bash
# Se déplacer dans le répertoire
cd postmortem

# Rendre le script exécutable
chmod +x start_postmortem.sh

# Démarrer l'application
./start_postmortem.sh
```

L'interface sera accessible sur : **http://localhost:5000**

## 📋 Fonctionnalités

### Interface Web
- **Liste des post-mortems** avec statuts et métadonnées
- **Visualisation détaillée** avec format structuré
- **Création de nouveaux post-mortems** via formulaire
- **Interface responsive** et professionnelle
- **API REST** pour l'intégration

### Format Structuré
Chaque post-mortem suit le format standard SRE :

```
POSTMORTEM : [Titre de l'incident]
• Owner : [Responsable(s)]
• Shared with : [Destinataires]
• Status : [Brouillon/Final/En cours de révision]
• Incident date : [Date et heure]
• Published : [Date]

EXECUTIVE SUMMARY
• Impact : [Description de l'impact]
• Root cause : [Cause principale]

PROBLEM SUMMARY
• Duration of problem
• Products affected
• % of product affected
• User impact
• Revenue impact
• Detection
• Resolution

IMPACT
• User impact
• Revenue impact
• Team impact

ROOT CAUSES AND TRIGGER
• Technical cause
• Trigger
• System reaction
• Missing protections

TIMELINE / RECOVERY EFFORTS
• Chronologie détaillée des événements

LESSONS LEARNED
• Things that went well
• Things that went poorly
• Where we got lucky

ACTION ITEMS
• Actions préventives et correctives
• Priorités et responsables

GLOSSARY
• Définitions des termes techniques

APPENDIX
• Informations complémentaires
```

## 🛠️ Utilisation

### Créer un Post-Mortem

1. Accédez à http://localhost:5000
2. Cliquez sur "Nouveau Post-Mortem"
3. Remplissez le formulaire structuré
4. Sauvegardez le post-mortem

### Visualiser un Post-Mortem

1. Accédez à la liste des post-mortems
2. Cliquez sur "Voir" pour un post-mortem
3. Consultez la présentation structurée

### API REST

```bash
# Lister tous les post-mortems
curl http://localhost:5000/api/postmortems

# Récupérer un post-mortem spécifique
curl http://localhost:5000/api/postmortem/incident_20241222_143000

# Créer un nouveau post-mortem
curl -X POST http://localhost:5000/api/create \
  -H "Content-Type: application/json" \
  -d '{"title": "Nouvel incident", ...}'
```

## 📁 Structure des Données

### Format JSON
Les post-mortems sont stockés en JSON dans `data/postmortems/` :

```json
{
  "id": "incident_20241222_143000",
  "title": "Titre de l'incident",
  "owner": "Équipe SRE",
  "status": "Final",
  "incident_date": "2024-12-22T14:30:00Z",
  "executive_summary": {
    "impact": "Description de l'impact",
    "root_cause": "Cause principale"
  },
  "problem_summary": {
    "duration": "2h30",
    "products_affected": "Service X",
    "user_impact": "15 000 utilisateurs affectés"
  },
  "impact": {
    "user_impact": {
      "description": "Impact sur les utilisateurs",
      "requests_lost": "45 000 requêtes perdues"
    }
  },
  "timeline": [
    {
      "time": "14:30",
      "title": "Début de l'incident",
      "description": "Description de l'événement"
    }
  ],
  "action_items": [
    {
      "description": "Action à entreprendre",
      "type": "prevent",
      "priority": "P0",
      "owner": "Équipe SRE",
      "tracking_bug": "SRE-123"
    }
  ]
}
```

## 🎨 Interface

### Design
- **Bootstrap 5** pour l'interface responsive
- **Font Awesome** pour les icônes
- **Thème professionnel** avec couleurs SRE
- **Navigation intuitive** et claire

### Fonctionnalités UI
- **Statistiques** en temps réel
- **Filtres** par statut
- **Recherche** dans les post-mortems
- **Export** en PDF (à venir)

## 🔧 Configuration

### Variables d'Environnement
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
export POSTMORTEM_DIR=data/postmortems
```

### Personnalisation
- **Thème** : Modifiez `templates/base.html`
- **Format** : Adaptez `templates/postmortem.html`
- **API** : Étendez `app.py`

## 📊 Exemple de Post-Mortem

Un exemple complet est fourni dans `data/postmortems/incident_20241222_143000.json` :

- **Incident** : Panne du service URL Shortener
- **Durée** : 2h30
- **Impact** : 15 000 utilisateurs, 45 000 requêtes perdues
- **Cause** : Saturation de la base de données PostgreSQL
- **Actions** : 6 actions préventives et correctives

## 🚀 Déploiement

### Production
```bash
# Configuration de production
export FLASK_ENV=production
export FLASK_DEBUG=0

# Utilisation de Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🔗 Intégration

### Avec le Lab SRE
L'interface s'intègre parfaitement avec le lab SRE :

1. **Simulation d'incidents** → Création automatique de post-mortems
2. **Métriques Splunk** → Données d'impact dans les post-mortems
3. **Monitoring** → Timeline des événements

### API d'Intégration
```python
import requests

# Créer un post-mortem programmatiquement
response = requests.post('http://localhost:5000/api/create', json={
    'title': 'Incident automatique',
    'owner': 'Système de monitoring',
    'status': 'Brouillon',
    'incident_date': '2024-12-22T14:30:00Z'
})
```

## 📚 Ressources

- **Format SRE** : [Google SRE Book](https://sre.google/sre-book/postmortem-culture/)
- **Best Practices** : [Post-Mortem Guidelines](https://sre.google/sre-book/postmortem-culture/)
- **Flask Documentation** : [Flask Docs](https://flask.palletsprojects.com/)

---

**Interface Post-Mortems SRE**  
**Version 1.0 - Interface web professionnelle pour la gestion des incidents**
