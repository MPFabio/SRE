# Runbook: Service Down

## Alerte
- **Nom**: `ServiceDown`
- **Sévérité**: critical
- **Condition**: `up == 0` pendant 1 minute

## Services et criticité

| Service | Criticité | Impact si down |
|---------|-----------|----------------|
| api-gateway | P1 | Site totalement inaccessible |
| payment-service | P1 | Impossible de payer |
| cart-service | P1 | Impossible d'ajouter au panier |
| orders-service | P1 | Impossible de commander |
| catalog-service | P2 | Produits non visibles |
| users-service | P2 | Login impossible |

## Diagnostic rapide

### 1. Identifier le service down
```bash
# Status de tous les services
docker compose ps

# Ou via Prometheus
curl --silent 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result[] | select(.value[1] == "0")'
```

### 2. Vérifier les logs
```bash
# Logs du service problématique
docker compose logs --tail 100 <service-name>
```

### 3. Vérifier les ressources
```bash
# Stats du conteneur
docker stats <container-name> --no-stream
```

## Causes possibles

| Cause | Symptômes | Résolution |
|-------|-----------|------------|
| OOMKilled | `Exited (137)` | Augmenter mémoire ou restart |
| Crash loop | Redémarrages répétés | Vérifier logs, fix bug |
| Dépendance down | Timeout au démarrage | Vérifier Redis, autres services |
| Port conflit | `Exited (1)` | Libérer le port |
| Config erreur | `Exited (1)` | Vérifier env vars |

## Résolution

### Redémarrage simple
```bash
docker compose restart <service-name>
```

### Si OOMKilled
```bash
# Vérifier les events
docker events --filter container=<container> --since 10m

# Restart avec plus de mémoire (temporaire)
docker compose up --detach <service-name>
```

### Si dépendance down
```bash
# Redémarrer dans l'ordre
docker compose restart redis
sleep 5
docker compose restart <service-name>
```

### Si crash loop
```bash
# Voir les logs au démarrage
docker compose logs --follow <service-name>

# Vérifier la configuration
docker compose config | grep -A20 <service-name>
```

## Vérification post-résolution

```bash
# Vérifier le status
docker compose ps <service-name>

# Vérifier le health
curl http://localhost:<port>/health

# Test global
make test
```

## Escalade

Si non résolu après 10 minutes (P1) ou 30 minutes (P2) :
1. Contacter l'équipe responsable
2. Envisager le failover si disponible
3. Communiquer le status

## Actions préventives

- [ ] Configurer des alertes de mémoire AVANT OOM
- [ ] Ajouter des health checks plus robustes
- [ ] Configurer des restart policies
- [ ] Documenter les dépendances

## Post-incident

- [ ] Créer le post-mortem
- [ ] Identifier la cause racine
- [ ] Définir les actions correctives
- [ ] Mettre à jour ce runbook si nécessaire
