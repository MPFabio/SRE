# Démarrage rapide - Reskilling SRE Lab

## 1. Prérequis

- Docker Engine 20.10+ et Compose v2
- 4 Go de RAM disponibles pour Docker
- Ports libres : 3000, 4317, 8080-8085, 8089, 8090, 8889, 9090, 9093

### Installer Docker

**Windows (WSL2)**

```bash
wsl --install -d Ubuntu
```

Puis, dans la distribution WSL, suivre les instructions Linux ci-dessous.

Avec Docker Desktop : activer l'integration WSL2 dans
*Settings > Resources > WSL Integration*.

**Linux et WSL2 (Ubuntu/Debian)**

```bash
curl --fail --silent --show-error --location https://get.docker.com --output get-docker.sh
sudo sh get-docker.sh
sudo usermod --append --groups docker $USER
```

Ouvrir un nouveau terminal pour appliquer les permissions.

**macOS**

```bash
brew install colima
colima start
```

Ou [Docker Desktop](https://www.docker.com/products/docker-desktop/).

**Verifier**

```bash
docker --version
docker compose version
docker run --rm hello-world
```

## 2. Démarrer

```bash
# Cloner le repo
git clone https://github.com/MPFabio/SRE.git
cd SRE

# Démarrer le lab
./start.sh
# ou
make start
```

Première exécution : ~5 minutes (téléchargement des images)

## 3. Accéder aux interfaces

| Interface | URL | Credentials |
|-----------|-----|-------------|
| Boutique CapShop | http://localhost:8080 | - |
| Operations Console | http://localhost:8090 | - |
| Grafana | http://localhost:3000 | admin / mot de passe affiché par `./start.sh` |
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| Locust (generateur de trafic) | http://localhost:8089 | - |

## 4. Vérifier que tout fonctionne

```bash
make test
```

## 5. Configuration

Au premier lancement, `./start.sh` cree le fichier `.env` a partir de
`.env.example`, avec des valeurs aleatoires pour `POSTGRES_PASSWORD`,
`JWT_SECRET` et `GRAFANA_ADMIN_PASSWORD`. Ce fichier reste sur le poste et
n'est jamais commite.

Pour imposer vos propres valeurs, creez-le avant le premier lancement :

```bash
cp .env.example .env
```

Les mots de passe PostgreSQL et Grafana ne sont lus qu'a l'initialisation des
volumes. Pour les changer ensuite : `make clean`, modifier `.env`, puis
`make start`.

## 6. Premier exercice : Déclencher un incident

```bash
# Via l'interface
# Ouvrez http://localhost:8090 et cliquez sur "Payment Latency"

# Ou via CLI
make incident-payment
```

Observez l'impact dans :
- La boutique (checkout lent)
- Grafana (métriques en rouge)
- Les logs (erreurs)

## 7. Résoudre l'incident

```bash
make incident-resolve
```

## 8. Arrêter le lab

```bash
make stop          # arrete les conteneurs
make clean         # arrete et supprime les volumes (base incluse)
```

## Commandes utiles

```bash
make help          # Liste toutes les commandes
make status        # Status des services
make logs          # Logs de tous les services
make logs-payment  # Logs d'un service spécifique
make urls          # Affiche toutes les URLs
make test-purchase # Simule un achat
make psql          # Shell PostgreSQL
make db-stats      # Lignes par table
make chaos-status  # Etat du chaos sur les 5 services
```

## Problèmes courants

### Port déjà utilisé
```bash
# Trouver ce qui utilise le port
lsof -i :8080  # Linux/macOS
netstat -ano | findstr :8080  # Windows
```

### Conteneurs qui crashent
```bash
make clean  # Nettoie tout (volumes compris)
make start  # Redémarre
```

### Mémoire insuffisante

Conteneurs arretes en `OOMKilled` : augmenter la RAM allouee a Docker.

Sous WSL2, dans `%UserProfile%\.wslconfig` :

```ini
[wsl2]
memory=6GB
```

Puis `wsl --shutdown`.

### Erreur "Cannot connect to Docker daemon"

```bash
sudo service docker start
```

Avec Docker Desktop : verifier que l'application est lancee.

### Le build echoue

```bash
docker compose down --volumes
docker system prune --force
./start.sh
```

### Un service ne se connecte pas a la base
```bash
curl http://localhost:8081/ready   # doit renvoyer "database":"up"
docker compose logs postgres --tail 30
```

### Le schema SQL a change
```bash
docker compose down
docker volume rm sre_postgres-data   # le schema est rejoue au demarrage
make start
```

## Prochaines étapes

1. Lire le [README](README.md) complet
2. Faire les [exercices](exercises/README.md)
3. Explorer les [dashboards Grafana](http://localhost:3000)
4. Consulter la [documentation](docs/)
