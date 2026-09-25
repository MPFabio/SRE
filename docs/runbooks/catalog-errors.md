# Runbook: Catalog Service Errors

## Alerte
- **Nom**: `HighErrorRate`
- **Sévérité**: warning
- **Condition**: taux de 5xx > 1% pendant 2 minutes

`CriticalErrorRate` prend le relais au-dela de 5% pendant 1 minute.

## Impact
- Produits non affichés
- Pages partiellement chargées
- Expérience utilisateur dégradée
- Potentielle perte de conversion

## Diagnostic rapide

### 1. Vérifier les métriques
```promql
# Taux d'erreur actuel
sum(rate(catalog_requests_total{status=~"5.."}[5m])) 
/ sum(rate(catalog_requests_total[5m]))

# Répartition par code d'erreur
sum by (status) (rate(catalog_requests_total{status=~"[45].."}[5m]))

# Health du service
up{job="catalog-service"}
```

### 2. Vérifier les logs
```logql
# Erreurs 500 ou exceptions
{job="catalog-service"} |~ " 500 |(?i)(error|exception)"
```

### 3. Vérifier le health endpoint
```bash
curl --verbose http://localhost:8081/health
```

## Causes possibles

| Cause | Probabilité | Vérification |
|-------|-------------|--------------|
| Bug dans le code | Haute | Vérifier les logs |
| Données corrompues | Moyenne | Vérifier les requêtes spécifiques |
| Limite de ressources | Moyenne | Vérifier CPU/mémoire |
| Configuration chaos | Lab | Vérifier `make chaos-status` |

## Résolution

### Si chaos engineering actif
```bash
make chaos-stop
# ou
make chaos-stop
```

### Si erreur de code
1. Identifier l'endpoint en erreur via les logs
2. Vérifier le pattern des requêtes qui échouent
3. Rollback si déploiement récent

### Si limite de ressources
```bash
# Vérifier les ressources
docker stats catalog-service

# Redémarrer si nécessaire
docker compose restart catalog-service
```

### Si données corrompues
1. Identifier les produits problématiques
2. Vérifier la cohérence des données
3. Corriger ou exclure les données

## Vérification post-résolution

1. Vérifier que le taux d'erreur < 1%
2. Vérifier que tous les produits s'affichent
3. Tester la navigation sur la boutique

```bash
curl http://localhost:8080/api/products | jq 'length'
# Devrait retourner 15 produits
```

## Escalade

Si non résolu après 30 minutes :
1. Contacter l'équipe Catalog
2. Envisager d'activer un cache statique
3. Communiquer aux utilisateurs si nécessaire

## Post-incident

- [ ] Créer le post-mortem
- [ ] Analyser les patterns d'erreur
- [ ] Améliorer la validation des données
- [ ] Ajouter des tests si nécessaire
