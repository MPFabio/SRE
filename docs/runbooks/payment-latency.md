# Runbook: Payment Service Latency

## Alerte
- **Nom**: `PaymentServiceHighLatency`
- **Sévérité**: warning
- **Condition**: P95 du paiement > 300 ms pendant 2 minutes

Voir aussi `HighLatencyP99` (P99 gateway > 500 ms, 2 min) et
`CircuitBreakerOpen` (declenchement immediat).

## Impact
- Checkouts extrêmement lents (>5s)
- Timeouts côté utilisateur
- Circuit breaker peut s'ouvrir → échecs de paiement
- Perte de revenus directe

## Diagnostic rapide

### 1. Vérifier les métriques
```promql
# Latence P99 actuelle
histogram_quantile(0.99, sum by (le) (rate(payment_request_duration_seconds_bucket[5m])))

# Requêtes par seconde
rate(payment_requests_total[5m])

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
- Chercher des traces > 2s pour le service `payment`

## Causes possibles

| Cause | Probabilité | Vérification |
|-------|-------------|--------------|
| Charge élevée | Haute | Vérifier RPS et CPU |
| Dépendance lente (DB, externe) | Moyenne | Vérifier traces |
| Fuite mémoire | Moyenne | Vérifier métriques mémoire |
| Configuration chaos | Application fil rouge | Incident en cours dans l'Operations Console |

## Résolution

### Si chaos engineering actif
L'injection s'arrete quand l'incident est resolu dans l'Operations Console
(*Mark Resolved*). Pour verifier l'etat du chaos sur chaque service :

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

1. Vérifier que la latence P99 < 500ms
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
