# Installation Rapide de KinD

## Windows

### Option 1: Via Chocolatey (Recommandée)
```powershell
# Installer Chocolatey si pas déjà fait
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Installer KinD
choco install kind -y
```

### Option 2: Via Scoop
```powershell
# Installer Scoop si pas déjà fait
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# Installer KinD
scoop install kind
```

### Option 3: Téléchargement Direct
```powershell
# Télécharger KinD
Invoke-WebRequest -Uri "https://kind.sigs.k8s.io/dl/v0.20.0/kind-windows-amd64" -OutFile "kind.exe"

# Déplacer vers un dossier dans le PATH
Move-Item kind.exe C:\Windows\System32\kind.exe
```

## macOS

### Option 1: Via Homebrew (Recommandée)
```bash
# Installer Homebrew si pas déjà fait
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer KinD
brew install kind
```

### Option 2: Via Go
```bash
# Installer Go si pas déjà fait
brew install go

# Installer KinD
go install sigs.k8s.io/kind@latest
```

## Linux (Ubuntu/Debian)

### Option 1: Téléchargement Direct
```bash
# Télécharger et installer KinD
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
```

### Option 2: Via Snap
```bash
# Installer KinD via Snap
sudo snap install kind --classic
```

## Vérification de l'Installation

```bash
# Vérifier que KinD est installé
kind --version

# Vérifier que Docker fonctionne
docker --version

# Tester KinD
kind create cluster --name test-cluster
kind delete cluster --name test-cluster
```

## Dépannage

### Problème : "kind: command not found"
- Vérifiez que KinD est dans votre PATH
- Redémarrez votre terminal
- Sur Windows, redémarrez PowerShell

### Problème : "Docker not found"
- Vérifiez que Docker Desktop est démarré
- Sur Linux, vérifiez que l'utilisateur est dans le groupe docker :
  ```bash
  sudo usermod -aG docker $USER
  # Puis redémarrez votre session
  ```

### Problème : "Permission denied"
- Sur Linux/macOS, utilisez `sudo` si nécessaire
- Vérifiez les permissions des fichiers

## Ressources

- [Documentation officielle KinD](https://kind.sigs.k8s.io/)
- [Guide d'installation KinD](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [Dépannage KinD](https://kind.sigs.k8s.io/docs/user/quick-start/#troubleshooting)
