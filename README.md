# Reskilling - Lab SRE E-Commerce

Lab complet pour apprendre les pratiques SRE en auditant une boutique e-commerce tech réaliste.

## Contexte

Vous êtes engagé comme consultant SRE pour auditer **CapShop**, une boutique e-commerce tech premium. Le site rencontre des problèmes de fiabilité et la direction vous demande de :

- Mettre en place une observabilité complète
- Définir des SLOs pertinents
- Investiguer et résoudre des incidents
- Proposer des automatisations

## Démarrage rapide

```bash
./start.sh          # ou: make start
make test           # verifie les 13 composants
make stop
```

Prerequis, installation de Docker et depannage : voir
**[QUICKSTART.md](QUICKSTART.md)**.

Pour un deploiement multi-apprenants sur Kubernetes, un namespace chacun :
voir **[helm/README.md](helm/README.md)**.

## Interfaces disponibles

| Service | URL | Description |
|---------|-----|-------------|
| Boutique CapShop | http://localhost:8080 | Site e-commerce à auditer |
| Operations Console | http://localhost:8090 | Gestion incidents/post-mortems |
| Grafana | http://localhost:3000 | Dashboards (admin, mot de passe affiché par `./start.sh`) |
| Prometheus | http://localhost:9090 | Métriques |
| Loki | interne au reseau Docker | Logs, interroges depuis Grafana |
| Tempo | interne au reseau Docker | Traces, interrogees depuis Grafana |
| Alertmanager | http://localhost:9093 | Alertes |
| Locust | http://localhost:8089 | Générateur de trafic |

## Architecture

```
                    +---------------------------------+
                    |      API Gateway (:8080)        |
                    |  Boutique CapShop + routage API |
                    +----------------+----------------+
                                     |
     +---------------+---------------+---------------+---------------+
     |               |               |               |               |
     v               v               v               v               v
+----------+   +----------+   +----------+   +----------+   +----------+
| Catalog  |   |   Cart   |   |  Users   |   |  Orders  |-->| Payment  |
| (:8081)  |   | (:8082)  |   | (:8085)  |   | (:8083)  |   | (:8084)  |
|          |   |  Redis   |   |   JWT    |   |          |   | Circuit  |
|          |   |          |   |          |   |          |   | Breaker  |
+-----+----+   +----------+   +-----+----+   +-----+----+   +----------+
      |                             |              |
      +-------------+---------------+--------------+
                    v
          +--------------------+
          | PostgreSQL (:5432) |   Schemas: catalog, orders, users, lab
          +--------------------+   (interne au reseau Docker)
```

| Donnee | Stockage |
|---|---|
| Produits, commandes, comptes, objets du lab | PostgreSQL |
| Panier | Redis (TTL 24h) |

### Socle commun

Les 5 services metier partagent `microservices/_shared/` :

| Module | Role |
|---|---|
| `observability.py` | Logging, OpenTelemetry, CORS, auto-instrumentation |
| `chaos.py` | `ChaosController` : injection pilotable a chaud |
| `ops.py` | `/health`, `/ready`, `/metrics`, `/api/chaos` |
| `db.py` | Pool asyncpg avec metriques Prometheus |

L'API Gateway a sa propre implementation : son `/health` agrege l'etat des
services amont et repond `degraded` si l'un d'eux est indisponible.

### Stack d'observabilité

```
+---------------------------------------------------------------------+
|                          Grafana (:3000)                            |
|              Dashboards - Explore - Alerting                        |
+-------------------------------+-------------------------------------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
+---------------+     +---------------+     +---------------+
|  Prometheus   |     |     Loki      |     |    Tempo      |
|   (:9090)     |     |    (interne)  |     |   (interne)   |
|   Métriques   |     |     Logs      |     |    Traces     |
+-------+-------+     +---------------+     +---------------+
        |
        +----------+----------+----------+----------+
        v          v          v          v          v
  +----------+ +--------+ +--------+ +--------+ +----------+
  | Alert-   | |Blackbox| | Redis  | |Postgres| |  OTel    |
  | manager  | |Exporter| |Exporter| |Exporter| |Collector |
  | (:9093)  | |        | |        | |        | | (:4317)  |
  +----------+ +--------+ +--------+ +--------+ +----------+
```

Loki, Tempo et les exporters s'interrogent depuis Grafana. Prometheus les
scrape sur le reseau Docker.

## Les 3 piliers de l'observabilité

