#!/bin/bash

# Script de démarrage de l'application Flask pour les post-mortems
# Interface web pour la gestion et visualisation des post-mortems SRE
# Version adaptée pour Windows (Git Bash)

set -e

echo "[INFO] Démarrage de l'application Post-Mortems SRE..."

# Vérifier Python
if ! command -v python &> /dev/null; then
    echo "[ERROR] Python n'est pas installé"
    exit 1
fi

# Vérifier pip
if ! command -v pip &> /dev/null; then
    echo "[ERROR] pip n'est pas installé"
    exit 1
fi

# Installer les dépendances si nécessaire
if [ ! -d "venv" ]; then
    echo "[INFO] Création de l'environnement virtuel..."
    python -m venv venv
fi

echo "[INFO] Activation de l'environnement virtuel..."
# Sur Windows, utiliser le script d'activation Windows
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "[ERROR] Impossible de trouver le script d'activation"
    exit 1
fi

echo "[INFO] Installation des dépendances..."
pip install -r requirements.txt

# Créer les répertoires nécessaires
mkdir -p data/postmortems
mkdir -p templates

echo "[INFO] Démarrage de l'application Flask..."
echo ""
echo "Application Post-Mortems SRE demarree !"
echo ""
echo "URLs d'acces :"
echo "   - Interface principale: http://localhost:5000"
echo "   - API des post-mortems: http://localhost:5000/api/postmortems"
echo ""
echo "Fonctionnalites :"
echo "   - Visualisation des post-mortems avec format structure"
echo "   - Creation de nouveaux post-mortems"
echo "   - Interface responsive et professionnelle"
echo "   - API REST pour l'integration"
echo ""
echo "Pour arreter l'application, appuyez sur Ctrl+C"

# Démarrer l'application
python app.py
