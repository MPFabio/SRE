# Module fil rouge : brancher votre service sur CapShop

Vous développez un module de CapShop, dans le langage et sur le métier de
votre choix : avis produits, livraison, fidélité, recommandations... Le lab
l'accueille à côté des six services existants, et le surveille avec la même
stack : Prometheus, Grafana, Loki, Tempo.

Un exemple complet est fourni, en Python et en Go :
[`reviews-service`](reviews-service/), un service d'avis produits. Vous
pouvez le suivre, vous en inspirer ou faire tout autre chose.

## Conditions pour s'intégrer au lab

Votre module est libre, à quatre conditions près :

| Condition | Pourquoi |
|---|---|
| Une **image Docker** poussée sur un registry que le cluster peut lire | Kubernetes la télécharge pour lancer le pod |
| Un **port HTTP**, lu dans la variable `PORT` (8086 par défaut) | Le Service Kubernetes y envoie le trafic |
| Une **route de santé** qui répond 200 (`/health` par défaut) | Sondes `readiness` et `liveness`, sonde Blackbox |
| Le processus écrit ses **logs sur la sortie standard** | Promtail les envoie dans Loki |

Deux éléments sont attendus plus tard dans le parcours, mais pas pour un
premier déploiement :

- une route **`/metrics`** au format Prometheus, pour les métriques business ;
- l'envoi de **traces OpenTelemetry** en OTLP/gRPC.

Tant que `/metrics` n'existe pas, la cible de votre module apparaît `down`
dans Prometheus : c'est normal.

## Ce que le lab fournit à votre conteneur

| Variable | Valeur |
|---|---|
| `PORT` | le port configuré (8086 par défaut) |
| `SERVICE_NAME`, `OTEL_SERVICE_NAME` | le nom du module |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `otel-collector:4317` (gRPC, sans TLS) |
| `REDIS_URL` | `redis://redis:6379`, si vous voulez stocker vos données dans Redis |
| `CATALOG_SERVICE_URL` | `http://catalog-service:8081`, pour interroger les produits |
| `DATABASE_URL` | URL PostgreSQL, seulement avec `learnerService.database=true` |

Vous pouvez ajouter les vôtres avec `--set learnerService.env.MA_VARIABLE=valeur`.

## Déployer votre module

Sur `utils-stagiaireXX`, avec le lab déjà installé :

```bash
helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.enabled=true \
    --set learnerService.name=reviews-service \
    --set learnerService.image=<registry>/<chemin>/reviews-service:1.0
```

Adaptez le nom, l'image, et au besoin le port (`learnerService.port`) ou la
route de santé (`learnerService.healthPath`). Le nom devient celui du
Deployment, du Service et du job Prometheus.

### Image sur le registry du GitLab commun

Le cluster a besoin d'un identifiant pour lire le registry GitLab. Dans
votre projet GitLab, **Settings** → **Repository** → **Deploy tokens**, créez
un token avec le droit `read_registry`, puis :

```bash
kubectl create secret docker-registry gitlab-registry \
    --docker-server=<adresse du registry GitLab> \
    --docker-username=<nom du token> \
    --docker-password=<valeur du token>

helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.imagePullSecret=gitlab-registry
```

### Prendre en compte la nouvelle cible dans Prometheus

Le déploiement ajoute votre module à la configuration de Prometheus. Elle
arrive dans le pod au bout d'une minute environ, puis :

```bash
curl --request POST http://localhost:9090/-/reload
```

## Vérifier

```bash
kubectl get pods -l app=reviews-service
kubectl logs deploy/reviews-service --tail 20
kubectl exec deploy/api-gateway -- curl --silent reviews-service:8086/health
```

- **Prometheus** (http://localhost:9090/targets) : la cible `reviews-service`
  est `up` si votre module expose `/metrics`.
- **Loki** (Grafana, Explore) : `{job="reviews-service"}`.
- **Tempo** (Grafana, Explore) : `{ resource.service.name = "reviews-service" }`,
  si votre module envoie des traces.

Pour appeler votre module depuis votre poste, ajoutez un port-forward
(`kubectl port-forward svc/reviews-service 8086:8086`) et le port 8086 à
votre tunnel SSH.

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| `learnerService.image est obligatoire` | Image non renseignée | `--set learnerService.image=...` |
| `ImagePullBackOff` | Image absente, mauvais chemin, ou registry non autorisé | `kubectl describe pod -l app=<nom>`, vérifier le chemin et le secret `imagePullSecret` |
| `CrashLoopBackOff` | Le programme s'arrête au démarrage | `kubectl logs deploy/<nom> --previous` |
| `Running` mais `0/1` prêt | La route de santé ne répond pas 200, ou pas sur le bon port | `kubectl describe pod -l app=<nom>` (section Events), vérifier `PORT` et `healthPath` |
| Cible `down` dans Prometheus | Pas de `/metrics`, ou autre chemin | Normal avant l'exercice métriques ; sinon `--set learnerService.metricsPath=...` |
| Cible absente dans Prometheus | Configuration pas encore rechargée | Attendre une minute puis `curl --request POST http://localhost:9090/-/reload` |
| `exec format error` | Image construite pour une autre architecture | Construire sur `utils-stagiaireXX`, ou `docker build --platform linux/amd64` |

</details>
