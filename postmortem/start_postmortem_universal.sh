#!/bin/bash

# Script de démarrage universel pour l'application Flask des post-mortems
# Détecte automatiquement l'OS et utilise la bonne méthode d'activation

set -e

echo "[INFO] Démarrage de l'application Post-Mortems SRE..."

# Détecter l'OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "[INFO] Détection: Windows"
    PYTHON_CMD="python"
    PIP_CMD="pip"
    ACTIVATE_SCRIPT="venv/Scripts/activate"
else
    echo "[INFO] Détection: Unix/Linux/macOS"
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
    ACTIVATE_SCRIPT="venv/bin/activate"
fi

# Vérifier Python
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "[ERROR] $PYTHON_CMD n'est pas installé"
    exit 1
fi

# Vérifier pip
if ! command -v $PIP_CMD &> /dev/null; then
    echo "[ERROR] $PIP_CMD n'est pas installé"
    exit 1
fi

# Installer les dépendances si nécessaire
if [ ! -d "venv" ]; then
    echo "[INFO] Création de l'environnement virtuel..."
    $PYTHON_CMD -m venv venv
fi

echo "[INFO] Activation de l'environnement virtuel..."
if [ -f "$ACTIVATE_SCRIPT" ]; then
    source $ACTIVATE_SCRIPT
else
    echo "[ERROR] Impossible de trouver le script d'activation: $ACTIVATE_SCRIPT"
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
