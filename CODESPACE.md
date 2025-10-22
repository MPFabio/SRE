# Lab SRE dans Codespace

Ce guide explique comment utiliser le lab SRE dans un environnement Codespace de GitHub.

## 🚀 Démarrage Rapide

### 1. Démarrer le lab
```bash
# Script optimisé pour Codespace
./start_lab_codespace.sh
```

### 2. Tester les services
```bash
# Test complet des services
./test_codespace.sh
```

## 🌐 Accès aux Services

### Port Forwarding Automatique
Dans Codespace, les ports sont automatiquement exposés :

- **URL Shortener**: `http://localhost:30000`
- **Splunk**: `http://localhost:8000`
- **Métriques**: `http://localhost:30000/metrics`

### Interface VS Code
1. Ouvrez l'onglet **"Ports"** dans VS Code
2. Les ports 30000 et 8000 apparaîtront automatiquement
3. Cliquez sur **"Open in Browser"** pour accéder aux services

## 🧪 Tests en Ligne de Commande

### Test de base
```bash
# Vérifier la santé du service
curl http://localhost:30000/health

# Voir les métriques
curl http://localhost:30000/metrics

# Créer une URL courte
curl -X POST "http://localhost:30000/shorten?url=https://www.google.com"
```

### Test complet
```bash
# Lancer tous les tests
./test_codespace.sh
```

## 📊 Surveillance

### Vérifier les pods
```bash
kubectl get pods
kubectl get services
```

### Voir les logs
```bash
# Logs du service
kubectl logs -l app=url-shortener -f

# Logs Splunk
docker-compose logs splunk
```

### Métriques Prometheus
```bash
# Métriques brutes
curl http://localhost:30000/metrics

# Métriques formatées
curl http://localhost:30000/metrics | grep -E "(http_requests_total|urls_created_total)"
```

## 🔧 Configuration Spécifique Codespace

### Port Forwarding Manuel
Si le port forwarding automatique ne fonctionne pas :

```bash
# URL Shortener
kubectl port-forward --address 0.0.0.0 service/url-shortener-service 30000:80 &

# Splunk
docker port splunk-sre-lab 8000
```

### Variables d'Environnement
```bash
# Exporter les URLs pour les tests
export URL_SHORTENER="http://localhost:30000"
export SPLUNK_URL="http://localhost:8000"
export METRICS_URL="http://localhost:30000/metrics"
```

## 🚨 Dépannage

### Problèmes Courants

1. **Service inaccessible**
   ```bash
   # Vérifier les pods
   kubectl get pods
   
   # Redémarrer si nécessaire
   kubectl delete pod -l app=url-shortener
   ```

2. **Port forwarding échoué**
   ```bash
   # Vérifier les services
   kubectl get services
   
   # Redémarrer le port forwarding
   pkill -f "kubectl port-forward"
   ./start_lab_codespace.sh
   ```

3. **Splunk non accessible**
   ```bash
   # Vérifier le container
   docker ps | grep splunk
   
   # Redémarrer Splunk
   docker-compose restart splunk
   ```

### Logs de Debug
```bash
# Logs détaillés
kubectl logs -l app=url-shortener --tail=50

# Événements Kubernetes
kubectl get events --sort-by='.lastTimestamp'

# Statut des services
kubectl describe service url-shortener-service
```

## 📚 Exercices dans Codespace

### Exercice 1: Test de Base
```bash
# Créer plusieurs URLs
curl -X POST "http://localhost:30000/shorten?url=https://www.github.com"
curl -X POST "http://localhost:30000/shorten?url=https://www.stackoverflow.com"

# Tester les redirections
curl -I http://localhost:30000/[CODE_COURT]
```

### Exercice 2: Surveillance
```bash
# Générer du trafic
cd simulator
python3 traffic_generator.py --duration 30 --rpm 10

# Surveiller les métriques
watch -n 5 'curl -s http://localhost:30000/metrics | grep http_requests_total'
```

### Exercice 3: Simulation d'Incident
```bash
# Déclencher un incident
cd incident
./trigger_failure.sh

# Surveiller la récupération
kubectl get pods -w
```

## 🔗 URLs Utiles

- **Service Principal**: http://localhost:30000
- **Health Check**: http://localhost:30000/health
- **Métriques**: http://localhost:30000/metrics
- **Splunk**: http://localhost:8000 (admin/admin123)
- **Documentation**: README.md

## 💡 Conseils

1. **Utilisez l'onglet Ports** de VS Code pour accéder aux services
2. **Gardez le terminal ouvert** pour le port forwarding
3. **Utilisez curl** pour tester les APIs
4. **Surveillez les logs** avec `kubectl logs -f`
5. **Testez régulièrement** avec `./test_codespace.sh`

---

**Lab SRE - Optimisé pour Codespace**  
**Prêt pour l'apprentissage des pratiques SRE !**
