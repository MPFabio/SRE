from fastapi import FastAPI, HTTPException, Response, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import uvicorn
import os
from pathlib import Path
import logging
import time
import httpx
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional


from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource


class TraceIdFilter(logging.Filter):
    """Ajoute l'identifiant de la trace en cours : Grafana relie ainsi les logs aux traces."""

    def filter(self, record):
        context = trace.get_current_span().get_span_context()
        record.trace_id = format(context.trace_id, "032x") if context.is_valid else "-"
        return True


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - trace_id=%(trace_id)s - %(message)s')
for handler in logging.getLogger().handlers:
    handler.addFilter(TraceIdFilter())
logger = logging.getLogger("api-gateway")


resource = Resource(attributes={
    "service.name": "api-gateway",
    "service.version": "1.0.0",
    "deployment.environment": os.getenv("ENVIRONMENT", "development")
})
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317"),
    insecure=True
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
tracer = trace.get_tracer(__name__)


HTTPXClientInstrumentor().instrument()


REQUEST_COUNT = Counter('gateway_requests_total', 'Total requests', ['method', 'service', 'status'])
REQUEST_LATENCY = Histogram('gateway_request_duration_seconds', 'Request latency', ['method', 'service'])
UPSTREAM_ERRORS = Counter('gateway_upstream_errors_total', 'Upstream service errors', ['service'])
ACTIVE_REQUESTS = Gauge('gateway_active_requests', 'Currently active requests')

http_client = None


@asynccontextmanager
async def lifespan(_app):
    global http_client
    http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=40))
    yield
    await http_client.aclose()


app = FastAPI(title="E-Commerce API Gateway", version="1.0.0", docs_url="/api/docs",
              lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)


SERVICES = {
    "catalog": os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8081"),
    "cart": os.getenv("CART_SERVICE_URL", "http://cart-service:8082"),
    "orders": os.getenv("ORDERS_SERVICE_URL", "http://orders-service:8083"),
    "payment": os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8084"),
    "users": os.getenv("USERS_SERVICE_URL", "http://users-service:8085"),
}

# Module fil rouge, branché seulement si son URL est fournie. Il reste hors de
# SERVICES : sa panne ne doit pas dégrader le /health de la gateway.
OPTIONAL_SERVICES = {
    "reviews": os.getenv("REVIEWS_SERVICE_URL", ""),
}

