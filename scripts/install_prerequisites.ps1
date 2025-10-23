# Script d'installation des prérequis pour le Lab SRE
# Exécuter en tant qu'administrateur

Write-Host "===============================================" -ForegroundColor Green
Write-Host "  Installation des prérequis pour le Lab SRE" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# Vérifier si le script est exécuté en tant qu'administrateur
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "[ERREUR] Ce script doit être exécuté en tant qu'administrateur" -ForegroundColor Red
    Write-Host "Clic droit sur PowerShell -> 'Exécuter en tant qu'administrateur'" -ForegroundColor Yellow
    exit 1
}

# Fonction pour vérifier si une commande existe
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# 1. Vérifier/Installer Chocolatey
Write-Host "`n[1/6] Verification de Chocolatey..." -ForegroundColor Blue
if (-not (Test-Command choco)) {
    Write-Host "Installation de Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
} else {
    Write-Host "[OK] Chocolatey deja installe" -ForegroundColor Green
}

# 2. Vérifier/Installer Docker Desktop
Write-Host "`n[2/6] Verification de Docker Desktop..." -ForegroundColor Blue
if (-not (Test-Command docker)) {
    Write-Host "Installation de Docker Desktop..." -ForegroundColor Yellow
    choco install docker-desktop -y
    Write-Host "[ATTENTION] Docker Desktop installe. Veuillez le demarrer manuellement." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Docker deja installe" -ForegroundColor Green
}

# 3. Vérifier/Installer KinD
Write-Host "`n[3/6] Verification de KinD..." -ForegroundColor Blue
if (-not (Test-Command kind)) {
    Write-Host "Installation de KinD..." -ForegroundColor Yellow
    choco install kind -y
} else {
    Write-Host "[OK] KinD deja installe" -ForegroundColor Green
}

# 4. Vérifier/Installer kubectl
Write-Host "`n[4/6] Verification de kubectl..." -ForegroundColor Blue
if (-not (Test-Command kubectl)) {
    Write-Host "Installation de kubectl..." -ForegroundColor Yellow
    choco install kubernetes-cli -y
} else {
    Write-Host "[OK] kubectl deja installe" -ForegroundColor Green
}

# 5. Vérifier/Installer Python
Write-Host "`n[5/6] Verification de Python..." -ForegroundColor Blue
if (-not (Test-Command python)) {
    Write-Host "Installation de Python..." -ForegroundColor Yellow
    choco install python -y
} else {
    Write-Host "[OK] Python deja installe" -ForegroundColor Green
}

# 6. Vérifier/Installer Git
Write-Host "`n[6/6] Verification de Git..." -ForegroundColor Blue
if (-not (Test-Command git)) {
    Write-Host "Installation de Git..." -ForegroundColor Yellow
    choco install git -y
} else {
    Write-Host "[OK] Git deja installe" -ForegroundColor Green
}

# 7. Installation des dépendances Python
Write-Host "`n[7/7] Installation des dependances Python..." -ForegroundColor Blue
$requirements = @"
requests>=2.28.0
numpy>=1.21.0
prometheus-client>=0.14.0
schedule>=1.2.0
"@

$requirements | Out-File -FilePath "requirements.txt" -Encoding UTF8
pip install -r requirements.txt

# 8. Vérification finale
Write-Host "`n[VERIFICATION] Verification finale..." -ForegroundColor Blue

$tools = @(
    @{Name="Docker"; Command="docker --version"},
    @{Name="Docker Compose"; Command="docker-compose --version"},
    @{Name="KinD"; Command="kind --version"},
    @{Name="kubectl"; Command="kubectl version --client"},
    @{Name="Python"; Command="python --version"},
    @{Name="Git"; Command="git --version"}
)

foreach ($tool in $tools) {
    try {
        $version = Invoke-Expression $tool.Command 2>$null
        Write-Host "[OK] $($tool.Name): $version" -ForegroundColor Green
    } catch {
        Write-Host "[ERREUR] $($tool.Name): Non trouve" -ForegroundColor Red
    }
}

Write-Host "`n===============================================" -ForegroundColor Green
Write-Host "  Installation terminee avec succes !" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host "`nProchaines etapes :" -ForegroundColor Yellow
Write-Host "1. Redemarrez votre terminal" -ForegroundColor White
Write-Host "2. Demarrer Docker Desktop" -ForegroundColor White
Write-Host "3. Executer : ./start_lab.sh" -ForegroundColor White
Write-Host "`n[INFO] Si Docker Desktop ne demarre pas, redemarrez votre ordinateur" -ForegroundColor Cyan
