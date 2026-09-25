# Guide SLOs et Alerting - Reskilling Lab

Ce guide explique comment définir des SLOs, calculer l'Error Budget, et configurer des alertes efficaces.

## Concepts fondamentaux

### SLI (Service Level Indicator)

Un **SLI** est une métrique qui mesure un aspect de la qualité du service.

**Exemples de SLIs** :
- Latence : Temps de réponse P99
- Disponibilité : % de requêtes réussies
- Throughput : Requêtes par seconde
- Exactitude : % de réponses correctes

### SLO (Service Level Objective)

Un **SLO** est un objectif cible pour un SLI.

**Exemples de SLOs** :
- "99.5% des requêtes doivent réussir sur 30 jours"
- "P99 de latence < 500ms"
- "99.9% de disponibilité mensuelle"

### Error Budget

L'**Error Budget** est la marge d'erreur autorisée par le SLO.

```
Error Budget = 100% - SLO
```

**Exemple** :
- SLO de disponibilité : 99.5%
- Error Budget : 0.5%
- Sur 30 jours : 0.5% × 30 × 24 × 60 = **216 minutes** de downtime autorisé

## SLOs recommandés pour Reskilling

### Service Catalog

| SLI | SLO | Justification |
|-----|-----|---------------|
| Disponibilité | 99.5% | Les produits doivent être visibles |
| Latence P99 | < 200ms | Navigation fluide |
| Taux d'erreur | < 1% | Peu d'impact UX si quelques erreurs |

**Requêtes Prometheus** :

```promql
# Disponibilité
sum(rate(catalog_requests_total{status!~"5.."}[5m])) 
/ sum(rate(catalog_requests_total[5m]))

# Latence P99
histogram_quantile(0.99, 
  sum by (le) (rate(catalog_request_duration_seconds_bucket[5m])))

# Taux d'erreur
sum(rate(catalog_requests_total{status=~"5.."}[5m])) 
/ sum(rate(catalog_requests_total[5m]))
```

### Service Cart

| SLI | SLO | Justification |
|-----|-----|---------------|
| Disponibilité | 99.9% | Critique pour la conversion |
| Latence P99 | < 300ms | Actions rapides attendues |
| Durabilité | 99.99% | Ne pas perdre le panier |

### Service Payment

| SLI | SLO | Justification |
|-----|-----|---------------|
| Disponibilité | 99.95% | Très critique - revenus |
| Latence P99 | < 500ms | Checkout peut être plus lent |
| Exactitude | 100% | Jamais de double charge |

### Service Orders

| SLI | SLO | Justification |
|-----|-----|---------------|
| Disponibilité | 99.9% | Critique pour finaliser l'achat |
| Latence P99 | < 1s | Création peut être plus lente |
| Durabilité | 99.99% | Ne pas perdre de commandes |

## Calcul de l'Error Budget

### Formule générale

```
Budget consommé = (Erreurs observées / Total requêtes) × 100
Budget restant = Error Budget total - Budget consommé
```

### Exemple pratique

**Contexte** :
- SLO : 99.5% disponibilité sur 30 jours
- Error Budget : 0.5% = 216 minutes

**Après 15 jours** :
- 50 minutes de downtime
- Budget consommé : 50 / 216 = 23%
- Budget restant : 77% (166 minutes)

**Interprétation** :
- Budget sain → Autoriser les déploiements risqués
- Budget < 50% → Prudence, focus stabilité
- Budget < 20% → Freeze des déploiements

### Dashboard Error Budget

Créez un panel Grafana avec :

```promql
# Disponibilité actuelle (rolling 30d), vue depuis l'API Gateway
avg_over_time(
  (sum(rate(gateway_requests_total{status!~"5.."}[5m])) 
   / sum(rate(gateway_requests_total[5m])))[30d:1h]
)

# Budget restant (%), pour un SLO de 99,5%
(
  avg_over_time(
    (sum(rate(gateway_requests_total{status!~"5.."}[5m]))
     / sum(rate(gateway_requests_total[5m])))[30d:1h]
  ) - 0.995
) / 0.005 * 100
```

## Burn Rate

Le **Burn Rate** mesure la vitesse de consommation de l'Error Budget.

### Définition

```
Burn Rate = Taux d'erreur actuel / Taux d'erreur autorisé
```

**Exemples** :
- Burn Rate = 1 → Consommation normale (budget épuisé en 30j)
- Burn Rate = 6 → 6x plus rapide (budget épuisé en 5j)
- Burn Rate = 14.4 → 14x plus rapide (budget épuisé en 2j)

### Alertes basées sur Burn Rate

L'approche classique utilise des alertes multi-fenêtres :

| Type | Burn Rate | Fenêtre courte | Fenêtre longue | Urgence |
|------|-----------|----------------|----------------|---------|
| Fast Burn | 14.4× | 1h | 5m | Page immédiat |
| Medium Burn | 6× | 6h | 30m | Page |
| Slow Burn | 3× | 3d | 6h | Ticket |

### Configuration Prometheus

