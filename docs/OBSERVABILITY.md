# Guide Observabilité - Reskilling SRE

Ce guide détaille l'utilisation des outils d'observabilité de l'application fil rouge.

## Vue d'ensemble

L'application fil rouge utilise la stack **Grafana** pour l'observabilité :

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

# Latence (histogram), exemple sur le service payment
payment_request_duration_seconds_bucket
payment_request_duration_seconds_sum
payment_request_duration_seconds_count
```

Chaque service possède son propre préfixe : `gateway_*`, `catalog_*`, `cart_*`, `orders_*`, `payment_*`, `users_*`. Les services de ShopEasy n'ont pas de métrique générique `http_requests_total` ; votre module peut en avoir une, comme l'exemple `reviews-service`.

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

# Connexions réellement occupées
db_pool_size - db_pool_idle

# Latence des requêtes, par opération
histogram_quantile(0.99, sum by (le, operation) (rate(db_query_duration_seconds_bucket[5m])))

# Erreurs de requête
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

# Latence du provider de paiement externe (histogram)
histogram_quantile(0.99, rate(external_payment_provider_latency_seconds_bucket[5m]))

# Erreurs du provider externe
rate(external_payment_provider_errors_total[5m])
```

### Requêtes PromQL utiles

```promql
# Taux d'erreur global (%) vu depuis l'API Gateway
100 * sum(rate(gateway_requests_total{status=~"5.."}[5m])) 
    / sum(rate(gateway_requests_total[5m]))

# Latence P50, P90, P99 des paiements (sans les health checks ni /metrics,
# bien plus nombreux que les paiements)
histogram_quantile(0.50, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[5m])))
histogram_quantile(0.90, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[5m])))
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[5m])))

# Requêtes par service
sum by (service) (rate(gateway_requests_total[5m]))

# Services avec le plus d'erreurs
topk(5, sum by (service) (rate(gateway_requests_total{status=~"5.."}[5m])))
```

### Règles d'alertes

