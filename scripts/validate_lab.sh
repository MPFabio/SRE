#!/bin/bash

# Script de validation du lab SRE
# Vérifie que tous les composants sont opérationnels

set -e

echo "[INFO] Validation du lab SRE..."

# Vérifier que kubectl est configuré
if ! kubectl cluster-info &> /dev/null; then
    echo "[ERROR] kubectl n'est pas configuré ou le cluster n'est pas accessible"
    exit 1
fi

echo "[SUCCESS] Cluster Kubernetes accessible"

# Attendre que tous les pods soient prêts
echo "[INFO] Attente que tous les pods soient prêts..."
kubectl wait --for=condition=Ready pods --all --timeout=300s

# Vérifier le statut des pods
echo "[INFO] Statut des pods :"
kubectl get pods

# Vérifier les services
echo ""
echo "🌐 Services disponibles :"
kubectl get services

# Tester l'URL Shortener
echo ""
echo "[INFO] Test de l'URL Shortener..."
if curl -s http://localhost:30000/health > /dev/null; then
    echo "[SUCCESS] URL Shortener accessible sur http://localhost:30000"
else
    echo "[WARN] URL Shortener non accessible (peut être en cours de démarrage)"
fi

# Tester les métriques
echo ""
echo "[INFO] Test des métriques..."
if curl -s http://localhost:30000/metrics > /dev/null; then
    echo "[SUCCESS] Métriques disponibles sur http://localhost:30000/metrics"
else
    echo "[WARN] Métriques non accessibles"
fi

echo ""
# Tester Splunk (Docker Compose)
echo ""
echo "[INFO] Test de Splunk..."
if curl -s http://localhost:8000 > /dev/null; then
    echo "[SUCCESS] Splunk accessible sur http://localhost:8000"
else
    echo "[WARN] Splunk non accessible (vérifiez docker-compose up -d)"
fi

# Tester OpenTelemetry Collector (Docker Compose)
echo ""
echo "[INFO] Test de l'OpenTelemetry Collector..."
if curl -s http://localhost:8889/metrics > /dev/null; then
    echo "[SUCCESS] OpenTelemetry Collector accessible sur http://localhost:8889/metrics"
else
    echo "[WARN] OpenTelemetry Collector non accessible"
fi

# Tester Post-Mortems (Kubernetes)
echo ""
echo "[INFO] Test de l'interface Post-Mortems..."
if curl -s http://localhost:30001 > /dev/null; then
    echo "[SUCCESS] Interface Post-Mortems accessible sur http://localhost:30001"
else
    echo "[WARN] Interface Post-Mortems non accessible"
fi

echo ""
echo "[INFO] URLs d'accès :"
echo "   - URL Shortener: http://localhost:30000"
echo "   - Métriques: http://localhost:30000/metrics"
echo "   - Health Check: http://localhost:30000/health"
echo "   - Splunk: http://localhost:8000 (admin/admin123)"
echo "   - OpenTelemetry: http://localhost:8889/metrics"
echo "   - Post-Mortems: http://localhost:30001"

echo ""
echo "[SUCCESS] Validation terminée ! Le lab SRE est prêt à être utilisé."
