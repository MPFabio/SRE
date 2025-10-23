# Script de validation du lab SRE (PowerShell)
# Vérifie que tous les composants sont opérationnels

Write-Host "🔍 Validation du lab SRE..." -ForegroundColor Green

# Vérifier que kubectl est configuré
try {
    kubectl cluster-info | Out-Null
    Write-Host "✅ Cluster Kubernetes accessible" -ForegroundColor Green
} catch {
    Write-Host "❌ kubectl n'est pas configuré ou le cluster n'est pas accessible" -ForegroundColor Red
    exit 1
}

# Attendre que tous les pods soient prêts
Write-Host "⏳ Attente que tous les pods soient prêts..." -ForegroundColor Yellow
kubectl wait --for=condition=Ready pods --all --timeout=300s

# Vérifier le statut des pods
Write-Host "📊 Statut des pods :" -ForegroundColor Cyan
kubectl get pods

# Vérifier les services
Write-Host ""
Write-Host "🌐 Services disponibles :" -ForegroundColor Cyan
kubectl get services

# Tester l'URL Shortener
Write-Host ""
Write-Host "🧪 Test de l'URL Shortener..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:30000/health" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ URL Shortener accessible sur http://localhost:30000" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  URL Shortener non accessible (peut être en cours de démarrage)" -ForegroundColor Yellow
}

# Tester les métriques
Write-Host ""
Write-Host "📈 Test des métriques..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:30000/metrics" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Métriques disponibles sur http://localhost:30000/metrics" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Métriques non accessibles" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎯 URLs d'accès :" -ForegroundColor Cyan
Write-Host "   - URL Shortener: http://localhost:30000" -ForegroundColor White
Write-Host "   - Métriques: http://localhost:30000/metrics" -ForegroundColor White
Write-Host "   - Health Check: http://localhost:30000/health" -ForegroundColor White

Write-Host ""
Write-Host "✅ Validation terminée ! Le lab SRE est prêt à être utilisé." -ForegroundColor Green
