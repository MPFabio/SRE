#!/bin/bash

# Script de test pour Codespace
# Teste tous les services sans interface graphique

set -e

echo "[INFO] Test du lab SRE dans Codespace..."

# Fonction de test avec retry
test_endpoint() {
    local url=$1
    local description=$2
    local max_attempts=5
    local attempt=1
    
    echo "🧪 Test de $description..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s --connect-timeout 5 "$url" > /dev/null 2>&1; then
            echo "✅ $description - OK"
            return 0
        else
            echo "⏳ $description - Tentative $attempt/$max_attempts..."
            sleep 5
            ((attempt++))
        fi
    done
    
    echo "❌ $description - ÉCHEC après $max_attempts tentatives"
    return 1
}

# Test des services Kubernetes
echo "🔍 Test des services Kubernetes..."
kubectl get pods
kubectl get services

# Test du service URL Shortener
echo ""
echo "🌐 Test du service URL Shortener..."

# Test de santé
test_endpoint "http://localhost:30000/health" "Health Check"

# Test de création d'URL
echo "🧪 Test de création d'URL..."
SHORT_RESPONSE=$(curl -s -X POST "http://localhost:30000/shorten?url=https://www.google.com")
echo "Réponse: $SHORT_RESPONSE"

# Extraction du code court
SHORT_CODE=$(echo "$SHORT_RESPONSE" | grep -o '"short_code":"[^"]*"' | cut -d'"' -f4)
if [ -n "$SHORT_CODE" ]; then
    echo "✅ URL créée avec succès: $SHORT_CODE"
    
    # Test de redirection
    echo "🧪 Test de redirection..."
    REDIRECT_RESPONSE=$(curl -s -I "http://localhost:30000/$SHORT_CODE")
    if echo "$REDIRECT_RESPONSE" | grep -q "Location:"; then
        echo "✅ Redirection fonctionne"
    else
        echo "❌ Redirection échouée"
    fi
else
    echo "❌ Impossible de créer une URL"
fi

# Test des métriques
echo ""
echo "📊 Test des métriques..."
test_endpoint "http://localhost:30000/metrics" "Métriques Prometheus"

# Test de Splunk (si accessible)
echo ""
echo "🔍 Test de Splunk..."
if docker ps | grep -q "splunk-sre-lab"; then
    echo "✅ Splunk container en cours d'exécution"
    
    # Test de connexion à Splunk
    if curl -s --connect-timeout 10 "http://localhost:8000" > /dev/null 2>&1; then
        echo "✅ Splunk accessible sur le port 8000"
    else
        echo "⚠️ Splunk non accessible sur le port 8000 (normal si pas de port forwarding)"
    fi
else
    echo "❌ Splunk container non trouvé"
fi

# Test des logs
echo ""
echo "📝 Test des logs..."
echo "Logs du service URL Shortener:"
kubectl logs -l app=url-shortener --tail=5

# Test de génération de trafic
echo ""
echo "🚀 Test de génération de trafic..."
if [ -f "simulator/traffic_generator.py" ]; then
    echo "🧪 Lancement du générateur de trafic..."
    cd simulator
    python3 traffic_generator.py --duration 10 --rpm 5 &
    TRAFFIC_PID=$!
    sleep 15
    kill $TRAFFIC_PID 2>/dev/null || true
    cd ..
    echo "✅ Génération de trafic testée"
else
    echo "⚠️ Générateur de trafic non trouvé"
fi

echo ""
echo "🎉 Tests terminés !"
echo ""
echo "📋 Résumé des services :"
echo "   - URL Shortener: http://localhost:30000"
echo "   - Health Check: http://localhost:30000/health"
echo "   - Métriques: http://localhost:30000/metrics"
echo "   - Splunk: http://localhost:8000 (si port forwarding configuré)"
echo ""
echo "💡 Pour accéder aux services dans Codespace :"
echo "   1. Ouvrez l'onglet 'Ports' dans VS Code"
echo "   2. Les ports 30000 et 8000 devraient apparaître automatiquement"
echo "   3. Cliquez sur 'Open in Browser' pour accéder aux services"
