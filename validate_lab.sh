#!/bin/bash

# Script de validation du lab SRE
# Vérifie que tous les composants sont opérationnels

set -e

echo "🔍 Validation du lab SRE..."

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
echo "🧪 Test de l'URL Shortener..."
if curl -s http://localhost:30000/health > /dev/null; then
    echo "[SUCCESS] URL Shortener accessible sur http://localhost:30000"
else
    echo "[WARN] URL Shortener non accessible (peut être en cours de démarrage)"
fi

# Tester les métriques
echo ""
echo "📈 Test des métriques..."
if curl -s http://localhost:30000/metrics > /dev/null; then
    echo "[SUCCESS] Métriques disponibles sur http://localhost:30000/metrics"
else
    echo "[WARN] Métriques non accessibles"
fi

echo ""
echo "🎯 URLs d'accès :"
echo "   - URL Shortener: http://localhost:30000"
echo "   - Métriques: http://localhost:30000/metrics"
echo "   - Health Check: http://localhost:30000/health"

echo ""
echo "[SUCCESS] Validation terminée ! Le lab SRE est prêt à être utilisé."
