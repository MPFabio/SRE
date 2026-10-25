from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from prometheus_client import Counter, Histogram
import uvicorn
from contextlib import asynccontextmanager
import asyncio
import os


from _shared import (setup_telemetry, setup_app, ChaosController,
                     register_metrics_middleware,
                     register_ops_endpoints, Database)

logger, tracer = setup_telemetry("catalog-service")


REQUEST_COUNT = Counter('catalog_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('catalog_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
PRODUCTS_SERVED = Counter('catalog_products_served_total', 'Products served')
STOCK_CHECKS = Counter('catalog_stock_checks_total', 'Stock availability checks', ['result'])
RESTOCKS = Counter('catalog_restocks_total', 'Products restocked')

RESTOCK_INTERVAL = int(os.getenv("RESTOCK_INTERVAL", "60"))
RESTOCK_THRESHOLD = int(os.getenv("RESTOCK_THRESHOLD", "5"))
RESTOCK_QUANTITY = int(os.getenv("RESTOCK_QUANTITY", "30"))


async def restock_loop():
    while True:
        await asyncio.sleep(RESTOCK_INTERVAL)
        try:
            result = await db.execute(
                "UPDATE catalog.products SET stock = stock + $1 WHERE stock < $2",
                RESTOCK_QUANTITY, RESTOCK_THRESHOLD, operation="restock")
            restocked = int(result.split()[-1])
            if restocked:
                RESTOCKS.inc(restocked)
                logger.info("Restocked %d product(s)", restocked)
        except Exception as exc:
            logger.warning("Restock failed: %s", exc)


@asynccontextmanager
async def lifespan(_app):
    await db.connect()
    restock = asyncio.create_task(restock_loop())
    yield
    restock.cancel()
    await db.disconnect()

app = FastAPI(title="Catalog Service", version="1.0.0", lifespan=lifespan)

setup_app(app)


class Product(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    stock: int
    image_url: Optional[str] = None
    brand: Optional[str] = None

    compare_at_price: Optional[float] = None
    rating: Optional[float] = None
    rating_count: int = 0

class Category(BaseModel):
    id: int
    name: str
    description: str


chaos = ChaosController("catalog-service", logger)
db = Database("catalog-service", logger)


register_metrics_middleware(app, REQUEST_COUNT, REQUEST_LATENCY)

register_ops_endpoints(app, "catalog-service", chaos, db=db)

@app.get("/api/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, limit: int = 100):
    """Liste tous les produits avec filtrage optionnel par catégorie"""
    with tracer.start_as_current_span("get_products") as span:
        await chaos.inject()

        span.set_attribute("category_filter", category or "all")
        span.set_attribute("limit", limit)

        if category:
            rows = await db.fetch(
                "SELECT * FROM catalog.products WHERE category = $1 ORDER BY id LIMIT $2",
                category, limit, operation="get_products")
        else:
            rows = await db.fetch(
                "SELECT * FROM catalog.products ORDER BY id LIMIT $1",
                limit, operation="get_products")

        result = [Product(**dict(r)) for r in rows]
        PRODUCTS_SERVED.inc(len(result))

        logger.info(f"Returned {len(result)} products (category={category})")
        return result

@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """Récupère un produit par son ID"""
    with tracer.start_as_current_span("get_product") as span:
        await chaos.inject()

        span.set_attribute("product_id", product_id)

        row = await db.fetchrow(
            "SELECT * FROM catalog.products WHERE id = $1",
            product_id, operation="get_product")
        if row is None:
            logger.warning(f"Product {product_id} not found")
            raise HTTPException(status_code=404, detail="Product not found")

        PRODUCTS_SERVED.inc()
        product = Product(**dict(row))
        logger.info(f"Returned product {product_id}: {product.name}")
        return product

@app.get("/api/products/{product_id}/stock")
async def check_stock(product_id: int, quantity: int = 1):
    """Vérifie la disponibilité du stock"""
    with tracer.start_as_current_span("check_stock") as span:
        await chaos.inject()

        span.set_attribute("product_id", product_id)
        span.set_attribute("requested_quantity", quantity)

        row = await db.fetchrow(
            "SELECT stock FROM catalog.products WHERE id = $1",
            product_id, operation="check_stock")
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")

        stock = row["stock"]
        available = stock >= quantity
        STOCK_CHECKS.labels(result="available" if available else "unavailable").inc()

        logger.info(f"Stock check for product {product_id}: {stock} available, {quantity} requested")
        return {
            "product_id": product_id,
            "available": available,
            "stock": stock,
            "requested": quantity
        }

@app.post("/api/products/{product_id}/reserve")
async def reserve_stock(product_id: int, quantity: int):
    """Réserve du stock pour une commande"""
    with tracer.start_as_current_span("reserve_stock") as span:
        await chaos.inject()

        span.set_attribute("product_id", product_id)
        span.set_attribute("quantity", quantity)


        row = await db.fetchrow(
            "UPDATE catalog.products SET stock = stock - $2 "
            "WHERE id = $1 AND stock >= $2 RETURNING stock",
            product_id, quantity, operation="reserve_stock")

        if row is not None:
            logger.info(f"Reserved {quantity} units of product {product_id}")
            return {"success": True, "remaining_stock": row["stock"]}

        exists = await db.fetchrow(
            "SELECT 1 FROM catalog.products WHERE id = $1",
            product_id, operation="reserve_stock")
        if exists is None:
            raise HTTPException(status_code=404, detail="Product not found")

        logger.warning(f"Insufficient stock for product {product_id}")
        raise HTTPException(status_code=400, detail="Insufficient stock")

@app.get("/api/categories", response_model=List[Category])
async def get_categories():
    """Liste toutes les catégories"""
    with tracer.start_as_current_span("get_categories"):
        await chaos.inject()
        rows = await db.fetch(
            "SELECT id, name, description FROM catalog.categories ORDER BY id",
            operation="get_categories")
        logger.info(f"Returned {len(rows)} categories")
        return [Category(**dict(r)) for r in rows]

@app.get("/api/search")
async def search_products(q: str, limit: int = 20):
    """Recherche de produits"""
    with tracer.start_as_current_span("search_products") as span:
        await chaos.inject()

        span.set_attribute("query", q)

        rows = await db.fetch(
            "SELECT * FROM catalog.products "
            "WHERE name ILIKE $1 OR description ILIKE $1 OR brand ILIKE $1 "
            "ORDER BY id LIMIT $2",
            "%" + q + "%", limit, operation="search_products")
        logger.info(f"Search '{q}' returned {len(rows)} results")
        return [Product(**dict(r)) for r in rows]

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    logger.info(f"Starting Catalog Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
