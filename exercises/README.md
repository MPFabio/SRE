# Exercices du Lab SRE

Ce dossier contient les exercices détaillés pour le Lab SRE. Chaque exercice est conçu pour vous faire progresser dans l'apprentissage des pratiques SRE.

## Liste des Exercices

### Exercice 1 : Déploiement et Observabilité
**Durée estimée :** 1-2 heures  
**Difficulté :** ** (2/5)

**Objectif :** Déployer l'environnement et vérifier la visibilité des données.

**Étapes :**
1. Démarrer le lab avec `./scripts/start_lab.sh`
2. Vérifier que tous les services sont accessibles
3. Configurer Splunk pour recevoir les métriques
4. Accéder à Splunk et explorer les données
5. Configurer des dashboards de base

**Configuration Splunk (OBLIGATOIRE) :**

**Étape 3.1 : Activer le HEC globalement**
1. Accédez à Splunk : http://localhost:8000
2. Connectez-vous : admin / admin123
3. Allez dans Settings > Data Inputs > HTTP Event Collector
4. Cliquez sur "Global Settings" (en haut à droite)
5. Décochez "Enable SSL" ☐
6. Vérifiez que "HTTP Port Number" = 8088
7. Cliquez sur "Save"

**Étape 3.2 : Créer un token HEC**
1. Allez dans Settings > Data Inputs > HTTP Event Collector
2. Cliquez sur "New Token" ou "Créer un nouveau jeton"
3. Remplissez :
   - **Nom** : `sre-lab-token`
   - **Remplace le nom de la source** : `otel-collector`
   - **Description** : `OpenTelemetry Collector metrics`
   - **Output Group** : `Aucun(e)`
   - **Activer l'accusé de réception** : ☐ (décoché)
4. Cliquez sur "Suivant"

**Étape 3.3 : Configurer les paramètres d'entrée**
1. **Sourcetype** : `Automatique`
2. **Index** : Cliquez sur **"ajouter tous >>"** pour sélectionner tous les index
3. **Index par défaut** : Sélectionnez **"main"** dans le dropdown
4. Cliquez sur "Suivant" ou "Créer"

**Étape 3.4 : Mettre à jour la configuration OpenTelemetry**
1. Copiez le token généré
2. Mettez à jour le fichier `otel-collector-config.yml` :
   ```yaml
   splunk_hec:
     endpoint: "http://splunk:8088/services/collector"
     token: "VOTRE_TOKEN_ICI"
     source: "otel-collector"
     sourcetype: "otel"
     index: "main"
   ```
3. Redémarrez l'OpenTelemetry Collector :
   ```bash
   docker-compose restart otel-collector
   ```

**Étape 3.5 : Vérifier que les métriques arrivent**
Dans Splunk, recherchez :
```
index=main source="otel-collector"
```
Vous devriez voir des événements avec `source="otel-collector"`.

**Étape 3.6 : Créer le Dashboard des 4 Golden Signals**
> **[Guide Complet]** [SPLUNK_DASHBOARD_GUIDE.md](SPLUNK_DASHBOARD_GUIDE.md) - Création d'un dashboard Splunk avec les 4 Golden Signals

**Livrables :**
- Cluster opérationnel
- Dashboard Splunk avec les 4 Golden Signals (LATENCY, TRAFFIC, ERRORS, SATURATION)

**Commandes utiles :**
```bash
# Démarrer le lab
./scripts/start_lab.sh

# Vérifier le statut
./scripts/validate_lab.sh

# Tester le lab
python3 scripts/test_lab.py
```

### Exercice 2 : Définition et Implémentation des SLIs/SLOs
**Durée estimée :** 2-3 heures  
**Difficulté :** ** (2/5)

**Objectif :** Identifier les SLIs pertinents et définir les SLOs.

**Étapes :**
1. Analyser les métriques disponibles dans Splunk
2. Identifier les SLIs critiques (latence, erreurs, trafic)
3. Définir les SLOs dans `sre/slo_config.json`
4. Documenter les SLIs et leur calcul
5. Configurer des alertes basées sur les SLOs

**Livrables :**
- Fichier de configuration des SLOs
- Documentation des SLIs
- Alertes configurées

**Commandes utiles :**
```bash
# Analyser les métriques
curl http://localhost:30000/metrics

# Calculer le burn rate
cd sre && python3 burn_rate_calc.py

# Surveiller l'error budget
python3 error_budget_tracker.py --dashboard
```

