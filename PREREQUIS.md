# Installation des Prérequis - Lab SRE

Ce guide détaille l'installation de tous les prérequis nécessaires pour le Lab SRE sur différents systèmes d'exploitation.

## Prérequis Généraux

- Docker et Docker Compose
- KinD (Kubernetes in Docker)
- kubectl
- Python 3.8+
- Git

## Windows

### Installation Automatique (Recommandée)
```powershell
# Exécuter en tant qu'administrateur
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install_prerequisites.ps1
```

### Installation Manuelle

#### 1. Docker Desktop
```bash
# Télécharger et installer Docker Desktop pour Windows
# https://www.docker.com/products/docker-desktop/
```

#### 2. KinD (Kubernetes in Docker)
```bash
# Option 1: Via Chocolatey
choco install kind

# Option 2: Via Scoop
scoop install kind

# Option 3: Téléchargement direct
# Télécharger depuis: https://github.com/kubernetes-sigs/kind/releases
# Ajouter au PATH
```

#### 3. kubectl
```bash
# Via Chocolatey
choco install kubernetes-cli

# Via Scoop
scoop install kubectl

# Ou télécharger depuis: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
```

#### 4. Python 3.8+
```bash
# Via Microsoft Store ou python.org
# Vérifier l'installation
python --version
pip --version
```

## macOS

### Installation Automatique (Recommandée)
```bash
# Rendre le script exécutable
chmod +x install_prerequisites.sh
# Exécuter le script d'installation
./install_prerequisites.sh
```

### Installation Manuelle

#### 1. Docker Desktop
```bash
# Via Homebrew
brew install --cask docker

# Ou télécharger depuis: https://www.docker.com/products/docker-desktop/
```

#### 2. KinD
```bash
# Via Homebrew
brew install kind

# Ou via Go
go install sigs.k8s.io/kind@latest
```

#### 3. kubectl
```bash
# Via Homebrew
brew install kubectl

# Ou via Go
go install k8s.io/kubectl@latest
```

#### 4. Python 3.8+
```bash
# Via Homebrew
brew install python@3.11

# Vérifier l'installation
python3 --version
pip3 --version
```

## Linux (Ubuntu/Debian)

### Installation Automatique (Recommandée)
```bash
# Rendre le script exécutable
chmod +x install_prerequisites.sh
# Exécuter le script d'installation
./install_prerequisites.sh
```

### Installation Manuelle

#### 1. Docker
```bash
# Installation Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Installation Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. KinD
```bash
# Téléchargement direct
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

#### 3. kubectl
```bash
# Installation kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

#### 4. Python 3.8+
```bash
# Installation Python
sudo apt update
sudo apt install python3 python3-pip

# Vérifier l'installation
python3 --version
pip3 --version
```

## Vérification des Prérequis

Après installation, vérifiez que tout fonctionne :

```bash
# Vérifier Docker
docker --version
docker-compose --version

# Vérifier KinD
kind --version

# Vérifier kubectl
kubectl version --client

# Vérifier Python
python --version
# ou
python3 --version

# Vérifier pip
pip --version
# ou
pip3 --version
```

## Dépannage des Prérequis

### Problème : Docker Desktop ne démarre pas
- **Windows :** Vérifiez que l'hyperviseur est activé
- **macOS :** Vérifiez les permissions dans les Préférences Système
- **Linux :** Vérifiez que l'utilisateur est dans le groupe docker

### Problème : KinD ne trouve pas Docker
```bash
# Vérifier que Docker fonctionne
docker info

# Redémarrer Docker Desktop si nécessaire
```

### Problème : kubectl ne fonctionne pas
```bash
# Vérifier la configuration
kubectl config view

# Tester la connexion (après création du cluster)
kubectl cluster-info
```

### Problème : Python/pip non trouvé
```bash
# Windows : Vérifier le PATH
# macOS/Linux : Utiliser python3 et pip3
python3 --version
pip3 --version
```

## Guide d'Installation Rapide KinD

Pour une installation détaillée de KinD, consultez le guide spécialisé :
- **[INSTALL_KIND.md](INSTALL_KIND.md)** - Guide complet d'installation de KinD

## Scripts d'Installation Automatique

Le projet inclut des scripts d'installation automatique pour simplifier le processus :

- **Windows :** `install_prerequisites.ps1`
- **macOS/Linux :** `install_prerequisites.sh`

Ces scripts installent automatiquement tous les prérequis nécessaires et vérifient leur fonctionnement.

## Prochaines Étapes

Une fois tous les prérequis installés :

1. **Redémarrez votre terminal**
2. **Démarrez Docker Desktop** (si nécessaire)
3. **Exécutez le lab :** `./start_lab.sh`

## Support

Si vous rencontrez des problèmes :

1. Vérifiez que tous les prérequis sont installés
2. Consultez la section de dépannage ci-dessus
3. Vérifiez les logs d'installation
4. Redémarrez votre système si nécessaire
