# Lab SRE - Environnement Pédagogique

Un environnement SRE complet, conteneurisé et réutilisable pour apprendre les pratiques de Site Reliability Engineering.

## Objectif

Ce lab permet aux participants de :
- Observer un service (URL shortener) via logs, métriques et traces
- Définir et implémenter les SLIs et SLOs
- Mettre en place les "golden signals"
- Simuler des incidents à diagnostiquer et réparer
- Rédiger des post-mortems collaboratifs
- Introduire les concepts d'error budget et de burn rate
- Expérimenter la réduction du "toil" (tâches manuelles)

## Stack Technique

- **Kubernetes :** KinD (Kubernetes in Docker)
- **Application :** Microservice URL Shortener
- **Observabilité :** Splunk Enterprise Trial
- **Instrumentation :** OpenTelemetry (Collector OTLP/gRPC)
- **Scripts :** Python et Bash
- **Monitoring :** Prometheus + Grafana (optionnel)

## Structure du Projet

```
SRE/
├── docker-compose.yml              # Déploie Splunk Enterprise Trial
├── kind/
│   ├── kind-config.yaml           # Configuration du cluster KinD
│   ├── manifests/                 # YAML K8s pour URL shortener + OpenTelemetry
│   └── setup.sh                   # Script de déploiement
├── scripts/                       # Scripts de démarrage et validation
│   ├── start_lab.sh              # Démarrage automatique (Linux/macOS)
│   ├── start_lab.ps1             # Démarrage automatique (Windows)
│   ├── validate_lab.sh           # Validation du lab (Linux/macOS)
│   ├── validate_lab.ps1          # Validation du lab (Windows)
│   ├── test_lab.py               # Tests automatisés du lab
│   ├── validate_setup.py         # Validation des prérequis
│   ├── validate_setup_simple.py  # Validation simple des prérequis
│   ├── install_prerequisites.sh  # Installation prérequis (Linux/macOS)
│   └── install_prerequisites.ps1 # Installation prérequis (Windows)
├── data/
│   ├── logs/                      # Logs simulés sur 30 jours
│   ├── metrics/                   # Métriques simulées
│   └── traces/                    # Traces simulées
├── exercises/
│   └── README.md                  # Exercices détaillés du lab SRE
├── simulator/
│   └── traffic_generator.py       # Génère le trafic simulé
├── ingest/
│   └── ingest_to_splunk.py        # Injecte les données simulées
├── incident/
│   ├── trigger_failure.sh         # Script pour provoquer des pannes
│   ├── fix_failure.sh             # Script pour réparer les pannes
│   └── postmortem_template.md     # Template pour le post-mortem
├── postmortem/
│   ├── app.py                     # Application Flask pour les post-mortems
│   ├── templates/                 # Templates HTML pour l'interface web
│   ├── data/postmortems/          # Données des post-mortems (JSON)
│   └── requirements.txt           # Dépendances Python Flask
├── automation/
│   └── toil_reduction.sh          # Scripts d'automatisation
├── sre/
│   ├── slo_config.json            # Définition des SLOs
│   ├── burn_rate_calc.py          # Calcul du burn rate
│   └── error_budget_tracker.py    # Suivi de l'error budget
├── otel-collector-config.yml      # Configuration OpenTelemetry
├── requirements.txt               # Dépendances Python
├── config.json                    # Configuration du lab
├── PREREQUIS.md                   # Guide d'installation
└── README.md                      # Ce fichier
```

## Démarrage Rapide

### Prérequis

- Docker et Docker Compose
- KinD (Kubernetes in Docker)
- kubectl
- Python 3.8+
- Git

## Démarrage du Lab

### Démarrage automatique (recommandé)

**Linux/macOS :**
```bash
./scripts/start_lab.sh
```

**Windows PowerShell :**
```powershell
.\scripts\start_lab.ps1
```

### Démarrage manuel

