#!/bin/bash

# Script d'installation des prérequis pour le Lab SRE
# Compatible macOS et Linux

set -e

echo "==============================================="
echo "  Installation des prérequis pour le Lab SRE"
echo "==============================================="

# Détecter l'OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "[ERREUR] OS non supporte: $OSTYPE"
    exit 1
fi

echo "[INFO] OS detecte: $OS"

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Fonction pour installer sur macOS
install_macos() {
    echo "[1/6] Installation pour macOS"
    
    # Vérifier Homebrew
    if ! command_exists brew; then
        echo "Installation de Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "[OK] Homebrew deja installe"
    fi
    
    # Docker Desktop
    if ! command_exists docker; then
        echo "Installation de Docker Desktop..."
        brew install --cask docker
        echo "[ATTENTION] Docker Desktop installe. Veuillez le demarrer manuellement."
    else
        echo "[OK] Docker deja installe"
    fi
    
    # KinD
    if ! command_exists kind; then
        echo "Installation de KinD..."
        brew install kind
    else
        echo "[OK] KinD deja installe"
    fi
    
    # kubectl
    if ! command_exists kubectl; then
        echo "Installation de kubectl..."
        brew install kubectl
    else
        echo "[OK] kubectl deja installe"
    fi
    
    # Python
    if ! command_exists python3; then
        echo "Installation de Python..."
        brew install python@3.11
    else
        echo "[OK] Python deja installe"
    fi
    
    # Git
    if ! command_exists git; then
        echo "Installation de Git..."
        brew install git
    else
        echo "[OK] Git deja installe"
    fi
}

# Fonction pour installer sur Linux
install_linux() {
    echo "[1/6] Installation pour Linux"
    
    # Docker
    if ! command_exists docker; then
        echo "Installation de Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        
        # Docker Compose
        echo "Installation de Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    else
        echo "[OK] Docker deja installe"
    fi
    
    # KinD
    if ! command_exists kind; then
        echo "Installation de KinD..."
        curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
    else
        echo "[OK] KinD deja installe"
    fi
    
    # kubectl
    if ! command_exists kubectl; then
        echo "Installation de kubectl..."
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
    else
        echo "[OK] kubectl deja installe"
    fi
    
    # Python
    if ! command_exists python3; then
        echo "Installation de Python..."
        sudo apt update
        sudo apt install -y python3 python3-pip
    else
        echo "[OK] Python deja installe"
    fi
    
    # Git
    if ! command_exists git; then
        echo "Installation de Git..."
        sudo apt install -y git
    else
        echo "[OK] Git deja installe"
    fi
}

# Installation selon l'OS
case $OS in
    "macos")
        install_macos
        ;;
    "linux")
        install_linux
        ;;
    *)
        echo "[ERREUR] OS non supporté"
        exit 1
        ;;
esac

# Installation des dépendances Python
echo "[7/7] Installation des dépendances Python..."
cat > requirements.txt << EOF
requests>=2.28.0
numpy>=1.21.0
prometheus-client>=0.14.0
schedule>=1.2.0
EOF

if command_exists pip3; then
    pip3 install -r requirements.txt
elif command_exists pip; then
    pip install -r requirements.txt
else
    echo "[ATTENTION] pip non trouve, installation manuelle necessaire"
fi

# Vérification finale
echo "[VERIFICATION] Verification finale..."

tools=(
    "docker:Docker"
    "docker-compose:Docker Compose"
    "kind:KinD"
    "kubectl:kubectl"
    "python3:Python"
    "git:Git"
)

for tool_info in "${tools[@]}"; do
    IFS=':' read -r cmd name <<< "$tool_info"
    if command_exists "$cmd"; then
        version=$($cmd --version 2>/dev/null | head -n1)
        echo "[OK] $name: $version"
    else
        echo "[ERREUR] $name: Non trouve"
    fi
done

echo ""
echo "==============================================="
echo "  Installation terminee avec succes !"
echo "==============================================="
echo ""
echo "Prochaines etapes :"
echo "1. Redemarrez votre terminal"
echo "2. Demarrer Docker Desktop (si necessaire)"
echo "3. Executer : ./start_lab.sh"
echo ""
echo "[INFO] Si Docker ne fonctionne pas, redemarrez votre ordinateur"
