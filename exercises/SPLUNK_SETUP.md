# Exercice 1 : Configuration Splunk pour l'Observabilité

Ce guide explique comment configurer Splunk pour recevoir les métriques du lab SRE. C'est le **premier exercice** du lab SRE.

## Objectif

Configurer Splunk pour recevoir et analyser les métriques, logs et traces du lab SRE.

## Prérequis

- Le lab SRE doit être démarré (voir README.md)
- Splunk doit être accessible sur http://localhost:8000
- OpenTelemetry Collector doit être en cours d'exécution

## Démarrage

1. **Accédez à Splunk** : http://localhost:8000
2. **Connectez-vous** : admin / admin123
3. **Suivez les étapes ci-dessous**

## Configuration du HTTP Event Collector (HEC)

### Étape 1 : Activer le HEC globalement

1. **Allez dans** : Settings > Data Inputs > HTTP Event Collector
2. **Cliquez sur** : "Global Settings" (en haut à droite)
3. **Décochez** : "Enable SSL" ☐
4. **Vérifiez** : "HTTP Port Number" = 8088
5. **Cliquez sur** : "Save"

### Étape 2 : Créer un token HEC

1. **Allez dans** : Settings > Data Inputs > HTTP Event Collector
2. **Cliquez sur** : "New Token" ou "Créer un nouveau jeton"
3. **Remplissez** :
   - **Nom** : `sre-lab-token`
   - **Remplace le nom de la source** : `otel-collector`
   - **Description** : `OpenTelemetry Collector metrics`
   - **Output Group** : `Aucun(e)`
   - **Activer l'accusé de réception** : ☐ (décoché)
4. **Cliquez sur** : "Suivant"

### Étape 3 : Configurer les paramètres d'entrée

1. **Sourcetype** : `Automatique`
2. **Index** : Cliquez sur **"ajouter tous >>"** pour sélectionner tous les index
3. **Index par défaut** : `Défaut`
4. **Cliquez sur** : "Suivant" ou "Créer"

### Étape 4 : Copier le token

1. **Copiez le token généré** (ex: `3aaffac1-df6b-456b-897a-8b0628a9b4cc`)
2. **Sauvegardez-le** - vous en aurez besoin !

## Mise à jour de la configuration OpenTelemetry

Une fois le token créé, mettez à jour le fichier `otel-collector-config.yml` :

```yaml
splunk_hec:
  endpoint: "http://splunk:8088/services/collector"
  token: "VOTRE_TOKEN_ICI"
  source: "otel-collector"
  sourcetype: "otel"
  index: "main"
```

Puis redémarrez l'OpenTelemetry Collector :

```bash
docker-compose restart otel-collector
```

## Vérification

### Dans Splunk, recherchez :
```
index=main source="otel-collector"
```

### Vous devriez voir :
- Des événements avec `source="otel-collector"`
- Des métriques OpenTelemetry
- Des données de l'URL Shortener

## Dépannage

### Problème : "Connection reset by peer"
- **Solution** : Vérifiez que SSL est désactivé dans Splunk

### Problème : "EOF" dans les logs OpenTelemetry
- **Solution** : Vérifiez que le token est correct dans `otel-collector-config.yml`

### Problème : Pas de données dans Splunk
- **Solution** : Vérifiez que le HEC est activé globalement

## Recherches utiles dans Splunk

- `index=main source="otel-collector"` - Métriques OpenTelemetry
- `index=main sourcetype="otel"` - Données structurées
- `index=main` - Toutes les données

## Prochaines étapes

Une fois Splunk configuré, vous pouvez :
1. **Commencer les exercices** dans `exercises/README.md`
2. **Analyser les métriques** dans Splunk
3. **Tester l'URL Shortener** et observer les métriques
4. **Simuler des incidents** et pratiquer le SRE