```yaml
# observability/prometheus/rules/slo_alerts.yml
groups:
  - name: slo_burn_rate
    rules:
      # Fast Burn Alert (14.4x, épuisement en 2 jours)
      - alert: SLOBurnRateFast
        expr: |
          (
            sum(rate(gateway_requests_total{service="payment",status=~"5.."}[5m]))
            / sum(rate(gateway_requests_total{service="payment"}[5m]))
          ) > (14.4 * 0.005)
          and
          (
            sum(rate(gateway_requests_total{service="payment",status=~"5.."}[1h]))
            / sum(rate(gateway_requests_total{service="payment"}[1h]))
          ) > (14.4 * 0.005)
        for: 2m
        labels:
          severity: critical
          service: payment
        annotations:
          summary: "Fast burn rate on Payment service"
          description: "Error budget will be exhausted in < 2 days"

      # Slow Burn Alert (3x, épuisement en 10 jours)
      - alert: SLOBurnRateSlow
        expr: |
          (
            sum(rate(gateway_requests_total{service="payment",status=~"5.."}[6h]))
            / sum(rate(gateway_requests_total{service="payment"}[6h]))
          ) > (3 * 0.005)
          and
          (
            sum(rate(gateway_requests_total{service="payment",status=~"5.."}[3d]))
            / sum(rate(gateway_requests_total{service="payment"}[3d]))
          ) > (3 * 0.005)
        for: 1h
        labels:
          severity: warning
          service: payment
        annotations:
          summary: "Slow burn rate on Payment service"
          description: "Error budget will be exhausted in < 10 days"
```

## Alertmanager Configuration

### Routing des alertes

```yaml
# observability/alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  
  routes:
    # Alertes critiques  page immédiat
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    
    # Alertes SLO  équipe SRE
    - match_re:
        alertname: 'SLO.*'
      receiver: 'sre-team'
    
    # Alertes par service
    - match:
        service: payment
      receiver: 'payment-team'

receivers:
  - name: 'default'
    # Configuration par défaut
  
  - name: 'pagerduty'
    # Configuration PagerDuty
  
  - name: 'sre-team'
    # Configuration Slack/Email SRE
  
  - name: 'payment-team'
    # Configuration équipe Payment
```

### Silences et inhibitions

**Inhibitions** : Supprimer les alertes redondantes

```yaml
inhibit_rules:
  # Si service down, pas d'alerte latence
  - source_match:
      alertname: 'ServiceDown'
    target_match:
      alertname: 'HighLatency'
    equal: ['service']
```

## Bonnes pratiques

### 1. Définir des SLOs réalistes

- Basés sur des données historiques
- Alignés avec les attentes utilisateurs
- Pas trop ambitieux (99.99% est très dur)

### 2. Choisir les bons SLIs

| Type de service | SLIs recommandés |
|-----------------|------------------|
| API synchrone | Latence, disponibilité, erreurs |
| Pipeline async | Freshness, throughput, durabilité |
| Storage | Durabilité, latence lecture/écriture |
| Frontend | Time to Interactive, Core Web Vitals |

### 3. Alerter sur les symptômes, pas les causes

**Mauvais** : CPU > 80%
**Bon** : Latence P99 > SLO

### 4. Utiliser des fenêtres multi-durées

Évite les faux positifs tout en détectant les vrais problèmes.

### 5. Documenter les runbooks

Chaque alerte doit avoir :
- Description du problème
- Impact utilisateur
- Étapes de diagnostic
- Actions de résolution

### 6. Réviser régulièrement

- Revoir les SLOs chaque trimestre
- Analyser les alertes qui n'ont pas mené à une action
- Ajuster les seuils basés sur l'expérience

## Exercice pratique : Créer un SLO

### Étape 1 : Identifier le SLI

Pour le checkout :
- **SLI** : % de checkouts réussis en < 3s

### Étape 2 : Définir le SLO

- **SLO** : 99% des checkouts réussis en < 3s sur 7 jours

### Étape 3 : Calculer l'Error Budget

- Budget : 1% = 100.8 minutes/semaine

### Étape 4 : Créer la requête PromQL

```promql
# Checkouts réussis en < 3s
sum(rate(orders_requests_total{
  endpoint="/api/orders",
  method="POST",
  status="200"
}[5m])) 
/ 
sum(rate(orders_requests_total{
  endpoint="/api/orders",
  method="POST"
}[5m]))
```

### Étape 5 : Configurer l'alerte

```yaml
- alert: CheckoutSLOBreach
  expr: |
    (
      sum(rate(orders_requests_total{endpoint="/api/orders",method="POST",status!="200"}[1h]))
      / sum(rate(orders_requests_total{endpoint="/api/orders",method="POST"}[1h]))
    ) > 0.01
  for: 5m
  labels:
    severity: critical
    slo: checkout
  annotations:
    summary: "Checkout SLO breach"
    description: "Checkout success rate below 99%"
```

### Étape 6 : Créer le dashboard

Panel Grafana avec :
- Gauge : Disponibilité actuelle
- Graph : Historique 7 jours
- Single stat : Budget restant (%)
