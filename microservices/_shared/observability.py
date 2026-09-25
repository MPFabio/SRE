import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_telemetry(service_name: str, version: str = "1.0.0"):
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger(service_name)

    resource = Resource(attributes={
        "service.name": service_name,
        "service.version": version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    trace.set_tracer_provider(TracerProvider(resource=resource))
    exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317"),
        insecure=True,
    )
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))


    HTTPXClientInstrumentor().instrument()

    return logger, trace.get_tracer(service_name)


def setup_app(app: FastAPI):
    origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    FastAPIInstrumentor.instrument_app(app)
    return app

def register_metrics_middleware(app: FastAPI, request_count, request_latency):

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        route = request.scope.get("route")
        endpoint = getattr(route, "path", None) or "unmatched"

        request_count.labels(method=request.method, endpoint=endpoint,
                             status=response.status_code).inc()
        request_latency.labels(method=request.method,
                               endpoint=endpoint).observe(duration)
        return response

    return app
