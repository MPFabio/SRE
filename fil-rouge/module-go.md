# Écrire votre module en Go, pas à pas

Ce guide construit un module ShopEasy en trois étapes. Chaque étape se
déploie et fonctionne seule :

| Étape | Ce que le module sait faire | Version prête à l'emploi |
|---|---|---|
| 1 | Répondre à une API et à `/health` | [`reviews-service/go/1-base`](reviews-service/go/1-base/) |
| 2 | Exposer des métriques business | [`reviews-service/go/2-metriques`](reviews-service/go/2-metriques/) |
| 3 | Envoyer des traces OpenTelemetry | [`reviews-service/go/3-traces`](reviews-service/go/3-traces/) |

L'exemple suivi est un service d'avis produits, `reviews-service`. Vous
pouvez choisir un autre métier : la démarche reste la même.

> **Vous êtes en retard ou bloqué ?** Construisez la version prête à
> l'emploi de l'étape où vous en êtes (section « Construire et déployer »)
> et continuez le parcours. Vous reprendrez votre propre code plus tard.

Rien n'est à installer sur `utils-stagiaireXX` en dehors de Docker : le
code Go est compilé dans l'image. Pour les commandes `go` (gestion des
dépendances), cet alias les fait tourner dans un container, depuis le
dossier de votre module :

```bash
echo 'alias go='"'"'docker run --rm --user "$(id -u):$(id -g)" --env HOME=/tmp --env GOPATH=/tmp/go --volume "$PWD":/src --workdir /src golang:1.26-alpine go'"'"'' >> ~/.bashrc
source ~/.bashrc
go version
```

---

## Étape 1 : une API et un endpoint /health

### Ce qu'il faut écrire

Un dossier avec trois fichiers : `main.go`, `go.mod` et `Dockerfile`.

1. **`go.mod`** déclare le module :

   ```
   module capshop/reviews-service

   go 1.26
   ```

2. **`main.go`** démarre un serveur HTTP sur le port lu dans `PORT`, avec
   trois routes :

   | Route | Réponse |
   |---|---|
   | `GET /health` | `{"status": "ok"}`, code 200 |
   | `GET /api/reviews/{product_id}` | Les avis du produit et leur note moyenne |
   | `POST /api/reviews/{product_id}` | Enregistre un avis `{"rating": 1-5, "comment": "..."}`, code 201 |

   Le routeur de la bibliothèque standard suffit :

   ```go
   mux := http.NewServeMux()
   mux.HandleFunc("GET /health", health)
   mux.HandleFunc("GET /api/reviews/{product_id}", listReviews)
   mux.HandleFunc("POST /api/reviews/{product_id}", createReview)
   http.ListenAndServe(":"+os.Getenv("PORT"), mux)
   ```

   `req.PathValue("product_id")` lit l'identifiant dans l'URL. Les avis
   sont gardés en mémoire, dans une `map` protégée par un `sync.Mutex` :
   plusieurs requêtes peuvent arriver en même temps.

3. **Les logs** s'écrivent sur stdout avec `log/slog` :

   ```go
   slog.Info("avis publié", "product_id", id, "rating", review.Rating)
   ```

   Promtail les envoie dans Loki sans autre réglage.

4. **`Dockerfile`** en deux temps : compiler dans une image Go, puis copier
   le binaire dans une image légère.

   ```dockerfile
   FROM golang:1.26-alpine AS build
   WORKDIR /src
   COPY go.* ./
   RUN go mod download
   COPY main.go .
   RUN CGO_ENABLED=0 go build -o /reviews-service .

   FROM alpine:3.22
   COPY --from=build /reviews-service /reviews-service
   USER 10001
   EXPOSE 8086
   ENTRYPOINT ["/reviews-service"]
   ```

<details>
<summary>Code complet de l'étape 1</summary>

Voir [`reviews-service/go/1-base/main.go`](reviews-service/go/1-base/main.go).
La modération refuse (422) un avis contenant un mot interdit : c'est le
« métier » du service, qui donnera des métriques intéressantes à l'étape 2.

</details>

### Tester sur la VM

```bash
docker build --tag reviews-service:dev mon-module/
docker run --rm --publish 8086:8086 --env PORT=8086 reviews-service:dev
```

Dans un second terminal :