### 1. Métriques (Prometheus)

Accès : http://localhost:9090 ou via Grafana

```promql
# Requêtes par seconde par service (vues depuis l'API Gateway)
sum by (service) (rate(gateway_requests_total[5m]))

# Latence P99 (exemple : service payment)
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[5m])))

# Taux d'erreur global
sum(rate(gateway_requests_total{status=~"5.."}[5m])) / sum(rate(gateway_requests_total[5m]))
```

### 2. Logs (Loki)

Grafana > Explore > source de donnees **Loki**.

```logql
# Tous les logs du payment service
{job="payment-service"}

# Erreurs uniquement
{job="payment-service"} |= "error"

# Reponses 5xx sur la gateway
{job="api-gateway"} |~ " 5[0-9]{2} "

# Taux d'erreur par service
sum by (job) (rate({job=~".+-service"} |= "error" [5m]))
```

Le label `job` porte le nom du conteneur : `api-gateway`, `catalog-service`,
`cart-service`, `orders-service`, `payment-service`, `users-service`,
`lab-controller`.

### 3. Traces (Tempo)

Grafana > Explore > source de donnees **Tempo**.

| Onglet | Usage |
|---|---|
| Search | Filtrer par service, nom de span ou duree |
| TraceQL | `{ resource.service.name = "orders-service" }` |
| TraceID | Ouvrir une trace precise |

Une trace de checkout traverse api-gateway, orders-service, cart-service,
payment-service et catalog-service. Le graphe de services (Grafana >
Explore > Tempo > Service Graph) reconstruit ces appels a partir des
metriques generees par Tempo.

## Scénarios d'incidents

L'Operations Console (http://localhost:8090) permet de déclencher des incidents réalistes :

### 1. Payment Latency (P1)
- **Impact** : Checkouts lents, circuit breaker peut s'ouvrir
- **Symptômes** : Latence P99 > 3s
- **Investigation** : Dashboard Payment, traces Tempo

### 2. Catalog Errors (P2)
- **Impact** : Produits non affichés
- **Symptômes** : 30% erreurs 500
- **Investigation** : Logs Loki, métriques erreurs

### 3. Database Saturation (P1)
- **Impact** : Tous services dégradés
- **Symptômes** : Latence généralisée
- **Investigation** : Corrélation traces, métriques système

### 4. Cart Service Down (P2)
- **Impact** : Impossible d'ajouter au panier
- **Symptômes** : 80% erreurs
- **Investigation** : Logs pods, métriques mémoire

### 5. Auth Failures (P1)
- **Impact** : Aucune connexion possible
- **Symptômes** : 90% erreurs login
- **Investigation** : Logs JWT, config

## Injection de chaos manuelle

```bash
# Ajouter 3s de latence au payment service
make chaos SERVICE=payment LATENCY=3000

# Injecter 30% d'erreurs au catalog
make chaos SERVICE=catalog ERRORS=0.3

# Combiné : latence + erreurs
make chaos SERVICE=payment LATENCY=2000 ERRORS=0.2

# Arrêter le chaos
make chaos-stop
```

## Workflow incident > post-mortem

1. **Alerte** : Détection via Grafana/Alertmanager
2. **Triage** : Évaluation de la sévérité (P1-P4)
3. **Investigation** : Utilisation des 3 piliers
4. **Résolution** : Fix et validation
5. **Post-mortem** : Documentation via Operations Console

## Structure du projet

```
├── microservices/
│   ├── _shared/               # Socle commun aux 5 services metier
│   │   ├── observability.py   #   logging, OTel, CORS
│   │   ├── chaos.py           #   ChaosController
│   │   ├── ops.py             #   /health /ready /metrics /api/chaos
│   │   └── db.py              #   pool asyncpg + metriques
│   ├── requirements-base.txt  # Dependances communes
│   ├── api-gateway/           # Boutique CapShop + routage (static/)
│   ├── catalog-service/       # Produits (PostgreSQL)
│   ├── cart-service/          # Panier (Redis)
│   ├── orders-service/        # Commandes (PostgreSQL)
│   ├── payment-service/       # Paiements + Circuit Breaker
│   └── users-service/         # Auth JWT (PostgreSQL)
│
├── observability/
│   ├── postgres/init/         # Schema SQL + donnees initiales
│   ├── prometheus/            # Métriques + règles d'alertes
│   ├── loki/ tempo/           # Logs et traces
│   ├── grafana/               # Dashboards + provisioning
│   ├── alertmanager/          # Gestion alertes
│   ├── promtail/ blackbox/    # Collecte logs et probes
│   └── otel-collector-config.yml
│
├── lab-controller/api/        # Operations Console
│   ├── main.py                #   incidents, post-mortems, toil
│   ├── store.py               #   stockage persistant (PostgreSQL)
│   └── static/                #   frontend
│
├── traffic-generator/         # Locust
├── helm/                      # Chart Kubernetes, un namespace par apprenant
├── docs/                      # Documentation + runbooks
├── exercises/                 # Guides d'exercices
│
├── .env.example               # Secrets a copier en .env
├── docker-compose.yml
├── start.sh + Makefile (make help)
└── README.md
```

