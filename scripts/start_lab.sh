#!/bin/bash

# Script de démarrage complet du lab SRE
# Démarre tous les composants et valide le déploiement

set -e

echo "[INFO] Démarrage du lab SRE..."

# Vérifier les prérequis
echo "🔍 Vérification des prérequis..."

if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker n'est pas installé"
    exit 1
fi

if ! command -v kind &> /dev/null; then
    echo "[ERROR] KinD n'est pas installé"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "[ERROR] kubectl n'est pas installé"
    exit 1
fi

echo "[SUCCESS] Prérequis vérifiés"

# Démarrer Splunk
echo "[INFO] Démarrage de Splunk..."
if ! docker-compose ps | grep -q "Up"; then
    docker-compose up -d
    echo "[INFO] Attente que Splunk soit prêt..."
    sleep 30
else
    echo "[SUCCESS] Splunk déjà démarré"
fi

# Démarrer le cluster KinD
echo "[INFO] Démarrage du cluster KinD..."
if ! kind get clusters | grep -q "sre-lab"; then
    cd ../kind
    chmod +x setup.sh
    ./setup.sh
    cd ..
else
    echo "[SUCCESS] Cluster KinD déjà créé"
fi

# Validation
echo "🔍 Validation du déploiement..."
if [ -f "scripts/validate_lab.sh" ]; then
    chmod +x scripts/validate_lab.sh
    ./scripts/validate_lab.sh
else
    echo "[WARN] Script de validation non trouvé, validation manuelle..."
    kubectl get pods
    kubectl get services
fi

echo ""
echo "[SUCCESS] Lab SRE démarré avec succès !"
echo ""
echo "🌐 URLs d'accès :"
echo "   - URL Shortener: http://localhost:30000"
echo "   - Splunk: http://localhost:8000 (admin/admin123)"
echo "   - Métriques: http://localhost:30000/metrics"
echo ""
echo "📚 Pour commencer les exercices, consultez le README.md"