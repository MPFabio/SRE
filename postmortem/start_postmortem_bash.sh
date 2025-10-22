#!/bin/bash

# Script de démarrage de l'application Flask pour les post-mortems (Git Bash)
# Interface web pour la gestion et visualisation des post-mortems SRE

echo "[INFO] Démarrage de l'application Post-Mortems SRE..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 n'est pas installé. Veuillez installer Python 3.8+."
    exit 1
fi

# Vérifier pip
if ! command -v pip3 &> /dev/null; then
    echo "[ERROR] pip3 n'est pas installé. Veuillez installer pip."
    exit 1
fi

# Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo "[INFO] Création de l'environnement virtuel..."
    python3 -m venv venv
fi

echo "[INFO] Activation de l'environnement virtuel..."
# Activer l'environnement virtuel pour Git Bash
source venv/Scripts/activate

echo "[INFO] Installation des dépendances..."
pip install -r requirements.txt

# Créer les répertoires nécessaires
mkdir -p data/postmortems
mkdir -p templates

echo "[INFO] Démarrage de l'application Flask..."
echo ""
echo "[SUCCESS] Application Post-Mortems SRE démarrée !"
echo ""
echo "[INFO] URLs d'accès :"
echo "   - Interface principale: http://localhost:5000"
echo "   - API des post-mortems: http://localhost:5000/api/postmortems"
echo ""
echo "[INFO] Fonctionnalités :"
echo "   - Visualisation des post-mortems avec format structuré"
echo "   - Création de nouveaux post-mortems"
echo "   - Interface responsive et professionnelle"
echo "   - API REST pour l'intégration"
echo ""
echo "[INFO] Pour arrêter l'application, appuyez sur Ctrl+C"

# Démarrer l'application
python app.py