Les règles sont dans la ConfigMap `prometheus-rules`, générée depuis
`helm/reskilling-lab/files/sre_rules.yml` (copie pour le mode local :
`observability/prometheus/rules/sre_rules.yml`). Les principales sont
décrites dans la section [Alertmanager](#5-alertmanager) ; la liste
complète est sur http://localhost:9090/alerts.

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

# Par service (label "service" alimenté par Promtail à partir du chemin des fichiers de logs)
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

Les logs sont en texte brut (pas de JSON). Deux formats coexistent : les
access logs d'uvicorn, une ligne par requête, et les logs applicatifs, qui
portent l'identifiant de leur trace :
```
INFO:     172.23.0.15:36068 - "GET /api/products HTTP/1.1" 200 OK
2026-10-24 21:35:39,110 - catalog-service - INFO - trace_id=be8a71449096822671177d4574f05da7 - Returned product 15: Thunderbolt 3 Dock
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

Une trace représente une requête de bout en bout. Celle d'un achat :

```
[api-gateway]      POST /api/orders                       258 ms
  [orders-service]   create_order                         250 ms
    [cart-service]     GET /api/cart/{user_id}              2 ms
    [payment-service]  POST /api/payments                 179 ms
    [catalog-service]  POST /api/products/{id}/reserve      4 ms
    [cart-service]     DELETE /api/cart/{user_id}           3 ms
```

Chaque **span** contient :
- Nom de l'opération
- Service
- Durée
- Tags (HTTP method, status, etc.)
- Logs/événements

### Corrélation logs ↔ traces

Les logs applicatifs des services portent l'identifiant de leur trace
(`trace_id=...`). Les access logs d'uvicorn (`"GET /api/products HTTP/1.1"
200`) n'en ont pas.

1. Dans Loki, dépliez une ligne de log qui contient `trace_id=`
2. Le champ **TraceID** propose un lien vers Tempo
3. Grafana ouvre la trace correspondante

Dans l'autre sens, depuis une trace dans Tempo, le bouton **Logs for this
span** affiche les logs du service qui portent cet identifiant.

### Carte des services

Explore → Tempo, onglet **Service Graph** : Tempo calcule les appels entre
services à partir des traces (métriques `traces_service_graph_*` dans
Prometheus), avec leur débit et leurs erreurs.

## 4. Grafana - Dashboards

### Connexion

- URL : http://localhost:3000
- Login : `admin`, mot de passe stocké dans le secret de l'application fil rouge :

```bash
kubectl get secret lab-secrets --output jsonpath='{.data.GRAFANA_ADMIN_PASSWORD}' | base64 --decode
```

### Dashboard "SRE Overview"

Menu de gauche, **Dashboards**, puis **SRE Overview**. Il contient :

| Panel | Type | Contenu |
|---|---|---|
| Availability | Stat | Disponibilité globale vue par la gateway |
| P99 Latency | Stat | Latence P99 globale |
| Circuit Breaker | Stat | État du circuit breaker du paiement |
| Active Incidents | Stat | Incidents en cours dans l'Operations Console |
| Request Rate by Service | Time series | Requêtes par seconde, par service |
| Latency by Service (P95) | Time series | Latence P95, par service |
| Error Budget Remaining | Gauge | Budget d'erreur restant |
| Requests by Status Code | Time series | Requêtes par code HTTP |

Il ne montre ni P50 et P90, ni taux d'erreur en pourcentage, ni logs :
c'est l'objet du bonus 2.4.

### Modifier le dashboard

Vous pouvez modifier le dashboard fourni, ou travailler sur une copie :
**Save dashboard** → **Save as copy**, avec le nom `Reskilling Overview`.
Selon la version de Grafana, la copie se trouve aussi dans le menu ⋮ ou
**Settings** → **Save as**.

Pour ajouter un panel :

1. **Add** → **Visualization**
2. Choisir la source de données (Prometheus pour les métriques, Loki pour
   les logs)
3. Passer l'éditeur en **Code** et coller la requête
4. Choisir le type de visualisation dans le panneau de droite (Time
   series, Gauge, Stat, Logs)
5. Régler le titre, l'unité (**Standard options** → **Unit**) et les seuils
   (**Thresholds**) dans le même panneau
6. **Back to dashboard**, puis **Save dashboard**

### Requêtes pour le bonus 2.4

**Latence P50, P90, P99 par service** (Time series, unité *seconds*) : une
requête par quantile, avec **Add query**. Dans **Options** → **Legend**,
mettre `{{service}} P99` pour distinguer les courbes.

```promql
histogram_quantile(0.50, sum by (le, service) (rate(gateway_request_duration_seconds_bucket[5m])))
histogram_quantile(0.90, sum by (le, service) (rate(gateway_request_duration_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le, service) (rate(gateway_request_duration_seconds_bucket[5m])))
```

**Taux d'erreur** (Gauge, unité *Percent (0-100)*, seuils : vert de base,
orange à 1, rouge à 5) :

```promql
100 * sum(rate(gateway_requests_total{status=~"5.."}[5m])) / sum(rate(gateway_requests_total[5m]))
```

**Trafic total** (Stat, unité *requests/sec*) :

```promql
sum(rate(gateway_requests_total[5m]))
```

**Logs d'erreur récents** (Logs, source Loki) :

```logql
{job=~"api-gateway|.+-service"} |~ "(?i)error| 5[0-9]{2} "
```

## 5. Alertmanager

### Accès

http://localhost:9093

### Alertes configurées

| Alerte | Condition | Sévérité |
|--------|-----------|----------|
| HighErrorRate | 5xx > 1 % d'un service, vu de la gateway, pendant 2 min | warning |
| CriticalErrorRate | 5xx > 5 % pendant 1 min | critical |
| HighLatencyP99 | P99 > 500 ms pendant 2 min (hors orders) | warning |
| HighLatencyP99Orders | P99 des commandes > 1,5 s pendant 2 min | warning |
| CriticalLatencyP99 | P99 > 1 s pendant 1 min (hors orders) | critical |
| PaymentServiceHighLatency | P95 des paiements > 1 s pendant 2 min | warning |
| CircuitBreakerOpen | Circuit breaker du paiement ouvert | critical |
| ServiceDown | Target Prometheus injoignable (`up == 0`) pendant 1 min | critical |
| EndpointDown | Probe Blackbox en échec pendant 1 min | critical |
| ErrorBudgetFastBurn | Budget d'erreur consommé 14,4 fois trop vite (1 h) | critical |
| DatabaseDown | PostgreSQL injoignable pendant 1 min | critical |
| DatabasePoolExhausted | Pool de connexions saturé pendant 3 min | critical |

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
- Utiliser `rate()` plutôt que des counters bruts
- Agréger avec `sum by ()` pour réduire la cardinalité

### Dashboards efficaces

- Un dashboard = un objectif
- Utiliser des variables pour filtrer
- Ajouter des annotations pour les déploiements/incidents
- Configurer des liens vers Loki/Tempo depuis les panels
