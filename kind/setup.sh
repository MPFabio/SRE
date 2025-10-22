#!/bin/bash

# Script de déploiement du lab SRE
# Crée le cluster KinD et déploie les composants

set -e

echo "[INFO] Démarrage du lab SRE..."

# Vérifier que KinD est installé
if ! command -v kind &> /dev/null; then
    echo "[ERROR] KinD n'est pas installé. Veuillez l'installer d'abord."
    echo "   Instructions: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
    exit 1
fi

# Vérifier que kubectl est installé
if ! command -v kubectl &> /dev/null; then
    echo "[ERROR] kubectl n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Créer le cluster KinD
echo "[INFO] Création du cluster KinD..."
if kind get clusters | grep -q "sre-lab"; then
    echo "[WARN] Cluster sre-lab existe déjà, suppression..."
    kind delete cluster --name sre-lab
fi

kind create cluster --config=kind-config.yaml

# Attendre que le cluster soit prêt
echo "[INFO] Attente que le cluster soit prêt..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Appliquer les manifests
echo "[INFO] Déploiement des composants..."
kubectl apply -f manifests/postgres-pv.yaml
kubectl apply -f manifests/postgres-deployment.yaml
kubectl apply -f manifests/otel-collector-config.yaml
kubectl apply -f manifests/otel-collector-deployment.yaml
kubectl apply -f manifests/url-shortener-with-db.yaml

# Attendre que les pods soient prêts (avec délai plus long pour l'installation des dépendances)
echo "[INFO] Attente que les pods soient prêts..."
kubectl wait --for=condition=Ready pods --all --timeout=600s

# Afficher le statut
echo "[SUCCESS] Déploiement terminé !"
echo ""
echo "[INFO] Statut des pods :"
kubectl get pods

echo ""
echo "🌐 Services disponibles :"
kubectl get services

echo ""
echo "🔗 URLs d'accès :"
echo "   - URL Shortener: http://localhost:30000"
echo "   - Splunk: http://localhost:8000 (admin/admin123)"
echo "   - OpenTelemetry Collector: http://localhost:8889/metrics"

echo ""
echo "🎯 Pour commencer les exercices, consultez le README.md"
