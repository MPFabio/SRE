# Écrire votre module en Python (FastAPI), pas à pas

Ce guide construit un module CapShop en trois étapes. Chaque étape se
déploie et fonctionne seule :

| Étape | Ce que le module sait faire | Version prête à l'emploi |
|---|---|---|
| 1 | Répondre à une API et à `/health` | [`reviews-service/python/1-base`](reviews-service/python/1-base/) |
| 2 | Exposer des métriques business | [`reviews-service/python/2-metriques`](reviews-service/python/2-metriques/) |
| 3 | Envoyer des traces OpenTelemetry | [`reviews-service/python/3-traces`](reviews-service/python/3-traces/) |

L'exemple suivi est un service d'avis produits, `reviews-service`. Vous
pouvez choisir un autre métier, ou partir d'un programme FastAPI que vous
avez déjà : la démarche reste la même.

> **Vous êtes en retard ou bloqué ?** Construisez la version prête à
> l'emploi de l'étape où vous en êtes (section « Construire et déployer »)
> et continuez le parcours. Vous reprendrez votre propre code plus tard.

---

## Étape 1 : une API et un endpoint /health

### Ce qu'il faut écrire

Un dossier avec trois fichiers : `main.py`, `requirements.txt` et
`Dockerfile`.

1. **`requirements.txt`** :

   ```
   fastapi==0.141.1
   uvicorn==0.53.0
   pydantic==2.13.5
   ```

2. **`main.py`** déclare trois routes et démarre sur le port lu dans `PORT` :

   | Route | Réponse |
   |---|---|
   | `GET /health` | `{"status": "ok"}`, code 200 |
   | `GET /api/reviews/{product_id}` | Les avis du produit et leur note moyenne |
   | `POST /api/reviews/{product_id}` | Enregistre un avis `{"rating": 1-5, "comment": "..."}`, code 201 |

   Un modèle Pydantic valide l'avis : une note hors de 1 à 5 est refusée
   automatiquement (422).

   ```python
   class Review(BaseModel):
       rating: int = Field(ge=1, le=5)
       comment: str = Field(default="", max_length=500)

   @app.post("/api/reviews/{product_id}", status_code=201)
   def create_review(product_id: int, review: Review):
       ...
   ```

   Les avis sont gardés en mémoire, dans un dictionnaire.

3. **Les logs** passent par le module `logging`, sur stdout :
   Promtail les envoie dans Loki sans autre réglage.

4. **`Dockerfile`** :

   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir --requirement requirements.txt
   COPY main.py .
   USER 10001
   EXPOSE 8086
   CMD ["python", "main.py"]
   ```

<details>
<summary>Code complet de l'étape 1</summary>

Voir [`reviews-service/python/1-base/main.py`](reviews-service/python/1-base/main.py).
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

FastAPI génère aussi une documentation interactive sur
`http://localhost:8086/docs`.

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ModuleNotFoundError` au démarrage | Bibliothèque absente de `requirements.txt` | L'ajouter, puis reconstruire l'image |
| Le container démarre mais `curl` échoue | uvicorn écoute sur `127.0.0.1` | `uvicorn.run(app, host="0.0.0.0", port=PORT)` |
| 422 sur un avis correct | Corps JSON mal formé, ou `Content-Type` manquant | `--header 'Content-Type: application/json'` |
| Le container s'arrête aussitôt | Erreur dans `main.py` | `docker run` sans `--rm` puis `docker logs <id>` |

</details>

---

## Étape 2 : des métriques business

### Ce qu'il faut ajouter

1. **`prometheus-client==0.26.0`** dans `requirements.txt`.

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

   ```python
   REVIEWS = Counter("reviews_created_total", "Avis publiés", ["rating"])
   ...
   REVIEWS.labels(str(review.rating)).inc()
   ```

4. **Mesurer le trafic** de chaque route dans un middleware : un counter
   de requêtes et un histogram de durée.

5. **Exposer `/metrics`** :

   ```python
   @app.get("/metrics")
   def metrics():
       return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
   ```

   Préférez cette route à `app.mount("/metrics", make_asgi_app())` : le
   montage répond par une redirection vers `/metrics/`.

> Attention aux labels : `product_id` convient pour 15 produits, pas pour
> des millions. Chaque valeur de label crée une série dans Prometheus.

<details>
<summary>Code complet de l'étape 2</summary>

Voir [`reviews-service/python/2-metriques/main.py`](reviews-service/python/2-metriques/main.py).

</details>

### Vérifier

En local : `curl localhost:8086/metrics | grep reviews_` après avoir publié
un avis. Dans le lab, après déploiement, la target passe `up` dans
http://localhost:9090/targets et la requête suivante répond :

```promql
sum by (rating) (reviews_created_total)
```

<details>
<summary>Ça bloque ?</summary>

| Symptôme | Cause probable | Solution |
|---|---|---|
| La métrique n'apparaît pas dans `/metrics` | Une métrique à labels n'apparaît qu'après sa première valeur | Publier un avis, puis relire `/metrics` |
| `Duplicated timeseries in CollectorRegistry` | Deux métriques portent le même nom | Renommer l'une d'elles |
| `/metrics` répond 307 | Métriques exposées par `app.mount` | Utiliser une route `@app.get("/metrics")` |
| Target `down` ou absente dans Prometheus | Image pas à jour, ou configuration pas rechargée | `kubectl logs deploy/<nom>`, puis `curl --request POST http://localhost:9090/-/reload` |

