# Guide Observabilité - Reskilling Lab

Ce guide détaille l'utilisation des outils d'observabilité du lab.

## Vue d'ensemble

Le lab utilise la stack **Grafana** pour l'observabilité :

| Outil | Port | Rôle |
|-------|------|------|
| **Prometheus** | 9090 | Collecte et stockage des métriques |
| **Loki** | 3100 | Agrégation des logs |
| **Tempo** | 3200 | Traces distribuées |
| **Grafana** | 3000 | Visualisation unifiée |
| **Alertmanager** | 9093 | Gestion des alertes |
| **Blackbox Exporter** | 9115 | Probes externes (HTTP, TCP) |

## 1. Prometheus - Métriques

### Accès

- Direct : http://localhost:9090
- Via Grafana : Explore → Prometheus

### Métriques disponibles

#### Métriques HTTP (chaque service expose ses propres métriques préfixées)

```promql
# Requêtes par seconde par service, vues depuis l'API Gateway
sum by (service) (rate(gateway_requests_total[5m]))

# Requêtes totales d'un service donné (exemple : catalog)
catalog_requests_total{status="200"}

# Latence (histogramme), exemple sur le service payment
payment_request_duration_seconds_bucket
payment_request_duration_seconds_sum
payment_request_duration_seconds_count
```

Chaque service possède son propre préfixe : `gateway_*`, `catalog_*`, `cart_*`, `orders_*`, `payment_*`, `users_*`. Il n'existe pas de métrique générique `http_requests_total`.

#### Métriques métier

```promql
# Commandes créées
orders_created_total

# Paiements traités
payments_processed_total

# Produits servis par le catalog
catalog_products_served_total

# Opérations sur le panier
cart_operations_total
```

#### Métriques base de données

Exposées par les services persistants (catalog, orders, users) via le
pool partagé `_shared/db.py` :

```promql
# Connexions ouvertes et inactives dans le pool
db_pool_size
db_pool_idle

# Connexions reellement occupees
db_pool_size - db_pool_idle

# Latence des requetes, par operation
histogram_quantile(0.99, sum by (le, operation) (rate(db_query_duration_seconds_bucket[5m])))

# Erreurs de requete
rate(db_query_errors_total[5m])
```

Côté serveur, `postgres-exporter` expose environ 340 métriques `pg_*` :

```promql
# Base joignable
pg_up

# Connexions actives vs maximum
pg_stat_database_numbackends
pg_settings_max_connections

# Taille des bases
pg_database_size_bytes
```

Le scénario **Database Saturation** s'appuie sur ce dimensionnement :
`DB_POOL_MAX=10` par service, `max_connections=50` côté serveur.
Voir [le runbook](runbooks/database-saturation.md).

#### Métriques Circuit Breaker (Payment Service)

```promql
# État du circuit breaker (0=closed, 1=open, 2=half-open)
circuit_breaker_state

# Latence du provider de paiement externe (histogramme)
histogram_quantile(0.99, rate(external_payment_provider_latency_seconds_bucket[5m]))

# Erreurs du provider externe
rate(external_payment_provider_errors_total[5m])
```

### Requêtes PromQL utiles

```promql
# Taux d'erreur global (%) vu depuis l'API Gateway
100 * sum(rate(gateway_requests_total{status=~"5.."}[5m])) 
    / sum(rate(gateway_requests_total[5m]))

# Latence P50, P90, P99 (exemple : service payment)
histogram_quantile(0.50, sum by (le) (rate(payment_request_duration_seconds_bucket[5m])))
histogram_quantile(0.90, sum by (le) (rate(payment_request_duration_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[5m])))

# Requêtes par service
sum by (service) (rate(gateway_requests_total[5m]))

# Services avec le plus d'erreurs
topk(5, sum by (service) (rate(gateway_requests_total{status=~"5.."}[5m])))
```

### Règles d'alertes

Les alertes sont définies dans `observability/prometheus/rules/sre_rules.yml` :

- `HighErrorRate` : Taux d'erreur > 5%
- `HighLatency` : P99 > 1s
- `ServiceDown` : Service ne répond plus
- `CircuitBreakerOpen` : Circuit breaker ouvert

## 2. Loki - Logs

### Accès

Via Grafana uniquement : Explore → Loki

### Syntaxe LogQL

#### Sélection par labels

```logql
# Tous les logs d'un service
{job="payment-service"}

# Plusieurs services
{job=~"payment-service|orders-service"}

# Par service (label "service" alimenté par Promtail via Docker labels)
{service="api-gateway"}
```

#### Filtrage par contenu

```logql
# Contient "error" (insensible à la casse)
{job="payment-service"} |~ "(?i)error"

# Ne contient pas "health" (exclut les health checks)
{job="api-gateway"} != "/health"

# Expression régulière (codes 4xx/5xx dans les access logs uvicorn)
{job="catalog-service"} |~ " [45][0-9]{2} "
```

#### Format des logs

Les logs sont des access logs uvicorn en texte brut (pas de JSON), par exemple :
```
INFO:     172.23.0.15:36068 - "GET /api/products HTTP/1.1" 200 OK
```