1. **Démarrer Splunk et OpenTelemetry** :
   ```bash
   docker-compose up -d
   ```

2. **Déployer le cluster KinD** :
   ```bash
   cd kind
   chmod +x setup.sh
   ./setup.sh
   cd ..
   ```

3. **Vérifier le déploiement** :
   ```bash
   kubectl get pods
   kubectl get services
   ```

## Exercices SRE

**📚 Guide complet des exercices :** [exercises/README.md](exercises/README.md)

**Le premier exercice inclut la configuration Splunk nécessaire pour recevoir les métriques.**

## Installation des Prérequis

> **[Guide Complet]** [PREREQUIS.md](PREREQUIS.md) - Installation détaillée pour Windows, macOS et Linux

### Installation Rapide

**Windows :**
```powershell
# Exécuter en tant qu'administrateur
Set-ExecutionPolicy Bypass -Scope Process -Force
.\scripts\install_prerequisites.ps1
```

**macOS/Linux :**
```bash
# Rendre le script exécutable
chmod +x scripts/install_prerequisites.sh
# Exécuter l'installation
./scripts/install_prerequisites.sh
```

### Prérequis Nécessaires

- Docker et Docker Compose
- KinD (Kubernetes in Docker)
- kubectl
- Python 3.8+
- Git

### Vérification Rapide

```bash
# Vérifier l'installation
docker --version && kind --version && kubectl version --client && python --version
```

### Installation

1. **Cloner le projet**
   ```bash
   git clone <repository-url>
   cd SRE
   ```

2. **Démarrer Splunk**
   ```bash
   docker-compose up -d
   ```

3. **Déployer le cluster KinD**
   ```bash
   cd kind
   chmod +x setup.sh
   ./setup.sh
   ```

4. **Vérifier le déploiement**
   ```bash
   # Validation automatique (Linux/macOS)
   ./scripts/validate_lab.sh
   
   # Validation automatique (Windows PowerShell)
   .\scripts\validate_lab.ps1
   
   # Validation manuelle
   kubectl get pods
   kubectl get services
   ```

### Accès aux Services

- **URL Shortener :** http://localhost:30000
  - Interface web + API REST
  - Endpoints : `/shorten`, `/health`, `/metrics`
- **Splunk :** http://localhost:8000 (admin/admin123)
  - Interface web + HEC sur port 9997
- **OpenTelemetry Collector :** http://localhost:8889/metrics
  - Métriques Prometheus
  - OTLP : gRPC (4317), HTTP (4318)
- **Post-Mortems Interface :** http://localhost:30001
  - Interface web Flask pour les post-mortems
  - Gestion et visualisation des incidents


## Exercices

> **[Exercices Détaillés]** [exercises/README.md](exercises/README.md) - Guide complet des exercices SRE avec objectifs, étapes et livrables

Les exercices sont organisés par difficulté croissante et couvrent tous les aspects du SRE :

- **Exercice 1** : Déploiement et Observabilité (**)
- **Exercice 2** : Définition des SLIs/SLOs (***)  
- **Exercice 3** : Error Budget et Burn Rate (***)
- **Exercice 4** : Simulation d'Incident et Collaboration (****)
- **Exercice 5** : Automatisation pour Réduire le Toil (****)
- **Bonus** : Mode Chaos (*****)

## Scripts et Outils

### Générateur de Trafic

```bash
cd simulator
python traffic_generator.py --duration 60 --rpm 100 --error-rate 0.01
```

### Ingestion de Données

```bash
cd ingest
python ingest_to_splunk.py --logs 10000 --metrics 5000 --traces 3000
```

### Simulation d'Incidents

```bash
cd incident
./trigger_failure.sh          # Menu interactif
./trigger_failure.sh crash    # Crash de pods
./trigger_failure.sh latency  # Latence extrême
```

### Réparation d'Incidents

```bash
cd incident
./fix_failure.sh              # Menu interactif
./fix_failure.sh pods         # Restaurer les pods
./fix_failure.sh cleanup        # Nettoyage complet
```

