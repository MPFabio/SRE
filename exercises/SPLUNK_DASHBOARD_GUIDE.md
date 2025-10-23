# Guide : Création d'un Dashboard Splunk - 4 Golden Signals

Ce guide vous accompagne dans la création d'un dashboard Splunk pour monitorer les 4 Golden Signals du service URL Shortener.

## Objectif

Créer un dashboard Splunk avec les 4 Golden Signals :
- **LATENCY** : Temps de réponse
- **TRAFFIC** : Volume de requêtes
- **ERRORS** : Taux d'erreur
- **SATURATION** : Utilisation des ressources

## Étape 1 : Accéder à Splunk

1. **Ouvrir Splunk** : http://localhost:8000
2. **Se connecter** : admin / admin123
3. **Aller dans "Search & Reporting"** (sidebar gauche)
4. **Cliquer sur "Dashboards"**

## Étape 2 : Créer le Dashboard

1. **Cliquer sur "Create Dashboard"** (bouton vert)
2. **Choisir "Dashboard Studio"**
3. **Mise en page** : **"Grille"** (recommandé)
4. **Nommer** : `SRE Golden Signals - URL Shortener`
5. **Description** : `Dashboard des 4 Golden Signals pour le service URL Shortener`
6. **Cliquer sur "Save"**

## Étape 3 : Ajouter les 4 Panels

### Panel 1 : LATENCY

1. **Nouvelle recherche** dans "Search & Reporting"
2. **Requête SPL** :
```spl
index=main source="url-shortener"
| stats avg(response_time) as avg_latency
| eval avg_latency=round(avg_latency, 2)
```
3. **Cliquer sur "Save As"** → **"Existing Dashboard"**
4. **Configuration** :
   - **Dashboard** : "SRE Golden Signals - URL Shortener"
   - **Dashboard tab** : "SRE"
   - **Panel Title** : "LATENCY"
   - **Visualization Type** : "Single Value"
5. **Cliquer sur "Save to Dashboard"**

### Panel 2 : TRAFFIC

1. **Nouvelle recherche**
2. **Requête SPL** :
```spl
index=main source="url-shortener"
| timechart span=1m count as requests_per_minute
```
3. **Cliquer sur "Save As"** → **"Existing Dashboard"**
4. **Configuration** :
   - **Dashboard** : "SRE Golden Signals - URL Shortener"
   - **Dashboard tab** : "SRE"
   - **Panel Title** : "TRAFFIC"
   - **Visualization Type** : "Line Chart"
5. **Cliquer sur "Save to Dashboard"**

### Panel 3 : ERRORS

1. **Nouvelle recherche**
2. **Requête SPL** :
```spl
index=main source="url-shortener"
| stats count as total, count(eval(status_code>=400)) as errors
| eval error_rate=round((errors/total)*100, 2)
```
3. **Cliquer sur "Save As"** → **"Existing Dashboard"**
4. **Configuration** :
   - **Dashboard** : "SRE Golden Signals - URL Shortener"
   - **Dashboard tab** : "SRE"
   - **Panel Title** : "ERRORS"
   - **Visualization Type** : "Single Value"
5. **Cliquer sur "Save to Dashboard"**

### Panel 4 : SATURATION

1. **Nouvelle recherche**
2. **Requête SPL** :
```spl
index=main source="url-shortener"
| stats avg(cpu_usage) as avg_cpu, avg(memory_usage) as avg_memory
| eval avg_cpu=round(avg_cpu, 2)
| eval avg_memory=round(avg_memory, 2)
```
3. **Cliquer sur "Save As"** → **"Existing Dashboard"**
4. **Configuration** :
   - **Dashboard** : "SRE Golden Signals - URL Shortener"
   - **Dashboard tab** : "SRE"
   - **Panel Title** : "SATURATION"
   - **Visualization Type** : "Bar Chart"
5. **Cliquer sur "Save to Dashboard"**

## Étape 4 : Générer des données de test

Pour que les panels affichent des données :

1. **Aller sur l'URL Shortener** : http://localhost:30000
2. **Créer quelques URLs courtes** (ex: raccourcir 5-10 URLs)
3. **Attendre 1-2 minutes** que les données arrivent dans Splunk
4. **Revenir au dashboard** pour voir les métriques

## Étape 5 : Vérifier les données

1. **Dans Splunk, faire une recherche** :
```spl
index=main source="url-shortener"
```
2. **Si vous voyez des données**, les panels du dashboard se rempliront automatiquement
3. **Si pas de données**, vérifier que :
   - L'URL Shortener fonctionne
   - OpenTelemetry Collector est actif
   - Splunk HEC est configuré

## Résultat attendu

Votre dashboard devrait afficher :
- **LATENCY** : Temps de réponse moyen en ms
- **TRAFFIC** : Graphique des requêtes par minute
- **ERRORS** : Taux d'erreur en pourcentage
- **SATURATION** : Graphique CPU/Memory

## Configuration des alertes (Optionnel)

Pour chaque panel, vous pouvez configurer des alertes :
- **LATENCY** : > 200ms
- **ERRORS** : > 1%
- **CPU** : > 80%
- **Memory** : > 80%

## Validation

Votre dashboard est prêt quand :
- ✅ Les 4 panels sont visibles
- ✅ Les données s'affichent (pas "No search results")
- ✅ Les métriques se mettent à jour en temps réel
- ✅ Le layout 2x2 est propre et lisible

## Prochaines étapes

Une fois le dashboard créé :
1. **Configurer des alertes** basées sur les SLOs
2. **Créer des rapports** automatisés
3. **Intégrer avec d'autres outils** de monitoring
4. **Définir des seuils** d'alerte appropriés

---

**Conseil** : Ce dashboard sera votre point de référence pour tous les exercices SRE suivants !
