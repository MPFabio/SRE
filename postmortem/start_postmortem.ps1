# Script de démarrage de l'application Flask pour les post-mortems
# Interface web pour la gestion et visualisation des post-mortems SRE

Write-Host "[INFO] Démarrage de l'application Post-Mortems SRE..." -ForegroundColor Green

# Vérifier Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python n'est pas installé" -ForegroundColor Red
    exit 1
}

# Vérifier pip
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] pip n'est pas installé" -ForegroundColor Red
    exit 1
}

# Installer les dépendances si nécessaire
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Création de l'environnement virtuel..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "[INFO] Activation de l'environnement virtuel..." -ForegroundColor Yellow

# Activer l'environnement virtuel (Windows)
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "[ERROR] Impossible d'activer l'environnement virtuel" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Installation des dépendances..." -ForegroundColor Yellow
pip install -r requirements.txt

# Créer les répertoires nécessaires
if (-not (Test-Path "data\postmortems")) {
    New-Item -ItemType Directory -Path "data\postmortems" -Force
}
if (-not (Test-Path "templates")) {
    New-Item -ItemType Directory -Path "templates" -Force
}

Write-Host "[INFO] Démarrage de l'application Flask..." -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Application Post-Mortems SRE démarrée !" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 URLs d'accès :" -ForegroundColor White
Write-Host "   - Interface principale: http://localhost:5000" -ForegroundColor White
Write-Host "   - API des post-mortems: http://localhost:5000/api/postmortems" -ForegroundColor White
Write-Host ""
Write-Host "📚 Fonctionnalités :" -ForegroundColor White
Write-Host "   - Visualisation des post-mortems avec format structuré" -ForegroundColor White
Write-Host "   - Création de nouveaux post-mortems" -ForegroundColor White
Write-Host "   - Interface responsive et professionnelle" -ForegroundColor White
Write-Host "   - API REST pour l'intégration" -ForegroundColor White
Write-Host ""
Write-Host "Pour arreter l'application, appuyez sur Ctrl+C" -ForegroundColor Yellow

# Démarrer l'application
python app.py
