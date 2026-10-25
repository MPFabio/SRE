# Runbook: Payment Service Latency

## Alerte
- **Nom**: `PaymentServiceHighLatency`
- **Sévérité**: warning
- **Condition**: P95 des paiements (`POST /api/payments`) > 1 s pendant 2 minutes

Voir aussi `HighLatencyP99Orders` (P99 des commandes > 1,5 s, 2 min) et
`CircuitBreakerOpen` (déclenchement immédiat).

## Impact
- Checkouts très lents (plus de 3 s)
- Timeouts côté utilisateur
- Le circuit breaker ne s'ouvre que sur des erreurs : une simple lenteur
  ne le déclenche pas
- Perte de revenus directe

## Diagnostic rapide

### 1. Vérifier les métriques
```promql
# Latence P99 actuelle des paiements
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket{endpoint="/api/payments"}[5m])))

# Requêtes par seconde, par route
sum by (endpoint) (rate(payment_requests_total[5m]))

# État du circuit breaker
circuit_breaker_state
```

### 2. Vérifier les logs
```logql
# Logs du service payment (lenteur, timeout, erreurs)
{job="payment-service"} |~ "(?i)(slow|timeout|error)"
```

### 3. Vérifier une trace
- Grafana → Explore → Tempo
- TraceQL : `{ resource.service.name = "payment-service" && duration > 2s }`

## Causes possibles

| Cause | Probabilité | Vérification |
|-------|-------------|--------------|
| Charge élevée | Haute | Vérifier RPS et CPU |
| Dépendance lente (DB, externe) | Moyenne | Vérifier traces |
| Fuite mémoire | Moyenne | Vérifier métriques mémoire |
| Chaos injecté | Élevée pendant un exercice | Incident en cours dans l'Operations Console |

## Résolution

### Si chaos engineering actif
L'injection s'arrête quand l'incident est résolu dans l'Operations Console
(*Mark Resolved*). Pour vérifier l'état du chaos sur chaque service :

```bash
for svc in catalog-service:8081 cart-service:8082 orders-service:8083 payment-service:8084 users-service:8085; do
  echo "${svc%%:*} : $(kubectl exec deploy/${svc%%:*} -- curl --silent localhost:${svc##*:}/api/chaos)"
done
```

### Si charge élevée
```bash
# Scale up le service
kubectl scale deployment payment-service --replicas=3
```

### Si dépendance externe
1. Identifier la dépendance via les traces
2. Vérifier le status de la dépendance
3. Activer le fallback si disponible

### Si fuite mémoire
```bash
# Redémarrer le service
kubectl rollout restart deployment/payment-service
```

## Vérification post-résolution

1. Vérifier que la latence P99 des paiements est revenue sous 1 s
2. Vérifier que le circuit breaker est fermé
3. Vérifier qu'il n'y a plus d'erreurs dans les logs
4. Effectuer un achat complet dans la boutique (http://localhost:8080)

## Escalade

Si non résolu après 15 minutes :
1. Contacter l'équipe Payment
2. Envisager le rollback
3. Activer le mode dégradé si disponible

## Post-incident

- [ ] Créer le post-mortem
- [ ] Identifier la cause racine
- [ ] Définir les actions correctives
- [ ] Mettre à jour ce runbook si nécessaire
