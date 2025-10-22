#!/bin/bash

# Script de démarrage du lab SRE pour Codespace
# Configure automatiquement le port forwarding

set -e

echo "[INFO] Démarrage du lab SRE pour Codespace..."

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
    cd kind
    chmod +x setup.sh
    ./setup.sh
    cd ..
else
    echo "[SUCCESS] Cluster KinD déjà créé"
fi

# Configuration du port forwarding pour Codespace
echo "[INFO] Configuration du port forwarding pour Codespace..."

# Port forwarding pour le service URL Shortener
echo "[INFO] Configuration du port forwarding pour URL Shortener (port 30000)..."
kubectl port-forward --address 0.0.0.0 service/url-shortener-service 30000:80 &
URL_SHORTENER_PID=$!

# Port forwarding pour Splunk
echo "[INFO] Configuration du port forwarding pour Splunk (port 8000)..."
docker port splunk-sre-lab 8000 | xargs -I {} kubectl port-forward --address 0.0.0.0 service/url-shortener-service 8000:8000 &
SPLUNK_PID=$!

# Attendre que les services soient prêts
echo "[INFO] Attente que les services soient prêts..."
sleep 10

# Validation
echo "🔍 Validation du déploiement..."
if [ -f "validate_lab.sh" ]; then
    chmod +x validate_lab.sh
    ./validate_lab.sh
else
    echo "[WARN] Script de validation non trouvé, validation manuelle..."
    kubectl get pods
    kubectl get services
fi

echo ""
echo "[SUCCESS] Lab SRE démarré avec succès dans Codespace !"
echo ""
echo "🌐 URLs d'accès (Port Forwarding configuré) :"
echo "   - URL Shortener: http://localhost:30000"
echo "   - Splunk: http://localhost:8000 (admin/admin123)"
echo "   - Métriques: http://localhost:30000/metrics"
echo ""
echo "📝 Pour Codespace :"
echo "   - Les ports sont automatiquement exposés"
echo "   - Utilisez les URLs ci-dessus dans l'onglet 'Ports' de VS Code"
echo "   - Ou testez avec curl dans le terminal"
echo ""
echo "🧪 Test rapide :"
echo "   curl http://localhost:30000/health"
echo "   curl http://localhost:30000/metrics"
echo ""
echo "📚 Pour commencer les exercices, consultez le README.md"

# Garder le script en vie pour maintenir le port forwarding
echo "[INFO] Port forwarding actif. Appuyez sur Ctrl+C pour arrêter."
wait