async def proxy_request(
    service: str,
    path: str,
    method: str = "GET",
    body: dict = None,
    headers: dict = None,
    params: dict = None
):
    base_url = SERVICES.get(service) or OPTIONAL_SERVICES.get(service)
    if not base_url:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

    url = f"{base_url}{path}"
    
    start_time = time.time()
    ACTIVE_REQUESTS.inc()
    counted = False

    def record_failure(status: int):
        UPSTREAM_ERRORS.labels(service=service).inc()
        if not counted:
            REQUEST_COUNT.labels(method=method, service=service, status=status).inc()
            REQUEST_LATENCY.labels(method=method, service=service).observe(time.time() - start_time)

    try:
        request_headers = {}
        if headers:
            for key in ["authorization", "content-type"]:
                if headers.get(key) is not None:
                    request_headers[key] = headers[key]
        
        if method == "GET":
            response = await http_client.get(url, headers=request_headers, params=params, timeout=10.0)
        elif method == "POST":
            response = await http_client.post(url, json=body, headers=request_headers, params=params, timeout=10.0)
        elif method == "PUT":
            response = await http_client.put(url, json=body, headers=request_headers, params=params, timeout=10.0)
        elif method == "DELETE":
            response = await http_client.delete(url, headers=request_headers, params=params, timeout=10.0)
        else:
            raise HTTPException(status_code=405, detail=f"Method not allowed: {method}")
        
        duration = time.time() - start_time
        REQUEST_COUNT.labels(method=method, service=service, status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=method, service=service).observe(duration)
        counted = True

        payload = response.json() if response.content else None


        if response.status_code >= 400:
            UPSTREAM_ERRORS.labels(service=service).inc()
            detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
            logger.warning(
                "Upstream %s returned %s for %s %s: %s",
                service, response.status_code, method, path, detail,
            )
            raise HTTPException(status_code=response.status_code, detail=detail)

        return payload
        
    except HTTPException:


        raise
    except httpx.TimeoutException:
        record_failure(504)
        raise HTTPException(status_code=504, detail=f"Service {service} timeout")
    except httpx.ConnectError:
        record_failure(503)
        raise HTTPException(status_code=503, detail=f"Service {service} unavailable")
    except Exception as e:
        record_failure(500)
        logger.error(f"Error proxying to {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ACTIVE_REQUESTS.dec()

@app.get("/health")
async def health():
    """Health check avec status des services upstream"""
    service_status = {}
    
    for name, url in SERVICES.items():
        try:
            response = await http_client.get(f"{url}/health", timeout=2.0)
            service_status[name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            service_status[name] = "unreachable"
    
    all_healthy = all(s == "healthy" for s in service_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "service": "api-gateway",
        "upstream_services": service_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/ready")
async def ready():
    return {"status": "ready", "service": "api-gateway"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/products")
async def get_products(category: Optional[str] = None, limit: int = 100):
    with tracer.start_as_current_span("gateway_get_products"):
        params = {"limit": limit}
        if category:
            params["category"] = category
        return await proxy_request("catalog", "/api/products", params=params)

@app.get("/api/products/{product_id}")
async def get_product(product_id: int):
    with tracer.start_as_current_span("gateway_get_product"):
        return await proxy_request("catalog", f"/api/products/{product_id}")

@app.get("/api/products/{product_id}/stock")
async def check_stock(product_id: int, quantity: int = 1):
    with tracer.start_as_current_span("gateway_check_stock"):
        return await proxy_request("catalog", f"/api/products/{product_id}/stock", params={"quantity": quantity})

@app.get("/api/features")
async def get_features():
    return {"reviews": bool(OPTIONAL_SERVICES["reviews"])}

@app.get("/api/reviews/{product_id}")
async def get_reviews(product_id: int):
    with tracer.start_as_current_span("gateway_get_reviews"):
        return await proxy_request("reviews", f"/api/reviews/{product_id}")

@app.post("/api/reviews/{product_id}")
async def create_review(product_id: int, request: Request):
    with tracer.start_as_current_span("gateway_create_review"):
        body = await request.json()
        return await proxy_request("reviews", f"/api/reviews/{product_id}", method="POST", body=body)

@app.get("/api/categories")
async def get_categories():
    with tracer.start_as_current_span("gateway_get_categories"):
        return await proxy_request("catalog", "/api/categories")

@app.get("/api/search")
async def search_products(q: str, limit: int = 20):
    with tracer.start_as_current_span("gateway_search"):
        return await proxy_request("catalog", "/api/search", params={"q": q, "limit": limit})


@app.get("/api/cart/{user_id}")
async def get_cart(user_id: str):
    with tracer.start_as_current_span("gateway_get_cart"):
        return await proxy_request("cart", f"/api/cart/{user_id}")

@app.post("/api/cart/{user_id}/items")
async def add_to_cart(user_id: str, request: Request):
    with tracer.start_as_current_span("gateway_add_to_cart"):
        body = await request.json()
        return await proxy_request("cart", f"/api/cart/{user_id}/items", method="POST", body=body)

@app.put("/api/cart/{user_id}/items/{product_id}")
async def update_cart_item(user_id: str, product_id: int, quantity: int):
    with tracer.start_as_current_span("gateway_update_cart"):
        return await proxy_request("cart", f"/api/cart/{user_id}/items/{product_id}", method="PUT", params={"quantity": quantity})

@app.delete("/api/cart/{user_id}/items/{product_id}")
async def remove_cart_item(user_id: str, product_id: int):
    with tracer.start_as_current_span("gateway_remove_cart_item"):
        return await proxy_request("cart", f"/api/cart/{user_id}/items/{product_id}", method="DELETE")

@app.delete("/api/cart/{user_id}")
async def clear_cart(user_id: str):
    with tracer.start_as_current_span("gateway_clear_cart"):
        return await proxy_request("cart", f"/api/cart/{user_id}", method="DELETE")


@app.post("/api/orders")
async def create_order(request: Request):
    with tracer.start_as_current_span("gateway_create_order"):
        body = await request.json()
        return await proxy_request("orders", "/api/orders", method="POST", body=body)

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    with tracer.start_as_current_span("gateway_get_order"):
        return await proxy_request("orders", f"/api/orders/{order_id}")

@app.get("/api/orders/user/{user_id}")
async def get_user_orders(user_id: str, limit: int = 50, offset: int = 0):
    with tracer.start_as_current_span("gateway_get_user_orders"):
        return await proxy_request("orders", f"/api/orders/user/{user_id}",
                                   params={"limit": limit, "offset": offset})

@app.post("/api/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    with tracer.start_as_current_span("gateway_cancel_order"):
        return await proxy_request("orders", f"/api/orders/{order_id}/cancel", method="POST")


@app.get("/api/circuit-breaker")
async def get_circuit_breaker():
    with tracer.start_as_current_span("gateway_get_circuit_breaker"):
        return await proxy_request("payment", "/api/circuit-breaker")

@app.post("/api/circuit-breaker/reset")
async def reset_circuit_breaker():
    with tracer.start_as_current_span("gateway_reset_circuit_breaker"):
        return await proxy_request("payment", "/api/circuit-breaker/reset", method="POST")

@app.post("/api/payments")
async def create_payment(request: Request):
    with tracer.start_as_current_span("gateway_create_payment"):
        body = await request.json()
        return await proxy_request("payment", "/api/payments", method="POST", body=body)

@app.get("/api/payments/{payment_id}")
async def get_payment(payment_id: str):
    with tracer.start_as_current_span("gateway_get_payment"):
        return await proxy_request("payment", f"/api/payments/{payment_id}")


@app.post("/api/users/register")
async def register_user(request: Request):
    with tracer.start_as_current_span("gateway_register"):
        body = await request.json()
        return await proxy_request("users", "/api/users/register", method="POST", body=body)

@app.post("/api/users/login")
async def login_user(request: Request):
    with tracer.start_as_current_span("gateway_login"):
        body = await request.json()
        return await proxy_request("users", "/api/users/login", method="POST", body=body)

@app.post("/api/users/logout")
async def logout_user(authorization: str = Header(None)):
    with tracer.start_as_current_span("gateway_logout"):
        return await proxy_request("users", "/api/users/logout", method="POST", headers={"authorization": authorization})

@app.get("/api/users/me")
async def get_current_user(authorization: str = Header(None)):
    with tracer.start_as_current_span("gateway_get_current_user"):
        return await proxy_request("users", "/api/users/me", headers={"authorization": authorization})

@app.put("/api/users/me")
async def update_current_user(request: Request, authorization: str = Header(None)):
    with tracer.start_as_current_span("gateway_update_user"):
        body = await request.json()
        return await proxy_request("users", "/api/users/me", method="PUT", body=body, headers={"authorization": authorization})

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, authorization: str = Header(None)):
    with tracer.start_as_current_span("gateway_get_user"):
        return await proxy_request("users", f"/api/users/{user_id}",
                                   headers={"authorization": authorization})

@app.get("/api/users")
async def list_users(authorization: str = Header(None)):
    with tracer.start_as_current_span("gateway_list_users"):
        return await proxy_request("users", "/api/users",
                                   headers={"authorization": authorization})


STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting API Gateway on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
