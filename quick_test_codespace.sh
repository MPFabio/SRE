#!/bin/bash

# Test rapide pour Codespace
# Vérifie que les services fonctionnent sans interface graphique

echo "🧪 Test rapide du lab SRE dans Codespace..."

# Test 1: Vérifier que les pods sont en cours d'exécution
echo "1️⃣ Vérification des pods..."
if kubectl get pods | grep -q "Running"; then
    echo "✅ Pods en cours d'exécution"
else
    echo "❌ Aucun pod en cours d'exécution"
    kubectl get pods
    exit 1
fi

# Test 2: Vérifier les services
echo "2️⃣ Vérification des services..."
if kubectl get services | grep -q "url-shortener-service"; then
    echo "✅ Service URL Shortener disponible"
else
    echo "❌ Service URL Shortener non trouvé"
    kubectl get services
    exit 1
fi

# Test 3: Test de santé du service
echo "3️⃣ Test de santé du service..."
if curl -s --connect-timeout 10 "http://localhost:30000/health" | grep -q "healthy"; then
    echo "✅ Service en bonne santé"
else
    echo "❌ Service non accessible ou en mauvaise santé"
    echo "Tentative de diagnostic..."
    kubectl logs -l app=url-shortener --tail=10
    exit 1
fi

# Test 4: Test de création d'URL
echo "4️⃣ Test de création d'URL..."
RESPONSE=$(curl -s -X POST "http://localhost:30000/shorten?url=https://www.example.com")
if echo "$RESPONSE" | grep -q "short_code"; then
    echo "✅ Création d'URL fonctionne"
    SHORT_CODE=$(echo "$RESPONSE" | grep -o '"short_code":"[^"]*"' | cut -d'"' -f4)
    echo "   Code créé: $SHORT_CODE"
else
    echo "❌ Création d'URL échouée"
    echo "Réponse: $RESPONSE"
    exit 1
fi

# Test 5: Test des métriques
echo "5️⃣ Test des métriques..."
if curl -s --connect-timeout 10 "http://localhost:30000/metrics" | grep -q "http_requests_total"; then
    echo "✅ Métriques disponibles"
else
    echo "❌ Métriques non accessibles"
    exit 1
fi

# Test 6: Test de Splunk (si disponible)
echo "6️⃣ Test de Splunk..."
if docker ps | grep -q "splunk-sre-lab"; then
    echo "✅ Splunk container en cours d'exécution"
    if curl -s --connect-timeout 5 "http://localhost:8000" > /dev/null 2>&1; then
        echo "✅ Splunk accessible"
    else
        echo "⚠️ Splunk non accessible (port forwarding nécessaire)"
    fi
else
    echo "⚠️ Splunk non démarré"
fi

echo ""
echo "🎉 Tests terminés avec succès !"
echo ""
echo "📋 Services disponibles :"
echo "   - URL Shortener: http://localhost:30000"
echo "   - Health Check: http://localhost:30000/health"
echo "   - Métriques: http://localhost:30000/metrics"
echo "   - Splunk: http://localhost:8000 (si port forwarding configuré)"
echo ""
echo "💡 Pour accéder aux services :"
echo "   1. Ouvrez l'onglet 'Ports' dans VS Code"
echo "   2. Cliquez sur 'Open in Browser' pour les ports 30000 et 8000"
echo "   3. Ou utilisez curl dans le terminal"
echo ""
echo "🧪 Test manuel :"
echo "   curl http://localhost:30000/health"
echo "   curl http://localhost:30000/metrics"