```logql
# Filtrer sur un code de statut précis
{job="api-gateway"} |~ " 500 "

# Requêtes lentes ou en timeout (mots-clés applicatifs)
{job="api-gateway"} |~ "(?i)(slow|timeout|error)"
```

#### Agrégations

```logql
# Nombre de logs par minute
count_over_time({job="payment-service"}[1m])

# Logs d'erreur par service
sum by (job) (count_over_time({job=~".+"} |~ " [45][0-9]{2} " [5m]))
```

### Requêtes utiles

```logql
# Erreurs (4xx/5xx) sur l'API Gateway
{job="api-gateway"} |~ " [45][0-9]{2} "

# Paiements échoués
{job="payment-service"} |~ "(?i)(failed|error)"

# Logs d'erreur tous services confondus
{job=~".+"} |~ "(?i)error"
```

## 3. Tempo - Traces

### Accès

Via Grafana : Explore → Tempo

### Recherche de traces

#### Par TraceID

Si vous avez un TraceID (depuis les logs ou une erreur), collez-le directement dans Tempo.

#### Par critères

- **Service** : Filtrer par nom de service
- **Durée** : Traces > X ms
- **Status** : Erreurs uniquement
- **Tags** : http.method, http.status_code, etc.

### Anatomie d'une trace

Une trace représente une requête de bout en bout :

```
[api-gateway] ─── 150ms ───┐
                           │
    [catalog-service] ─ 45ms
    [cart-service] ─── 30ms ───┐
                               │
        [redis] ─ 5ms
    [orders-service] ── 60ms ──┐
                               │
        [payment-service] ─ 40ms
```

Chaque **span** contient :
- Nom de l'opération
- Service
- Durée
- Tags (HTTP method, status, etc.)
- Logs/événements

### Corrélation logs ↔ traces

1. Dans Loki, trouvez un log intéressant
2. Si le log contient un `trace_id`, cliquez dessus
3. Grafana ouvre automatiquement Tempo avec cette trace

### Corrélation traces ↔ métriques

1. Dans Tempo, identifiez un service problématique
2. Cliquez sur "Metrics" pour voir les métriques associées
3. Analysez la corrélation latence/erreurs

## 4. Grafana - Dashboards

### Connexion

- URL : http://localhost:3000
- Login : admin / admin

### Dashboard "SRE Overview"

Le dashboard principal contient :

1. **Golden Signals**
   - Latence (P50, P90, P99)
   - Traffic (req/s)
   - Erreurs (%)
   - Saturation (CPU, mémoire)

2. **Service Health**
   - Status par service
   - Requêtes par seconde
   - Taux d'erreur

3. **Alertes actives**

### Créer un nouveau dashboard

1. **+** → **Dashboard** → **Add visualization**
2. Sélectionner la datasource (Prometheus, Loki, Tempo)
3. Écrire la requête
4. Configurer la visualisation
5. Sauvegarder

### Exemple : Panel de latence

```yaml
Type: Time series
Datasource: Prometheus
Query: histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[5m])))
Legend: P99 Latency
Unit: seconds
Thresholds: 0.5 (yellow), 1 (red)
```

## 5. Alertmanager

### Accès

http://localhost:9093

### Alertes configurées

| Alerte | Condition | Sévérité |
|--------|-----------|----------|
| HighErrorRate | Erreurs > 5% pendant 5min | warning |
| HighLatency | P99 > 1s pendant 5min | warning |
| ServiceDown | 0 requêtes pendant 2min | critical |
| CircuitBreakerOpen | Circuit ouvert | critical |

### Silencer une alerte

1. Aller dans Alertmanager
2. Cliquer sur l'alerte
3. **Silence** → Définir la durée
4. Ajouter un commentaire

### Configuration

Le fichier `observability/alertmanager/alertmanager.yml` définit :
- Routes de notification
- Groupement des alertes
- Inhibitions

## 6. Blackbox Exporter

### Rôle

Effectue des probes externes pour vérifier :
- Disponibilité HTTP
- Temps de réponse
- Certificats SSL

### Métriques

```promql
# Succès des probes
probe_success

# Temps de réponse
probe_http_duration_seconds

# Status HTTP
probe_http_status_code
```

## Bonnes pratiques

### Investigation d'incident

1. **Commencer par les métriques** (Prometheus/Grafana)
   - Identifier le service affecté
   - Quantifier l'impact

2. **Analyser les logs** (Loki)
   - Chercher les erreurs
   - Identifier le pattern

3. **Tracer une requête** (Tempo)
   - Comprendre le flux
   - Identifier le goulot d'étranglement

### Requêtes performantes

- Utiliser des labels pour filtrer au maximum
- Limiter les time ranges (éviter `[30d]`)
- Utiliser `rate()` plutôt que des compteurs bruts
- Agréger avec `sum by ()` pour réduire la cardinalité

### Dashboards efficaces

- Un dashboard = un objectif
- Utiliser des variables pour filtrer
- Ajouter des annotations pour les déploiements/incidents
- Configurer des liens vers Loki/Tempo depuis les panels
