#!/bin/bash

# Script universel pour démarrer l'application Post-Mortems
# Détecte automatiquement l'environnement (Git Bash, WSL, Linux, macOS)

echo "[INFO] Démarrage de l'application Post-Mortems SRE..."

# Détecter l'environnement
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Git Bash sur Windows
    PYTHON_CMD="python"
    PIP_CMD="pip"
    VENV_ACTIVATE="venv/Scripts/activate"
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
    # Linux ou macOS
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
    VENV_ACTIVATE="venv/bin/activate"
else
    # Fallback
    PYTHON_CMD="python"
    PIP_CMD="pip"
    VENV_ACTIVATE="venv/Scripts/activate"
fi

# Vérifier Python
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "[ERROR] Python n'est pas installé. Veuillez installer Python 3.8+."
    exit 1
fi

# Vérifier pip
if ! command -v $PIP_CMD &> /dev/null; then
    echo "[ERROR] pip n'est pas installé. Veuillez installer pip."
    exit 1
fi

# Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo "[INFO] Création de l'environnement virtuel..."
    $PYTHON_CMD -m venv venv
fi

echo "[INFO] Activation de l'environnement virtuel..."
# Activer l'environnement virtuel
source $VENV_ACTIVATE

echo "[INFO] Installation des dépendances..."
$PIP_CMD install -r requirements.txt

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
$PYTHON_CMD app.py