from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from prometheus_client import Counter, Histogram, Gauge
import uvicorn
import os
import json
from datetime import datetime
import redis.asyncio as redis
import httpx
from contextlib import asynccontextmanager

from _shared import (setup_telemetry, setup_app, ChaosController,
                     register_metrics_middleware, register_ops_endpoints)

logger, tracer = setup_telemetry("cart-service")


REQUEST_COUNT = Counter('cart_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('cart_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
CART_ITEMS = Gauge('cart_items_total', 'Total items across all carts')
CART_VALUE = Gauge('cart_total_value', 'Total value across all carts')
CART_OPERATIONS = Counter('cart_operations_total', 'Cart operations', ['operation'])

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = None
http_client = None


@asynccontextmanager
async def lifespan(_app):
    global redis_client, http_client
    http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20))
    # Le client se reconnecte seul : Redis peut démarrer après le service.
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("Connected to Redis")
    except redis.RedisError as exc:
        logger.warning(f"Redis not available yet, will retry on each request: {exc}")
    yield
    await http_client.aclose()
    await redis_client.aclose()


app = FastAPI(title="Cart Service", version="1.0.0", lifespan=lifespan)

setup_app(app)


@app.exception_handler(redis.RedisError)
async def redis_unavailable(_request: Request, exc: redis.RedisError):
    logger.error(f"Redis unavailable: {exc}")
    return JSONResponse({"detail": "Cart storage unavailable"}, status_code=503)


class RedisHealth:
    async def healthy(self) -> bool:
        try:
            return await redis_client.ping()
        except redis.RedisError:
            return False


CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8081")

chaos = ChaosController("cart-service", logger)


class CartItem(BaseModel):
    product_id: int
    quantity: int
    price: float
    name: str

class Cart(BaseModel):
    user_id: str
    items: List[CartItem] = []
    total: float = 0.0
    created_at: str = ""
    updated_at: str = ""

class AddItemRequest(BaseModel):
    product_id: int
    quantity: int = 1


async def get_cart(user_id: str) -> Cart:
    cart_key = f"cart:{user_id}"
    
    cart_data = await redis_client.get(cart_key)
    if cart_data:
        return Cart(**json.loads(cart_data))
    

    return Cart(
        user_id=user_id,
        items=[],
        total=0.0,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )

async def save_cart(cart: Cart):
    cart_key = f"cart:{cart.user_id}"
    cart.updated_at = datetime.now().isoformat()
    cart_data = cart.model_dump_json()
    
    await redis_client.set(cart_key, cart_data, ex=86400)

async def delete_cart(user_id: str):
    cart_key = f"cart:{user_id}"
    
    await redis_client.delete(cart_key)

async def refresh_cart_gauges():
    items = value = 0
    async for key in redis_client.scan_iter(match="cart:*", count=100):
        raw = await redis_client.get(key)
        if not raw:
            continue
        data = json.loads(raw)
        items += sum(i["quantity"] for i in data.get("items", []))
        value += data.get("total", 0.0)
    CART_ITEMS.set(items)
    CART_VALUE.set(value)


async def get_product_from_catalog(product_id: int):
    """Renvoie le produit, None s'il n'existe pas ; 503 si le catalogue est injoignable."""
    try:
        response = await http_client.get(
            f"{CATALOG_SERVICE_URL}/api/products/{product_id}", timeout=5.0)
    except httpx.HTTPError as e:
        logger.error(f"Error calling catalog service: {e}")
        raise HTTPException(status_code=503, detail="Catalog unavailable")
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        logger.error(f"Catalog service returned {response.status_code} for product {product_id}")
        raise HTTPException(status_code=503, detail="Catalog unavailable")
    return response.json()

register_metrics_middleware(app, REQUEST_COUNT, REQUEST_LATENCY)

register_ops_endpoints(app, "cart-service", chaos, db=RedisHealth())

