# Script de démarrage complet du lab SRE (PowerShell)
# Démarre tous les composants et valide le déploiement

Write-Host "🚀 Démarrage du lab SRE..." -ForegroundColor Green

# Vérifier les prérequis
Write-Host "🔍 Vérification des prérequis..." -ForegroundColor Yellow

try {
    docker --version | Out-Null
    Write-Host "✅ Docker installé" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker n'est pas installé" -ForegroundColor Red
    exit 1
}

try {
    kind version | Out-Null
    Write-Host "✅ KinD installé" -ForegroundColor Green
} catch {
    Write-Host "❌ KinD n'est pas installé" -ForegroundColor Red
    exit 1
}

try {
    kubectl version --client | Out-Null
    Write-Host "✅ kubectl installé" -ForegroundColor Green
} catch {
    Write-Host "❌ kubectl n'est pas installé" -ForegroundColor Red
    exit 1
}

# Démarrer Splunk
Write-Host "📦 Démarrage de Splunk..." -ForegroundColor Yellow
$splunkStatus = docker-compose ps
if ($splunkStatus -notmatch "Up") {
    docker-compose up -d
    Write-Host "⏳ Attente que Splunk soit prêt..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
} else {
    Write-Host "✅ Splunk déjà démarré" -ForegroundColor Green
}

# Démarrer le cluster KinD
Write-Host "📦 Démarrage du cluster KinD..." -ForegroundColor Yellow
$kindClusters = kind get clusters
if ($kindClusters -notmatch "sre-lab") {
    Set-Location kind
    .\setup.sh
    Set-Location ..
} else {
    Write-Host "✅ Cluster KinD déjà créé" -ForegroundColor Green
}

# Validation
Write-Host "🔍 Validation du déploiement..." -ForegroundColor Yellow
if (Test-Path "validate_lab.ps1") {
    .\validate_lab.ps1
} else {
    Write-Host "⚠️  Script de validation non trouvé, validation manuelle..." -ForegroundColor Yellow
    kubectl get pods
    kubectl get services
}

Write-Host ""
Write-Host "🎉 Lab SRE démarré avec succès !" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 URLs d'accès :" -ForegroundColor Cyan
Write-Host "   - URL Shortener: http://localhost:30000" -ForegroundColor White
Write-Host "   - Splunk: http://localhost:8000 (admin/admin123)" -ForegroundColor White
Write-Host "   - Métriques: http://localhost:30000/metrics" -ForegroundColor White
Write-Host ""
Write-Host "📚 Pour commencer les exercices, consultez le README.md" -ForegroundColor Cyan
