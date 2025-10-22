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
├── data/
│   ├── logs/                      # Logs simulés sur 30 jours
│   ├── metrics/                   # Métriques simulées
│   └── traces/                    # Traces simulées
├── simulator/
│   └── traffic_generator.py       # Génère le trafic simulé
├── ingest/
│   └── ingest_to_splunk.py        # Injecte les données simulées
├── incident/
│   ├── trigger_failure.sh         # Script pour provoquer des pannes
│   ├── fix_failure.sh             # Script pour réparer les pannes
│   └── postmortem_template.md     # Template pour le post-mortem
├── automation/
│   └── toil_reduction.sh          # Scripts d'automatisation
├── sre/
│   ├── slo_config.json            # Définition des SLOs
│   ├── burn_rate_calc.py          # Calcul du burn rate
│   └── error_budget_tracker.py    # Suivi de l'error budget
└── README.md                      # Ce fichier
```

## Démarrage Rapide

### Prérequis

- Docker et Docker Compose
- KinD (Kubernetes in Docker)
- kubectl
- Python 3.8+
- Git

## Installation des Prérequis

> **📋 Guide Complet :** [PREREQUIS.md](PREREQUIS.md) - Installation détaillée pour Windows, macOS et Linux

### Installation Rapide

**Windows :**
```powershell
# Exécuter en tant qu'administrateur
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install_prerequisites.ps1
```

**macOS/Linux :**
```bash
./install_prerequisites.sh
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
   ./validate_lab.sh
   
   # Validation automatique (Windows PowerShell)
   .\validate_lab.ps1
   
   # Validation manuelle
   kubectl get pods
   kubectl get services
   ```

### Accès aux Services

- **URL Shortener :** http://localhost:30000
- **Splunk :** http://localhost:8000 (admin/admin123)
- **OpenTelemetry Collector :** http://localhost:8889/metrics

## Exercices

### Exercice 1 : Déploiement et Observabilité

**Objectif :** Déployer l'environnement et vérifier la visibilité des données.

**Étapes :**
1. Déployer le cluster KinD et les composants
2. Vérifier que le service URL Shortener fonctionne
3. Accéder à Splunk et configurer les dashboards
4. Vérifier la collecte des logs, métriques et traces

**Livrables :**
- Cluster opérationnel
- Dashboards Splunk avec les "golden signals"

### Exercice 2 : Définition et Implémentation des SLIs/SLOs

**Objectif :** Identifier les SLIs pertinents et définir les SLOs.

**Étapes :**
1. Analyser les métriques disponibles
2. Identifier les SLIs critiques (latence, erreurs, trafic)
3. Définir les SLOs dans `sre/slo_config.json`
4. Documenter les SLIs et leur calcul

**Livrables :**
- Fichier de configuration des SLOs
- Documentation des SLIs

### Exercice 3 : Simulation d'Incident et Collaboration

**Objectif :** Déclencher un incident et identifier les "toils".

**Étapes :**
1. Déclencher un incident (vague 1) sans automatisation
2. Diagnostiquer et réparer manuellement
3. Rédiger un post-mortem collaboratif
4. Identifier les tâches manuelles répétitives (toil)
5. Implémenter des automatisations via `automation/toil_reduction.sh`
6. Déclencher une deuxième vague d'incident
7. Comparer les temps de résolution

**Livrables :**
- Post-mortem collaboratif
- Scripts d'automatisation
- Comparaison des performances

### Exercice 4 : Error Budget et Burn Rate

**Objectif :** Utiliser les SLOs pour calculer l'error budget et le burn rate.

**Étapes :**
1. Utiliser `sre/burn_rate_calc.py` pour calculer le burn rate
2. Configurer des alertes basées sur le burn rate
3. Analyser l'impact des incidents sur l'error budget
4. Implémenter des seuils d'alerte appropriés

**Livrables :**
- Script fonctionnel de calcul du burn rate
- Alertes Splunk configurées

### Exercice 5 : Automatisation pour Réduire le Toil

**Objectif :** Implémenter des automatisations pour réduire les tâches manuelles.

**Étapes :**
1. Analyser le post-mortem de l'Exercice 3
2. Identifier les tâches manuelles répétitives
3. Développer des scripts d'automatisation
4. Tester l'efficacité des automatisations
5. Mesurer la réduction du temps de résolution

**Livrables :**
- Scripts d'automatisation améliorés
- Métriques de réduction du toil

### Bonus : Mode Chaos

**Objectif :** Étendre les simulations d'incidents avec des pannes variées.

**Étapes :**
1. Étendre `incident/trigger_failure.sh` avec de nouveaux types de pannes
2. Implémenter des pannes de latence extrême
3. Ajouter des simulations de crash de pods
4. Créer des scénarios de perte réseau
5. Tester la robustesse des automatisations

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
./fix_failure.sh cleanup      # Nettoyage complet
```

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

## 📊 Monitoring et Alertes

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
SPLUNK_HEC_TOKEN=sre-lab-token

# Prometheus
PROMETHEUS_URL=http://localhost:9090

# Service
SERVICE_URL=http://localhost:30000
```

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

## 🤝 Contribution

1. Fork le projet
2. Créez une branche feature
3. Committez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👥 Auteurs

- **Fabio** - *Créateur du lab SRE*

## 🙏 Remerciements

- Équipe Google SRE pour l'inspiration
- Communauté OpenTelemetry
- Équipe KinD pour l'outil de développement

---

**Lab SRE - Version 1.0**  
**Dernière mise à jour :** 2024
