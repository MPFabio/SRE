# Application fil rouge DevOps / SRE

Application fil rouge des parcours DevOps Infra et DevOps SRE : une
boutique e-commerce en microservices, livrée avec une stack
d'observabilité complète. Chaque apprenant la déploie dans son namespace du
cluster EKS, y ajoute son propre module, puis l'observe, la casse et la
répare.

## Par où commencer

| Vous voulez... | Document |
|---|---|
| Installer l'application fil rouge dans votre namespace EKS | [AWS_SECURE/Readme.md](AWS_SECURE/Readme.md) |
| Faire les exercices de la formation (fil rouge) | [Exercices du parcours](exercises/README.md) |
| Développer et brancher votre module fil rouge | [fil-rouge/README.md](fil-rouge/README.md) |
| Provoquer des pannes, les diagnostiquer et les corriger | [chaos/README.md](chaos/README.md) |
| Aller plus loin : architecture, observabilité, incidents, SLOs, toil | [Exercices bonus](exercises/bonus/README.md) |
| Faire tourner l'application fil rouge sur votre poste avec Docker | [QUICKSTART.md](QUICKSTART.md) |

## Interfaces

Sur EKS, ces adresses s'ouvrent depuis votre poste par un tunnel SSH, ou
avec le nom de la VM à la place de `localhost` si vous passez par FoxyProxy
(voir l'installation, étape 8).

| Service | URL | Rôle |
|---------|-----|------|
| Boutique CapShop | http://localhost:8080 | Le site e-commerce |
| Operations Console | http://localhost:8090 | Incidents, post-mortems, toil |
| Grafana | http://localhost:3000 | Dashboards, Explore (logs et traces) |
| Prometheus | http://localhost:9090 | Métriques et alertes |
| Alertmanager | http://localhost:9093 | Routage des alertes |
| Locust | http://localhost:8089 | Générateur de trafic |

Loki et Tempo n'ont pas d'interface propre : on les interroge depuis Grafana.

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
          +--------------------+        +----------------------+
          | PostgreSQL (:5432) |        | Votre module (:8086) |
          +--------------------+        |  Go, Python, autre   |
                                        +----------------------+
```

| Donnée | Stockage |
|---|---|
| Produits, commandes, comptes, objets de l'application fil rouge | PostgreSQL (schémas `catalog`, `orders`, `users`, `lab`) |
| Panier | Redis (TTL 24h) |

Les cinq services métier partagent un socle, `microservices/_shared/` :
observabilité (logs, OpenTelemetry), injection de chaos, routes `/health`,
`/ready`, `/metrics` et `/api/chaos`, pool PostgreSQL instrumenté. La
gateway a sa propre implémentation : son `/health` agrège l'état des
services et répond `degraded` si l'un d'eux est indisponible.

Votre module rejoint cette architecture à côté des six services : l'application fil rouge le
déploie, le surveille et collecte ses logs et ses traces comme les autres.

### Observabilité

```
+---------------------------------------------------------------------+
|                          Grafana (:3000)                            |
+-------------------------------+-------------------------------------+
        |                       |                       |
        v                       v                       v
+---------------+     +---------------+     +---------------+
|  Prometheus   |     |     Loki      |     |    Tempo      |
|   Métriques   |     |     Logs      |     |    Traces     |
+-------+-------+     +-------^-------+     +-------^-------+
        |                     |                     |
        |               Promtail (logs        OTel Collector
        |               des pods)             (:4317, OTLP)
        v
  Alertmanager, Blackbox, exporters Redis et PostgreSQL
```

- **Métriques** : Prometheus scrape `/metrics` de chaque service.
- **Logs** : Promtail lit le stdout des pods ; le label `job` porte
  le nom du container (`{job="payment-service"}`).
- **Traces** : les services envoient leurs spans en OTLP au collecteur, qui
  les transmet à Tempo.

Requêtes et usages détaillés : [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md).

## Incidents simulés

L'Operations Console déclenche des incidents en injectant des pannes dans
les services :

| Scénario | Sévérité | Panne injectée |
|---|---|---|
| Latence du paiement | P1 | +3 s sur l'appel au prestataire de paiement |
| Erreurs du catalogue | P2 | 30 % d'erreurs 500 sur catalog |
| Saturation de la base | P1 | +2 s et 20 % d'erreurs sur catalog |
| Panier indisponible | P2 | 80 % d'erreurs sur cart |
| Échecs d'authentification | P1 | 90 % d'erreurs sur users |

Chaque incident est livré avec des témoignages fictifs, à vérifier contre
les métriques : ils ne disent pas toujours vrai. Les runbooks aident à
l'investigation :
[latence du paiement](docs/runbooks/payment-latency.md),
[erreurs du catalogue](docs/runbooks/catalog-errors.md),
[service indisponible](docs/runbooks/service-down.md),
[saturation de la base](docs/runbooks/database-saturation.md).

## Diagnostic sur Kubernetes

```bash
kubectl get pods                                   # état des pods
kubectl logs deploy/payment-service --tail 50      # logs d'un service
kubectl describe pod -l app=payment-service        # événements, redémarrages
kubectl rollout restart deployment/payment-service # redémarrer un service
kubectl exec deploy/catalog-service -- curl --silent localhost:8081/ready
kubectl exec -it statefulset/postgres -- psql --username=capshop --dbname=capshop
```

## Structure du projet

```
├── AWS_SECURE/                # Installation de l'application fil rouge dans un namespace EKS
├── chaos/                     # Pannes réelles à diagnostiquer et corriger
├── fil-rouge/                 # Conditions d'intégration + module d'exemple
│   ├── ci/                    #   pipeline GitLab d'exemple
│   └── reviews-service/       #   avis produits, en Python et en Go
├── microservices/
│   ├── _shared/               # Socle commun aux 5 services métier
│   ├── api-gateway/           # Boutique CapShop + routage (static/)
│   ├── catalog-service/       # Produits (PostgreSQL)
│   ├── cart-service/          # Panier (Redis)
│   ├── orders-service/        # Commandes (PostgreSQL)
│   ├── payment-service/       # Paiements + circuit breaker
│   └── users-service/         # Authentification JWT (PostgreSQL)
├── lab-controller/api/        # Operations Console
├── traffic-generator/         # Locust
├── helm/                      # Chart Kubernetes, un namespace par apprenant
├── observability/             # Configurations Prometheus, Grafana, Loki...
├── docs/                      # Guides et runbooks
├── exercises/                 # Exercices du parcours, avec aides et réponses
│   └── bonus/                 #   exercices facultatifs pour aller plus loin
├── docker-compose.yml         # Mode local
└── start.sh + Makefile        # Mode local
```

## Documentation

- [Installation sur EKS](AWS_SECURE/Readme.md)
- [Module fil rouge](fil-rouge/README.md)
- [Observabilité](docs/OBSERVABILITY.md)
- [SLOs et alerting](docs/SLOS_ALERTING.md)
- [Incidents et post-mortems](docs/INCIDENTS.md)
- [Exercices du parcours](exercises/README.md)
- [Exercices bonus](exercises/bonus/README.md)

## Mode local (Docker Compose)

Pour développer ou tester l'application fil rouge sur un poste, sans cluster :

```bash
./start.sh          # ou : make start
make test           # vérifie les composants
make stop
```

Prérequis, secrets et dépannage : [QUICKSTART.md](QUICKSTART.md).
`./start.sh` génère un fichier `.env` avec des secrets aléatoires ; aucun
secret n'est écrit dans le repo.

Commandes utiles (`make help` pour la liste complète) :

```bash
make status                                  # état des services
make logs-payment                            # logs d'un service
make incident-payment                        # déclenche un incident
make incident-resolve                        # résout les incidents actifs
make chaos SERVICE=payment LATENCY=3000      # chaos manuel
make chaos-stop                              # arrête le chaos
make psql                                    # shell PostgreSQL
make test-purchase                           # simule un achat complet
```

## Ressources

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Prometheus](https://prometheus.io/docs/)
- [Grafana](https://grafana.com/docs/), [Loki](https://grafana.com/docs/loki/), [Tempo](https://grafana.com/docs/tempo/)
- [OpenTelemetry](https://opentelemetry.io/docs/)
