"""Avis produits CapShop, étape 3 : traces OpenTelemetry."""
import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "reviews-service")
PORT = int(os.getenv("PORT", "8086"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(SERVICE_NAME)

trace.set_tracer_provider(TracerProvider(resource=Resource({"service.name": SERVICE_NAME})))
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317"), insecure=True)))
tracer = trace.get_tracer(SERVICE_NAME)

REQUESTS = Counter("http_requests_total", "Requêtes HTTP", ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Durée des requêtes HTTP", ["method", "route"])
REVIEWS = Counter("reviews_created_total", "Avis publiés", ["rating"])
REJECTED = Counter("reviews_rejected_total", "Avis refusés", ["reason"])
AVERAGE = Gauge("reviews_average_rating", "Note moyenne par produit", ["product_id"])

FORBIDDEN_WORDS = {"arnaque", "nul"}

app = FastAPI(title=SERVICE_NAME)
FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")

reviews: dict[int, list[dict]] = {}


class Review(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


@app.middleware("http")
async def measure(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", "unmatched")
    if route not in ("/health", "/metrics"):
        REQUESTS.labels(request.method, route, response.status_code).inc()
        LATENCY.labels(request.method, route).observe(time.time() - start)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/reviews/{product_id}")
def list_reviews(product_id: int):
    items = reviews.get(product_id, [])
    average = round(sum(r["rating"] for r in items) / len(items), 2) if items else None
    return {"product_id": product_id, "count": len(items), "average": average, "reviews": items}


@app.post("/api/reviews/{product_id}", status_code=201)
def create_review(product_id: int, review: Review):
    with tracer.start_as_current_span("moderate_review") as span:
        span.set_attribute("product_id", product_id)
        if FORBIDDEN_WORDS & set(review.comment.lower().split()):
            REJECTED.labels("moderation").inc()
            logger.warning("Avis refusé pour le produit %d : modération", product_id)
            raise HTTPException(status_code=422, detail="Avis refusé par la modération")

    with tracer.start_as_current_span("store_review"):
        items = reviews.setdefault(product_id, [])
        items.append(review.model_dump())
        AVERAGE.labels(str(product_id)).set(sum(r["rating"] for r in items) / len(items))

    REVIEWS.labels(str(review.rating)).inc()
    logger.info("Avis %d/5 publié pour le produit %d", review.rating, product_id)
    return review


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
