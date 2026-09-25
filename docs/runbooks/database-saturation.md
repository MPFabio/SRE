# Runbook: Database Saturation

## Alerte
- **Nom**: `DatabasePoolExhausted`
- **Sévérité**: critical (priorite P1)
- **Condition**: `db_pool_size > 0 and db_pool_idle == 0` pendant 3 minutes

## Impact
- Latence en hausse sur catalog, orders et users
- Erreurs 500 quand le pool ne rend plus de connexion
- Le parcours d'achat echoue a l'etape commande
- La boutique reste affichee, le panier etant sur Redis : la panne est
  partielle

## Contexte

Dimensionnement du lab :

| Parametre | Valeur | Ou |
|---|---|---|
| `DB_POOL_MAX` | 10 | `.env` / `_shared/db.py` |
| `max_connections` | 50 | `docker-compose.yml` (commande postgres) |
| `command_timeout` | 5s | `_shared/db.py` |

Trois services persistants x 10 connexions = 30 connexions en pointe,
sur 50 disponibles.

## Diagnostic rapide

### 1. Metriques du pool
```promql
# Connexions ouvertes et inactives, par service
db_pool_size
db_pool_idle

# Un pool sature: size au maximum, idle a zero
db_pool_size - db_pool_idle

# Latence des requetes par operation
histogram_quantile(0.99, sum by (le, operation) (rate(db_query_duration_seconds_bucket[5m])))

# Erreurs de requete
rate(db_query_errors_total[5m])
```

### 2. Cote serveur PostgreSQL
```promql
# Connexions actives vs maximum
pg_stat_database_numbackends
pg_settings_max_connections

# Taux d'occupation
sum(pg_stat_database_numbackends) / scalar(max(pg_settings_max_connections))
```

### 3. Readiness des services
```bash
# Un service qui ne joint plus la base renvoie 503
curl http://localhost:8081/ready
curl http://localhost:8083/ready
curl http://localhost:8085/ready
```

### 4. Inspecter la base
```bash
make psql
```

```sql
-- Qui occupe les connexions
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- Requetes longues en cours
SELECT pid, now() - query_start AS duree, state, left(query, 60)
FROM pg_stat_activity
WHERE state <> 'idle' AND query_start < now() - interval '1 second'
ORDER BY duree DESC;

-- Verrous en attente
SELECT count(*) FROM pg_locks WHERE NOT granted;
```

### 5. Logs
```logql
{job=~"catalog-service|orders-service|users-service"} |~ "(?i)(pool|timeout|connection)"
{job="postgres"} |~ "(?i)(too many|connection)"
```

## Causes frequentes

| Cause | Signature | Verification |
|---|---|---|
| Pic de trafic | `db_pool_size` au max sur les 3 services | Locust a monte en charge |
| Requete lente qui retient une connexion | Une `operation` domine la latence P99 | `pg_stat_activity` |
| Chaos injecte | Latence ajoutee sur les handlers | `make chaos-status` |
| Verrou non relache | `pg_locks` avec `granted = false` | Requete verrous ci-dessus |

## Resolution

### Si le chaos est actif
```bash
make chaos-status
make chaos-stop
```

### Si une requete est bloquee
```sql
-- Identifier puis terminer la session fautive
SELECT pg_terminate_backend(<pid>);
```

### Si la charge est legitime
```bash
# Augmenter temporairement le pool (necessite un redemarrage)
# Dans .env :
DB_POOL_MAX=20

docker compose up --detach catalog-service orders-service users-service
```

En production, la bonne reponse est rarement d'agrandir le pool : c'est
un symptome. Chercher d'abord la requete lente ou la connexion non
rendue.

## Verification du retour a la normale

```bash
make test                          # 13 composants repondent
curl http://localhost:8081/ready   # "database":"up"
make test-purchase                 # parcours d'achat complet
```

```promql
# Le pool doit se vider
db_pool_idle > 0
```

## Prevention

- Surveiller `db_pool_size` / `db_pool_idle` en continu, pas seulement
  la latence applicative : la saturation du pool precede la degradation
  visible
- Alerter sur `db_query_errors_total` plutot que sur les seules 500 du
  gateway : la cause est plus proche
- Garder `command_timeout` court : une requete qui traine doit echouer
  vite plutot que retenir une connexion

## Voir aussi

- [Payment Latency](payment-latency.md)
- [Catalog Errors](catalog-errors.md)
- [Service Down](service-down.md)