### Interface Post-Mortems

L'application Flask pour les post-mortems est automatiquement déployée dans le cluster KinD et accessible via http://localhost:30001

**Fonctionnalités :**
- Visualisation des post-mortems avec format structuré
- Création de nouveaux post-mortems
- Interface responsive et professionnelle
- API REST pour l'intégration

### Calcul du Burn Rate

```bash
cd sre
python burn_rate_calc.py --hours 24 --verbose
```

### Suivi de l'Error Budget

```bash
cd sre
python error_budget_tracker.py --monitor --interval 5
```

### Automatisation

```bash
cd automation
./toil_reduction.sh           # Menu interactif
./toil_reduction.sh continuous # Surveillance continue
```

## Monitoring et Alertes

### Métriques Disponibles

- **Disponibilité :** Taux de requêtes réussies
- **Latence :** P50, P95, P99 des requêtes
- **Trafic :** Requêtes par seconde
- **Erreurs :** Taux d'erreurs 4xx et 5xx

### Dashboards Splunk

1. **Golden Signals Dashboard**
   - Latence, trafic, erreurs, saturation
   - Vues en temps réel et historiques

2. **SLO Dashboard**
   - Error budget et burn rate
   - Violations de SLO
   - Tendances sur 30 jours

3. **Incident Dashboard**
   - Événements d'incident
   - Temps de résolution
   - Fréquence des pannes

### Alertes Configurées

- **Burn Rate Critique :** > 6x (Error budget épuisé en < 1h)
- **Burn Rate Élevé :** > 2x (Error budget épuisé en < 6h)
- **Disponibilité Critique :** < 99.5%
- **Latence P99 :** > 3s

## Configuration

### Variables d'Environnement

```bash
# Splunk
SPLUNK_URL=http://localhost:8000
SPLUNK_HEC_TOKEN=your-hec-token-here

# Prometheus
PROMETHEUS_URL=http://localhost:9090

# Service
SERVICE_URL=http://localhost:30000
```

> **⚠️ Sécurité :** Configurez votre token HEC Splunk via la variable d'environnement `SPLUNK_HEC_TOKEN`. Voir le fichier `env.example` pour un exemple de configuration.

### Personnalisation

1. **SLOs :** Modifiez `sre/slo_config.json`
2. **Métriques :** Ajustez les requêtes Prometheus
3. **Alertes :** Configurez les seuils dans Splunk
4. **Automatisation :** Étendez `automation/toil_reduction.sh`

## Dépannage

### Problèmes Courants

1. **Service inaccessible**
   ```bash
   kubectl get pods
   kubectl logs -l app=url-shortener
   ```

2. **Splunk non accessible**
   ```bash
   docker-compose ps
   docker-compose logs splunk
   ```

3. **Métriques manquantes**
   ```bash
   kubectl get pods -l app=otel-collector
   kubectl logs -l app=otel-collector
   ```

### Logs Utiles

```bash
# Logs du service
kubectl logs -l app=url-shortener -f

# Logs OpenTelemetry
kubectl logs -l app=otel-collector -f

# Logs Splunk
docker-compose logs splunk -f
```

## Ressources

### Documentation SRE

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [SRE Workbook](https://sre.google/workbook/table-of-contents/)
- [Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)

### Outils et Technologies

- [KinD Documentation](https://kind.sigs.k8s.io/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Splunk Documentation](https://docs.splunk.com/)
- [Prometheus](https://prometheus.io/docs/)

## Contribution

1. Fork le projet
2. Créez une branche feature
3. Committez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Auteurs

- **Fabio** - *Créateur du lab SRE*

## Remerciements

- Équipe Google SRE pour l'inspiration
- Communauté OpenTelemetry
- Équipe KinD pour l'outil de développement

---

**Lab SRE - Version 1.0**  
**Dernière mise à jour :** 2024