```bash
curl localhost:8086/health
curl --request POST localhost:8086/api/reviews/3 \
    --header 'Content-Type: application/json' \
    --data '{"rating": 4, "comment": "super casque"}'
curl localhost:8086/api/reviews/3
```

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| `go.sum: no such file` au build | `COPY go.mod go.sum` alors qu'il n'y a pas de dépendance | `COPY go.* ./` copie ce qui existe |
| `missing go.sum entry` | Dépendance ajoutée sans mettre à jour `go.sum` | `go mod tidy` dans le dossier du module |
| `pattern ... conflicts` ou routes ignorées | Go antérieur à 1.22 : les motifs `GET /...` n'existent pas | Garder `golang:1.26-alpine` dans le Dockerfile |
| `connection refused` sur `curl` | Le container n'écoute pas sur le port publié | Vérifier `--publish 8086:8086` et que le code lit `PORT` |
| 404 sur `/api/reviews/3` | Motif de route mal écrit | `GET /api/reviews/{product_id}`, avec l'espace après la méthode |

</details>

---

## Étape 2 : des métriques business

### Ce qu'il faut ajouter

1. La bibliothèque Prometheus : importez-la en tête de `main.go` (voir
   l'exemple), puis, une fois le code écrit, dans le dossier du module :

   ```bash
   go mod tidy
   ```

   `go mod tidy` ajoute à `go.mod` les bibliothèques importées par le code
   et remplit `go.sum`, la liste vérifiée des dépendances. Lancé avant
   d'écrire les imports, il retirerait au contraire la bibliothèque.

2. **Choisir ses métriques.** Une métrique business répond à une question
   du métier, pas de l'infrastructure. Pour des avis produits :

   | Question | Métrique | Type |
   |---|---|---|
   | Combien d'avis sont publiés ? | `reviews_created_total{rating}` | Counter |
   | Combien sont refusés, et pourquoi ? | `reviews_rejected_total{reason}` | Counter |
   | Les clients sont-ils satisfaits ? | `reviews_average_rating{product_id}` | Gauge |

   Un *Counter* ne fait que monter (on lit son rythme avec `rate()`), une
   *Gauge* monte et descend, un *Histogram* répartit des durées.

3. **Les déclarer et les alimenter** :

   ```go
   created = promauto.NewCounterVec(prometheus.CounterOpts{
       Name: "reviews_created_total", Help: "Avis publiés"}, []string{"rating"})
   ...
   created.WithLabelValues(strconv.Itoa(review.Rating)).Inc()
   ```

4. **Mesurer le trafic** de chaque route avec un counter de requêtes et un
   histogram de durée, dans une fonction qui enveloppe les handlers
   (`measure` dans l'exemple).

5. **Exposer `/metrics`** :

   ```go
   mux.Handle("GET /metrics", promhttp.Handler())
   ```

> Attention aux labels : `product_id` convient pour 15 produits, pas pour
> des millions. Chaque valeur de label crée une série dans Prometheus.

<details>
<summary>Code complet de l'étape 2</summary>

Voir [`reviews-service/go/2-metriques/main.go`](reviews-service/go/2-metriques/main.go).

</details>

### Vérifier

En local : `curl localhost:8086/metrics | grep reviews_` après avoir publié
un avis. Dans l'application fil rouge, après déploiement, la target passe `up` dans
http://localhost:9090/targets et la requête suivante répond :

```promql
sum by (rating) (reviews_created_total)
```

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| `no required module provides package` au build | `go mod tidy` lancé avant d'écrire les imports, ou pas lancé | `go mod tidy` une fois le code écrit |
| La métrique n'apparaît pas dans `/metrics` | Un `CounterVec` n'apparaît qu'après son premier `Inc()` | Publier un avis, puis relire `/metrics` |
| `duplicate metrics collector registration` au démarrage | Deux métriques portent le même nom | Renommer l'une d'elles |
| Target `down` dans Prometheus | Image pas encore mise à jour, ou mauvais chemin | `kubectl logs deploy/<nom>`, vérifier `learnerService.metricsPath` |
| Target absente | Configuration de Prometheus pas rechargée | `curl --request POST http://localhost:9090/-/reload` |

</details>

---

## Étape 3 : des traces OpenTelemetry

### Ce qu'il faut ajouter

1. Les bibliothèques OpenTelemetry (`go.opentelemetry.io/otel`, son SDK,
   l'exporteur `otlptracegrpc` et `otelhttp`) : importez-les dans
   `main.go`, puis, une fois le code écrit, lancez `go mod tidy` comme à
   l'étape 2.

2. **Configurer l'envoi des traces** au démarrage, vers le collecteur du
   fil rouge (variable `OTEL_EXPORTER_OTLP_ENDPOINT`, en gRPC sans TLS), avec le
   nom du service : c'est lui qui apparaîtra dans Tempo. Voir
   `setupTracing` dans l'exemple.

3. **Tracer chaque requête** en enveloppant les handlers :

   ```go
   otelhttp.NewHandler(handler, "/api/reviews/{product_id}")
   ```

4. **Découper le traitement en étapes** avec des spans, pour voir où
   passe le temps :

   ```go
   _, span := tracer.Start(req.Context(), "moderate_review")
   refused := isForbidden(review.Comment)
   span.End()
   ```

5. **Suivre la requête dans les autres services.** L'exemple vérifie que
   le produit existe en appelant `catalog-service` (variable
   `CATALOG_SERVICE_URL`). Pour que la trace continue dans le catalogue,
   l'appel passe par un client instrumenté, et le contexte de trace est
   propagé dans les headers HTTP :

   ```go
   otel.SetTextMapPropagator(propagation.TraceContext{})
   client := &http.Client{Transport: otelhttp.NewTransport(http.DefaultTransport)}
   req, _ := http.NewRequestWithContext(ctx, http.MethodGet, catalogURL+"/api/products/3", nil)
   ```

   Sans le propagateur, chaque service produit sa propre trace, sans lien
   entre elles.

<details>
<summary>Code complet de l'étape 3</summary>

Voir [`reviews-service/go/3-traces/main.go`](reviews-service/go/3-traces/main.go).

</details>

### Vérifier

Après déploiement et quelques avis publiés, dans Grafana, Explore, source
**Tempo**, onglet TraceQL :

```traceql
{ resource.service.name = "reviews-service" }
```

Une trace de `POST` contient le span de la requête, ses étapes
`verify_product`, `moderate_review` et `store_review`, et sous
`verify_product` les spans de `catalog-service`.

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| `traces désactivées` ou erreurs d'export en local | Pas de collecteur hors du cluster | Normal en `docker run` ; tester une fois déployé |
| La trace s'arrête à votre service, sans `catalog-service` | Contexte de trace non propagé | `otel.SetTextMapPropagator(propagation.TraceContext{})`, client `otelhttp.NewTransport`, requête créée avec le contexte du span |
| Tous les avis sont refusés en 503 en local | Pas de catalogue hors du cluster | Normal en `docker run` ; tester une fois déployé |
| Aucune trace dans Tempo | Mauvais endpoint, ou spans non terminés | Vérifier `OTEL_EXPORTER_OTLP_ENDPOINT` (`kubectl describe pod`), et que chaque `span.End()` est appelé |
| Les spans d'étape sont des traces séparées | Le contexte de la requête n'est pas transmis | Démarrer les spans avec `req.Context()` |
| Le service s'appelle `unknown_service` | Nom du service absent de la ressource | `semconv.ServiceName(...)` dans `setupTracing` |

</details>

---

## Construire et déployer

L'image se publie sur le registry GitLab de votre projet. La première fois,
suivez [Déployer votre module](README.md#déployer-votre-module) : jeton,
secret de lecture pour le cluster, activation du module.

Ensuite, à chaque étape, sur `utils-stagiaireXX`, depuis la racine du
repo (`$IMAGE` a été enregistrée à la première fois) :

```bash
docker build --tag $IMAGE:etape2 mon-module/
docker push $IMAGE:etape2

helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.image=$IMAGE:etape2
```

Remplacez `mon-module/` par votre dossier, ou par la version prête à
l'emploi (`fil-rouge/reviews-service/go/2-metriques/` par exemple), et
changez le tag à chaque étape. Après l'exercice CI, c'est le pipeline qui
construit et pousse l'image : il ne reste que le `helm upgrade`.

Vérifications et dépannage du déploiement : [le module fil rouge](README.md#vérifier).
