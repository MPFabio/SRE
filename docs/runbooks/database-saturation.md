# Runbook: Database Saturation

## Alerte
- **Nom**: `DatabasePoolExhausted`
- **Sévérité**: critical (priorité P1)
- **Condition**: `db_pool_size > 0 and db_pool_idle == 0` pendant 3 minutes

## Impact
- Latence en hausse sur catalog, orders et users
- Erreurs 500 quand le pool ne rend plus de connexion
- Le parcours d'achat échoue à l'étape commande
- La boutique reste affichée, le panier étant sur Redis : la panne est
  partielle

## Contexte

Dimensionnement de l'application fil rouge :

| Paramètre | Valeur | Où |
|---|---|---|
| `DB_POOL_MAX` | 10 | `db.poolMax` du chart / `_shared/db.py` |
| `max_connections` | 50 | `postgres.maxConnections` du chart |
| `command_timeout` | 5s | `_shared/db.py` |

Trois services persistants × 10 connexions = 30 connexions en pointe,
sur 50 disponibles.

## Diagnostic rapide

### 1. Métriques du pool
```promql
# Connexions ouvertes et inactives, par service
db_pool_size
db_pool_idle

# Un pool saturé : size au maximum, idle à zéro
db_pool_size - db_pool_idle

# Latence des requêtes par opération
histogram_quantile(0.99, sum by (le, operation) (rate(db_query_duration_seconds_bucket[5m])))

# Erreurs de requête
rate(db_query_errors_total[5m])
```

### 2. Côté serveur PostgreSQL
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
kubectl exec deploy/catalog-service -- curl --silent localhost:8081/ready
kubectl exec deploy/orders-service -- curl --silent localhost:8083/ready
kubectl exec deploy/users-service -- curl --silent localhost:8085/ready
```

### 4. Inspecter la base
```bash
kubectl exec -it statefulset/postgres -- psql --username=capshop --dbname=capshop
```

```sql
-- Qui occupe les connexions
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- Requêtes longues en cours
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

## Causes fréquentes

| Cause | Signature | Vérification |
|---|---|---|
| Pic de trafic | `db_pool_size` au max sur les 3 services | Locust a monté en charge |
| Requête lente qui retient une connexion | Une `operation` domine la latence P99 | `pg_stat_activity` |
| Chaos injecté | Latence ajoutée sur les handlers | Incident en cours dans l'Operations Console |
| Verrou non relâché | `pg_locks` avec `granted = false` | Requête verrous ci-dessus |

## Résolution

### Si le chaos est actif
L'injection s'arrête quand l'incident est résolu dans l'Operations Console
(*Mark Resolved*). Pour vérifier l'état du chaos sur chaque service :

```bash
for svc in catalog-service:8081 cart-service:8082 orders-service:8083 payment-service:8084 users-service:8085; do
  echo "${svc%%:*} : $(kubectl exec deploy/${svc%%:*} -- curl --silent localhost:${svc##*:}/api/chaos)"
done
```

### Si une requête est bloquée
```sql
-- Identifier puis terminer la session fautive
SELECT pg_terminate_backend(<pid>);
```

### Si la charge est légitime
```bash
# Augmenter temporairement le pool : les services redémarrent
helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values --set db.poolMax=20
```

En production, la bonne réponse est rarement d'agrandir le pool : c'est
un symptôme. Chercher d'abord la requête lente ou la connexion non
rendue.

## Vérification du retour à la normale

```bash
kubectl get pods                   # tous les pods Running et prêts
kubectl exec deploy/catalog-service -- curl --silent localhost:8081/ready   # "database":"up"
```

Puis effectuer un achat complet dans la boutique (http://localhost:8080).

```promql
# Le pool doit se vider
db_pool_idle > 0
```

## Prévention

- Surveiller `db_pool_size` / `db_pool_idle` en continu, pas seulement
  la latence applicative : la saturation du pool précède la dégradation
  visible
- Alerter sur `db_query_errors_total` plutôt que sur les seules 500 du
  gateway : la cause est plus proche
- Garder `command_timeout` court : une requête qui traîne doit échouer
  vite plutôt que retenir une connexion

## Voir aussi

- [Payment Latency](payment-latency.md)
- [Catalog Errors](catalog-errors.md)
- [Service Down](service-down.md)