@app.get("/api/cart/{user_id}", response_model=Cart)
async def get_user_cart(user_id: str):
    """Récupère le panier d'un utilisateur"""
    with tracer.start_as_current_span("get_cart") as span:
        await chaos.inject()
        
        span.set_attribute("user_id", user_id)
        
        cart = await get_cart(user_id)
        logger.info(f"Retrieved cart for user {user_id}: {len(cart.items)} items, total: {cart.total}")
        
        CART_OPERATIONS.labels(operation="get").inc()
        return cart

@app.post("/api/cart/{user_id}/items", response_model=Cart)
async def add_item_to_cart(user_id: str, item: AddItemRequest):
    """Ajoute un produit au panier"""
    with tracer.start_as_current_span("add_to_cart") as span:
        await chaos.inject()
        
        span.set_attribute("user_id", user_id)
        span.set_attribute("product_id", item.product_id)
        span.set_attribute("quantity", item.quantity)
        

        product = await get_product_from_catalog(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        cart = await get_cart(user_id)
        

        existing_item = None
        for cart_item in cart.items:
            if cart_item.product_id == item.product_id:
                existing_item = cart_item
                break
        
        if existing_item:
            existing_item.quantity += item.quantity
        else:
            cart.items.append(CartItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price=product["price"],
                name=product["name"]
            ))
        

        cart.total = sum(i.price * i.quantity for i in cart.items)
        
        await save_cart(cart)
        
        logger.info(f"Added product {item.product_id} to cart for user {user_id}")
        CART_OPERATIONS.labels(operation="add_item").inc()
        await refresh_cart_gauges()
        
        return cart

@app.put("/api/cart/{user_id}/items/{product_id}")
async def update_cart_item(user_id: str, product_id: int, quantity: int):
    """Met à jour la quantité d'un produit dans le panier"""
    with tracer.start_as_current_span("update_cart_item") as span:
        await chaos.inject()
        
        span.set_attribute("user_id", user_id)
        span.set_attribute("product_id", product_id)
        span.set_attribute("new_quantity", quantity)
        
        cart = await get_cart(user_id)
        
        for item in cart.items:
            if item.product_id == product_id:
                old_quantity = item.quantity
                item.quantity = quantity
                cart.total = sum(i.price * i.quantity for i in cart.items)
                await save_cart(cart)
                
                logger.info(f"Updated product {product_id} quantity from {old_quantity} to {quantity} for user {user_id}")
                CART_OPERATIONS.labels(operation="update_item").inc()
                await refresh_cart_gauges()
                
                return cart
        
        raise HTTPException(status_code=404, detail="Item not in cart")

@app.delete("/api/cart/{user_id}/items/{product_id}")
async def remove_cart_item(user_id: str, product_id: int):
    """Supprime un produit du panier"""
    with tracer.start_as_current_span("remove_cart_item") as span:
        await chaos.inject()
        
        span.set_attribute("user_id", user_id)
        span.set_attribute("product_id", product_id)
        
        cart = await get_cart(user_id)
        
        for i, item in enumerate(cart.items):
            if item.product_id == product_id:
                removed_quantity = item.quantity
                cart.items.pop(i)
                cart.total = sum(i.price * i.quantity for i in cart.items)
                await save_cart(cart)
                
                logger.info(f"Removed {removed_quantity}x product {product_id} from cart for user {user_id}")
                CART_OPERATIONS.labels(operation="remove_item").inc()
                await refresh_cart_gauges()
                
                return cart
        
        raise HTTPException(status_code=404, detail="Item not in cart")

@app.delete("/api/cart/{user_id}")
async def clear_cart(user_id: str):
    """Vide le panier"""
    with tracer.start_as_current_span("clear_cart") as span:
        await chaos.inject()
        
        span.set_attribute("user_id", user_id)
        
        cart = await get_cart(user_id)
        total_items = sum(i.quantity for i in cart.items)
        
        await delete_cart(user_id)
        
        logger.info(f"Cleared cart for user {user_id} ({total_items} items)")
        CART_OPERATIONS.labels(operation="clear").inc()
        await refresh_cart_gauges()
        
        return {"message": "Cart cleared", "user_id": user_id}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8082"))
    logger.info(f"Starting Cart Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