## Documentation

### Guides
- [Démarrage rapide](QUICKSTART.md)
- [Déploiement Kubernetes](helm/README.md)
- [Observabilité (Prometheus/Loki/Tempo)](docs/OBSERVABILITY.md)
- [SLOs et Alerting](docs/SLOS_ALERTING.md)
- [Incidents et Post-Mortems](docs/INCIDENTS.md)

### Runbooks
- [Payment Latency](docs/runbooks/payment-latency.md)
- [Catalog Errors](docs/runbooks/catalog-errors.md)
- [Service Down](docs/runbooks/service-down.md)
- [Database Saturation](docs/runbooks/database-saturation.md)

### Exercices
- [Exercices pratiques](exercises/README.md) (exercices bonus, avec aides et réponses)

## Ressources

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)

## Base de données

```bash
# Ouvrir un shell SQL
make psql

# Compter les lignes par table
make db-stats
```

Quatre schemas, un par domaine metier :

| Schema | Contenu |
|---|---|
| `catalog` | Produits, categories |
| `orders` | Commandes, lignes de commande |
| `users` | Comptes, sessions |
| `lab` | Incidents, post-mortems, toil (JSONB) |

```sql
-- Exemples pour les exercices
SELECT status, count(*) FROM lab.incidents GROUP BY status;
SELECT * FROM orders.orders ORDER BY created_at DESC LIMIT 10;
SELECT name, stock FROM catalog.products WHERE stock < 20;
```

Le scenario **Database Saturation** s'appuie sur ce dimensionnement :
`DB_POOL_MAX=10` par service, `max_connections=50` cote serveur.

## Configuration

Aucun secret n'est ecrit dans le depot. Au premier lancement, `./start.sh`
genere un fichier `.env` avec des valeurs aleatoires, a partir de
`.env.example`. Sans ce fichier, `docker compose` refuse de demarrer.

| Variable | Role |
|---|---|
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL |
| `JWT_SECRET` | Signature des tokens |
| `GRAFANA_ADMIN_PASSWORD` | Acces Grafana |
| `DB_POOL_MAX` | Taille du pool (scenario de saturation) |
| `CORS_ORIGINS` | Origines autorisees (defaut `*`) |

Les conteneurs tournent en utilisateur non privilegie (`appuser`), avec
des limites memoire et CPU. PostgreSQL, Redis, Loki, Tempo et les
exporters sont joignables uniquement sur le reseau Docker.

## Commandes Make

```bash
make help              # Liste toutes les commandes
make start             # Démarre le lab
make stop              # Arrête le lab
make status            # Status des services
make test              # Vérifie tous les services
make logs              # Affiche les logs
make logs-payment      # Logs d'un service spécifique
make urls              # Affiche toutes les URLs

# Base de données
make psql              # Shell PostgreSQL
make db-stats          # Lignes par table

# Incidents
make incident-payment  # Déclenche latence payment
make incident-catalog  # Déclenche erreurs catalog
make incident-resolve  # Résout les incidents
make incident-list     # Liste les incidents actifs

# Chaos
make chaos SERVICE=payment LATENCY=3000 ERRORS=0.3
make chaos-status      # Etat du chaos sur les 5 services
make chaos-stop        # Arrête le chaos partout

# Tests
make test-purchase     # Simule un achat complet
```

## Commandes de diagnostic

```bash
# Voir les conteneurs
docker compose ps

# Logs d'un service
docker compose logs --follow payment-service

# Redémarrer un service
docker compose restart payment-service

# Verifier la connexion a la base
curl http://localhost:8081/ready

# Tout nettoyer et reconstruire
make clean && make start
```
