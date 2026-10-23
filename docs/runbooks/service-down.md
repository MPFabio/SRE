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
# État de tous les pods
kubectl get pods

# Ou via Prometheus : targets injoignables
curl --silent --get http://localhost:9090/api/v1/query --data-urlencode 'query=up == 0'
```

### 2. Vérifier les logs
```bash
# Logs du service problématique
kubectl logs deploy/<service-name> --tail 100
```

### 3. Vérifier les ressources
```bash
# État, redémarrages, limites et derniers événements du pod
kubectl describe pod -l app=<service-name>
```

## Causes possibles

| Cause | Symptômes | Résolution |
|-------|-----------|------------|
| OOMKilled | `Last State: OOMKilled` | Augmenter mémoire ou restart |
| Crash loop | `CrashLoopBackOff` | Vérifier logs, fix bug |
| Dépendance down | `Readiness probe failed` | Vérifier Redis, autres services |
| Image introuvable | `ImagePullBackOff` | Vérifier le nom et le tag de l'image |
| Config erreur | `CreateContainerConfigError` | Vérifier ConfigMap et Secret |

## Résolution

### Redémarrage simple
```bash
kubectl rollout restart deployment/<service-name>
```

### Si OOMKilled
```bash
# Vérifier les events
kubectl get events --sort-by=.lastTimestamp | grep <service-name>

# Plus de mémoire (temporaire : un helm upgrade remet la valeur du chart)
kubectl set resources deployment/<service-name> --limits=memory=512Mi
```

### Si dépendance down
```bash
# Redémarrer dans l'ordre
kubectl rollout restart deployment/redis
kubectl rollout status deployment/redis
kubectl rollout restart deployment/<service-name>
```

### Si crash loop
```bash
# Logs du container qui vient de planter
kubectl logs deploy/<service-name> --previous

# Vérifier la configuration
kubectl get deployment <service-name> --output yaml
```

## Vérification post-résolution

```bash
# Vérifier le status
kubectl get pods -l app=<service-name>

# Vérifier le health
kubectl exec deploy/<service-name> -- curl --silent localhost:<port>/health

# Test global : les vingt pods Running
kubectl get pods
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