### Exercice 3 : Error Budget et Burn Rate
**Durée estimée :** 2-3 heures  
**Difficulté :** ** (2/5)

**Objectif :** Utiliser les SLOs pour calculer l'error budget et le burn rate.

**Étapes :**
1. Utiliser `sre/burn_rate_calc.py` pour calculer le burn rate
2. Analyser l'impact des incidents sur l'error budget
3. Configurer des alertes basées sur le burn rate
4. Implémenter des seuils d'alerte appropriés
5. Tester les alertes avec des incidents simulés

**Livrables :**
- Script fonctionnel de calcul du burn rate
- Alertes Splunk configurées
- Documentation des seuils

**Commandes utiles :**
```bash
# Déclencher un incident
cd incident && ./trigger_failure.sh

# Réparer un incident
./fix_failure.sh

# Automatisation
cd automation && ./toil_reduction.sh
```

### Exercice 4 : Simulation d'Incident et Collaboration
**Durée estimée :** 3-4 heures  
**Difficulté :** **** (4/5)

**Objectif :** Déclencher un incident et identifier les "toils".

**Étapes :**
1. **Vague 1 - Sans automatisation :**
   - Déclencher un incident avec `./incident/trigger_failure.sh`
   - Diagnostiquer et réparer manuellement
   - Mesurer le temps de résolution
   - Rédiger un post-mortem avec le template

2. **Identification du toil :**
   - Analyser le post-mortem
   - Identifier les tâches manuelles répétitives
   - Prioriser les automatisations

3. **Vague 2 - Avec automatisation :**
   - Implémenter des automatisations via `automation/toil_reduction.sh`
   - Déclencher le même type d'incident
   - Comparer les temps de résolution

**Livrables :**
- Post-mortem collaboratif
- Scripts d'automatisation
- Comparaison des performances

**Commandes utiles :**
```bash
# Calculer le burn rate
cd sre && python3 burn_rate_calc.py --hours 24

# Surveiller l'error budget
python3 error_budget_tracker.py --monitor

# Générer des données de test
cd ingest && python3 ingest_to_splunk.py
```

### Exercice 5 : Automatisation pour Réduire le Toil
**Durée estimée :** 3-4 heures  
**Difficulté :** **** (4/5)

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
- Documentation des automatisations

**Commandes utiles :**
```bash
# Surveillance continue
cd automation && ./toil_reduction.sh continuous

# Auto-scaling
./toil_reduction.sh scale

# Nettoyage automatique
./toil_reduction.sh cleanup
```

### Bonus : Mode Chaos
**Durée estimée :** 1-2 heures  
**Difficulté :** *** (3/5)

**Objectif :** Étendre les simulations d'incidents avec des pannes variées.

**Étapes :**
1. Étendre `incident/trigger_failure.sh` avec de nouveaux types de pannes
2. Implémenter des pannes de latence extrême
3. Ajouter des simulations de crash de pods
4. Créer des scénarios de perte réseau
5. Tester la robustesse des automatisations

**Livrables :**
- Scripts de chaos étendus
- Tests de robustesse
- Documentation des scénarios

## Objectifs d'Apprentissage

À la fin de ces exercices, vous devriez être capable de :

1. **Déployer un environnement SRE complet**
   - Utiliser KinD pour un cluster Kubernetes local
   - Configurer l'observabilité avec Splunk et OpenTelemetry

2. **Définir et implémenter des SLOs**
   - Identifier les SLIs pertinents
   - Calculer l'error budget et le burn rate
   - Configurer des alertes appropriées

3. **Gérer des incidents**
   - Diagnostiquer des pannes
   - Réparer des services
   - Rédiger des post-mortems

4. **Réduire le toil**
   - Identifier les tâches manuelles répétitives
   - Développer des automatisations
   - Mesurer l'efficacité

5. **Surveiller et alerter**
   - Configurer des dashboards
   - Implémenter des alertes
   - Analyser les métriques

## Ressources Supplémentaires

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [SRE Workbook](https://sre.google/workbook/table-of-contents/)
- [SLO Engineering](https://sre.google/sre-book/sli-slo/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Splunk Documentation](https://docs.splunk.com/)

## Aide et Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs : `./start_lab.sh status`
2. Testez le lab : `python3 test_lab.py`
3. Consultez le README principal
4. Vérifiez les prérequis

## Notes

- Chaque exercice peut être fait indépendamment
- Les exercices sont progressifs (difficulté croissante)
- N'hésitez pas à expérimenter et personnaliser
- Documentez vos découvertes et améliorations