</details>

---

## Étape 3 : des traces OpenTelemetry

### Ce qu'il faut ajouter

1. Dans `requirements.txt` :

   ```
   opentelemetry-api==1.44.0
   opentelemetry-sdk==1.44.0
   opentelemetry-instrumentation-fastapi==0.65b0
   opentelemetry-exporter-otlp-proto-grpc==1.44.0
   ```

2. **Configurer l'envoi des traces** au démarrage, vers le collecteur du
   lab (variable `OTEL_EXPORTER_OTLP_ENDPOINT`, gRPC sans TLS), avec le nom
   du service : c'est lui qui apparaîtra dans Tempo.

   ```python
   trace.set_tracer_provider(TracerProvider(resource=Resource({"service.name": SERVICE_NAME})))
   trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
       endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317"), insecure=True)))
   ```

3. **Tracer chaque requête** automatiquement :

   ```python
   FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
   ```

4. **Découper le traitement en étapes** avec des spans, pour voir où passe
   le temps :

   ```python
   with tracer.start_as_current_span("moderate_review"):
       ...
   ```

5. **Suivre la requête dans les autres services.** L'exemple vérifie que
   le produit existe en appelant `catalog-service` (variable
   `CATALOG_SERVICE_URL`) avec `httpx`. Instrumenté, le client ajoute le
   contexte de trace aux headers, et la trace continue dans le catalogue.
   Ajoutez `httpx==0.28.1` et `opentelemetry-instrumentation-httpx==0.65b0`
   à `requirements.txt`, puis :

   ```python
   HTTPXClientInstrumentor().instrument()
   ...
   with tracer.start_as_current_span("verify_product"):
       response = httpx.get(f"{CATALOG_SERVICE_URL}/api/products/{product_id}", timeout=5.0)
   ```

<details>
<summary>Code complet de l'étape 3</summary>

Voir [`reviews-service/python/3-traces/main.py`](reviews-service/python/3-traces/main.py).

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
| Erreurs d'export (`StatusCode.UNAVAILABLE`) en local | Pas de collecteur hors du cluster | Normal en `docker run` ; tester dans le lab |
| La trace s'arrête à votre service, sans `catalog-service` | Client HTTP non instrumenté | `HTTPXClientInstrumentor().instrument()` avant les appels |
| Tous les avis sont refusés en 503 en local | Pas de catalogue hors du cluster | Normal en `docker run` ; tester dans le lab |
| Aucune trace dans Tempo | Mauvais endpoint | Vérifier `OTEL_EXPORTER_OTLP_ENDPOINT` avec `kubectl describe pod -l app=<nom>` |
| Les traces sont pleines de `/health` | Probes Kubernetes tracées | `excluded_urls="health,metrics"` |
| Le service s'appelle `unknown_service` | Nom absent de la ressource | `Resource({"service.name": ...})` |

</details>

---

## Construire et déployer

À chaque étape, sur `utils-stagiaireXX`, depuis la racine du repo :

```bash
export REGISTRY=docker-push.reskilling.internal/$STAGIAIRE
docker build --tag $REGISTRY/reviews-service:etape1 mon-module/
docker push $REGISTRY/reviews-service:etape1

helm upgrade lab helm/reskilling-lab --namespace $STAGIAIRE --reuse-values \
    --set learnerService.enabled=true \
    --set learnerService.name=reviews-service \
    --set learnerService.image=docker.reskilling.internal/$STAGIAIRE/reviews-service:etape1
```

Remplacez `mon-module/` par votre dossier, ou par la version prête à
l'emploi (`fil-rouge/reviews-service/python/1-base/`), et changez le tag à
chaque étape (`etape2`, `etape3`). Quand le pipeline GitLab construira
l'image (exercice CI), seule la valeur de `learnerService.image` changera.

Vérifications et dépannage du déploiement : [le module fil rouge](README.md#vérifier).
