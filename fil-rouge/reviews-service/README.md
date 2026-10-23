# reviews-service : exemple de module fil rouge

Service d'avis produits, écrit deux fois avec le même comportement :
en Python (FastAPI) et en Go (bibliothèque standard). C'est un exemple
parmi d'autres : votre module peut porter sur un autre métier et être
écrit autrement.

Chaque langage est découpé en trois étapes, qui se construisent et se
déploient chacune seule :

| Étape | Go | Python |
|---|---|---|
| 1. API et `/health` | [`go/1-base`](go/1-base/) | [`python/1-base`](python/1-base/) |
| 2. Métriques business | [`go/2-metriques`](go/2-metriques/) | [`python/2-metriques`](python/2-metriques/) |
| 3. Traces OpenTelemetry | [`go/3-traces`](go/3-traces/) | [`python/3-traces`](python/3-traces/) |

Les guides [module-go.md](../module-go.md) et
[module-python.md](../module-python.md) expliquent chaque étape.

## API

| Route | Rôle |
|---|---|
| `GET /health` | Santé du service |
| `GET /metrics` | Métriques Prometheus |
| `GET /api/reviews/{product_id}` | Avis d'un produit, nombre et note moyenne |
| `POST /api/reviews/{product_id}` | Publier un avis : `{"rating": 1 à 5, "comment": "..."}` |

Un avis contenant un mot interdit est refusé (422) par la modération.

## Métriques business

| Métrique | Sens |
|---|---|
| `reviews_created_total{rating}` | Avis publiés, par note |
| `reviews_rejected_total{reason}` | Avis refusés, par motif |
| `reviews_average_rating{product_id}` | Note moyenne par produit |

S'y ajoutent `http_requests_total` et `http_request_duration_seconds` pour
le trafic et la latence.

## Traces

Chaque publication d'avis produit une trace avec deux étapes :
`moderate_review` et `store_review`.

## Construire et tester

```bash
docker build --tag reviews-service:1.0 fil-rouge/reviews-service/go/3-traces
docker run --rm --publish 8086:8086 reviews-service:1.0
```

Pour une autre étape ou la version Python, changez le dossier. Dans un
autre terminal :

```bash
curl --request POST localhost:8086/api/reviews/3 \
    --header 'Content-Type: application/json' \
    --data '{"rating": 4, "comment": "super casque"}'
curl localhost:8086/api/reviews/3
curl localhost:8086/metrics
```

Hors du cluster, l'envoi des traces échoue (pas d'`otel-collector`) : les
messages d'erreur correspondants sont normaux.

Pour le déployer dans le lab, voir [le module fil rouge](../README.md).
