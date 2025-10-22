# Démarrage Rapide - Lab SRE

## Installation et Démarrage

### 1. Prérequis
- Docker et Docker Compose
- KinD (Kubernetes in Docker)
- kubectl
- Python 3.8+

### 2. Démarrage du Lab
```bash
# Démarrer tous les composants
./start_lab.sh

# Vérifier le statut
./start_lab.sh status

# Tester le lab
python3 test_lab.py
```

### 3. Accès aux Services
- **URL Shortener:** http://localhost:30000
- **Splunk:** http://localhost:8000 (admin/admin123)
- **OpenTelemetry:** http://localhost:8889/metrics

## Exercices Rapides

### Exercice 1: Vérification de Base
```bash
# Tester le service
curl http://localhost:30000/health

# Créer une URL courte
curl -X POST "http://localhost:30000/shorten?url=https://www.google.com"

# Voir les métriques
curl http://localhost:30000/metrics
```

### Exercice 2: Simulation d'Incident
```bash
# Déclencher un incident
cd incident
./trigger_failure.sh

# Réparer l'incident
./fix_failure.sh
```

### Exercice 3: Calcul du Burn Rate
```bash
cd sre
python3 burn_rate_calc.py --hours 24
```

### Exercice 4: Automatisation
```bash
cd automation
./toil_reduction.sh continuous
```

## Commandes Utiles

### Gestion du Lab
```bash
./start_lab.sh start    # Démarrer
./start_lab.sh stop     # Arrêter
./start_lab.sh restart  # Redémarrer
./start_lab.sh status   # Statut
```

### Génération de Données
```bash
# Générer du trafic
cd simulator
python3 traffic_generator.py --duration 30 --rpm 50

# Ingérer des données
cd ingest
python3 ingest_to_splunk.py --logs 1000 --metrics 500
```

### Surveillance
```bash
# Voir les pods
kubectl get pods

# Voir les services
kubectl get services

# Voir les logs
kubectl logs -l app=url-shortener -f
```

## Dépannage

### Problèmes Courants
1. **Service inaccessible:** Vérifiez `kubectl get pods`
2. **Splunk non accessible:** Vérifiez `docker-compose ps`
3. **Métriques manquantes:** Vérifiez les logs OpenTelemetry

### Logs Utiles
```bash
# Logs du service
kubectl logs -l app=url-shortener

# Logs Splunk
docker-compose logs splunk

# Logs OpenTelemetry
kubectl logs -l app=otel-collector
```

## Structure du Projet

```
SRE/
├── start_lab.sh              # Script de démarrage
├── test_lab.py               # Tests du lab
├── docker-compose.yml        # Splunk
├── kind/                     # Configuration KinD
├── simulator/                # Générateur de trafic
├── ingest/                   # Ingestion de données
├── incident/                 # Simulation d'incidents
├── automation/               # Scripts d'automatisation
├── sre/                      # Scripts SRE (SLOs, burn rate)
└── exercises/                # Exercices détaillés
```

## Support

- **Documentation complète:** README.md
- **Exercices détaillés:** exercises/README.md
- **Configuration:** config.json
- **Validation:** python3 validate_setup_simple.py

---

**Lab SRE - Version 1.0**  
**Prêt pour l'apprentissage des pratiques SRE !**
