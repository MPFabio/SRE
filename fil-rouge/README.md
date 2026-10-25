# Module fil rouge : brancher votre service

Vous développez un module de CapShop, dans le langage et sur le métier de
votre choix : avis produits, livraison, fidélité, recommandations... L'application fil rouge
l'accueille à côté des six services existants, et le surveille avec la même
stack : Prometheus, Grafana, Loki, Tempo.

Un exemple est fourni, [`reviews-service`](reviews-service/), un service
d'avis produits. Vous pouvez le suivre, vous en inspirer ou faire tout
autre chose. Deux guides le construisent pas à pas, en trois étapes :

- [Écrire votre module en Go](module-go.md)
- [Écrire votre module en Python](module-python.md)

Chaque étape existe aussi en version prête à l'emploi. La suite du parcours
s'appuie sur votre module : si vous êtes bloqué, déployez la version de
l'étape où vous en êtes et continuez.

## Conditions pour s'intégrer à l'application fil rouge

Votre module est libre, à quatre conditions près :

| Condition | Pourquoi |
|---|---|
| Une **image Docker** poussée sur un registry que le cluster peut lire | Kubernetes la télécharge pour lancer le pod |
| Un **port HTTP**, lu dans la variable `PORT` (8086 par défaut) | Le Service Kubernetes y envoie le trafic |
| Un **endpoint de health check** qui répond 200 (`/health` par défaut) | Readiness et liveness probes, probe Blackbox |
| Le processus écrit ses **logs sur stdout** | Promtail les envoie dans Loki |

Deux éléments sont attendus plus tard dans le parcours, mais pas pour un
premier déploiement :

- une route **`/metrics`** au format Prometheus, pour les métriques business ;
- l'envoi de **traces OpenTelemetry** en OTLP/gRPC.

Tant que `/metrics` n'existe pas, la target de votre module apparaît `down`
dans Prometheus : c'est normal.

## Ce que l'application fil rouge fournit à votre container

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

L'image de votre module est publiée sur le registry de conteneurs du GitLab
commun, dans votre projet. Le cluster la télécharge depuis ce registry.

### 1. Pousser l'image sur le registry GitLab

Dans votre projet sur https://gitlab.reskilling.internal, la page
**Deploy** → **Container Registry** affiche l'adresse du registry et le
chemin de votre image. Créez un jeton d'accès personnel (avatar →
**Preferences** → **Access tokens**) avec les droits `read_registry` et
`write_registry`, puis sur `utils-stagiaireXX`, depuis la racine du repo,
en remplaçant chaque `<...>` par sa valeur :

```bash
echo 'export IMAGE=<adresse du registry>/<groupe>/<projet>' >> ~/.bashrc   # affiché dans Container Registry
source ~/.bashrc
docker login <adresse du registry> -u <votre identifiant>   # mot de passe : le jeton
docker build --tag $IMAGE:etape1 mon-module/
docker push $IMAGE:etape1
```

Comme `STAGIAIRE`, la variable `IMAGE` reste définie dans chaque nouveau
terminal. `mon-module/` est le dossier de votre module ; pour la version
prête à l'emploi, `fil-rouge/reviews-service/go/1-base/` ou
`fil-rouge/reviews-service/python/1-base/`.

À partir de l'exercice CI, c'est le pipeline de votre projet qui construit
et pousse l'image : voir [l'exemple de pipeline](ci/README.md).

### 2. Autoriser le cluster à lire le registry

Une seule fois. Dans votre projet GitLab, **Settings** → **Repository** →
**Deploy tokens**, créez un token avec le droit `read_registry`, puis :

```bash
kubectl create secret docker-registry gitlab-registry \
    --docker-server=<adresse du registry> \
    --docker-username=<nom du token> \
    --docker-password=<valeur du token>
```

### 3. Activer le module

Avec l'application fil rouge déjà installée :

```bash
helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.enabled=true \
    --set learnerService.name=reviews-service \
    --set learnerService.image=$IMAGE:etape1 \
    --set learnerService.imagePullSecret=gitlab-registry
```

Adaptez le nom, et au besoin le port (`learnerService.port`) ou l'endpoint
de health check (`learnerService.healthPath`). Le nom devient celui du
Deployment, du Service et du job Prometheus.

Pour une nouvelle version, poussez l'image sous un nouveau tag, puis :

```bash
helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.image=$IMAGE:etape2
```

### Prendre en compte la nouvelle target dans Prometheus

Le déploiement ajoute votre module à la configuration de Prometheus. Elle
arrive dans le pod au bout d'une minute environ, puis :

```bash
curl --request POST http://localhost:9090/-/reload
```

### Afficher les avis dans la boutique (optionnel)

Avec l'exemple `reviews-service`, ou un module qui expose la même API
(`GET` et `POST /api/reviews/{product_id}`), la boutique peut afficher les
avis sous chaque produit et proposer d'en laisser un. Le générateur de
trafic publie et lit alors des avis en continu.

```bash
helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.shop=true
```

La gateway route alors `/api/reviews/...` vers votre module. Si le module
tombe, la boutique continue de fonctionner et affiche « Avis clients
indisponibles ». Laissez cette option désactivée si votre module a une
autre API.

## Vérifier

```bash
kubectl get pods -l app=reviews-service
kubectl logs deploy/reviews-service --tail 20
kubectl exec deploy/api-gateway -- curl --silent reviews-service:8086/health
```

- **Prometheus** (http://localhost:9090/targets) : la target `reviews-service`
  est `up` si votre module expose `/metrics`.
- **Loki** (Grafana, Explore) : `{job="reviews-service"}`.
- **Tempo** (Grafana, Explore) : `{ resource.service.name = "reviews-service" }`,
  si votre module envoie des traces.

Pour appeler votre module depuis votre poste, ajoutez un port-forward
(`kubectl port-forward svc/reviews-service 8086:8086`, avec
`--address 0.0.0.0` si vous passez par FoxyProxy), et le port 8086 à votre
tunnel SSH si vous utilisez l'option A de l'installation.

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| `learnerService.image est obligatoire` | Image non renseignée | `--set learnerService.image=...` |
| `ImagePullBackOff` | Image absente, mauvais chemin, ou registry non autorisé | `kubectl describe pod -l app=<nom>`, vérifier le chemin et le secret `imagePullSecret` |
| `CrashLoopBackOff` | Le programme s'arrête au démarrage | `kubectl logs deploy/<nom> --previous` |
| `Running` mais `0/1` prêt | Le health check ne répond pas 200, ou pas sur le bon port | `kubectl describe pod -l app=<nom>` (section Events), vérifier `PORT` et `healthPath` |
| Target `down` dans Prometheus | Pas de `/metrics`, ou autre chemin | Normal avant l'exercice métriques ; sinon `--set learnerService.metricsPath=...` |
| Target absente dans Prometheus | Configuration pas encore rechargée | Attendre une minute puis `curl --request POST http://localhost:9090/-/reload` |
| `exec format error` | Image construite pour une autre architecture | Construire sur `utils-stagiaireXX`, ou `docker build --platform linux/amd64` |

</details>
