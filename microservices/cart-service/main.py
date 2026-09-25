from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from prometheus_client import Counter, Histogram, Gauge
import uvicorn
import os
import time
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
    client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await client.ping()
        redis_client = client
        logger.info("Connected to Redis")
    except Exception as exc:
        await client.aclose()
        redis_client = None
        logger.warning(f"Redis not available, using in-memory storage: {exc}")
    yield
    await http_client.aclose()
    if redis_client:
        await redis_client.aclose()


app = FastAPI(title="Cart Service", version="1.0.0", lifespan=lifespan)

setup_app(app)


memory_carts: Dict[str, dict] = {}


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
    
    if redis_client:
        cart_data = await redis_client.get(cart_key)
        if cart_data:
            return Cart(**json.loads(cart_data))
    else:
        if user_id in memory_carts:
            return Cart(**memory_carts[user_id])
    

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
    
    if redis_client:
        await redis_client.setex(cart_key, 86400, cart_data)
    else:
        memory_carts[cart.user_id] = json.loads(cart_data)

async def delete_cart(user_id: str):
    cart_key = f"cart:{user_id}"
    
    if redis_client:
        await redis_client.delete(cart_key)
    else:
        memory_carts.pop(user_id, None)

async def refresh_cart_gauges():
    items = value = 0
    if redis_client:
        async for key in redis_client.scan_iter(match="cart:*", count=100):
            raw = await redis_client.get(key)
            if not raw:
                continue
            data = json.loads(raw)
            items += sum(i["quantity"] for i in data.get("items", []))
            value += data.get("total", 0.0)
    else:
        for data in memory_carts.values():
            items += sum(i["quantity"] for i in data.get("items", []))
            value += data.get("total", 0.0)
    CART_ITEMS.set(items)
    CART_VALUE.set(value)


async def get_product_from_catalog(product_id: int):
    try:
        response = await http_client.get(
            f"{CATALOG_SERVICE_URL}/api/products/{product_id}", timeout=5.0)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error calling catalog service: {e}")
        return None

register_metrics_middleware(app, REQUEST_COUNT, REQUEST_LATENCY)

register_ops_endpoints(app, "cart-service", chaos)

@app.get("/api/cart/{user_id}", response_model=Cart)
async def get_user_cart(user_id: str):
    """Récupère le panier d'un utilisateur"""
    with tracer.start_as_current_span("get_cart") as span:
        chaos.inject()
        
        span.set_attribute("user_id", user_id)
        
        cart = await get_cart(user_id)
        logger.info(f"Retrieved cart for user {user_id}: {len(cart.items)} items, total: {cart.total}")
        
        CART_OPERATIONS.labels(operation="get").inc()
        return cart

@app.post("/api/cart/{user_id}/items", response_model=Cart)
async def add_item_to_cart(user_id: str, item: AddItemRequest):
    """Ajoute un produit au panier"""
    with tracer.start_as_current_span("add_to_cart") as span:
        chaos.inject()
        
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
        chaos.inject()
        
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
        chaos.inject()
        
        span.set_attribute("user_id", user_id)
        span.set_attribute("product_id", product_id)
        
        cart = await get_cart(user_id)
        
        for i, item in enumerate(cart.items):
            if item.product_id == product_id:
                removed_quantity = item.quantity
                cart.items.pop(i)
                cart.total = sum(i.price * i.quantity for i in cart.items)
                await save_cart(cart)
                
                logger.info(f"Removed product {product_id} from cart for user {user_id}")
                CART_OPERATIONS.labels(operation="remove_item").inc()
                await refresh_cart_gauges()
                
                return cart
        
        raise HTTPException(status_code=404, detail="Item not in cart")

@app.delete("/api/cart/{user_id}")
async def clear_cart(user_id: str):
    """Vide le panier"""
    with tracer.start_as_current_span("clear_cart") as span:
        chaos.inject()
        
        span.set_attribute("user_id", user_id)
        
        cart = await get_cart(user_id)
        total_items = sum(i.quantity for i in cart.items)
        
        await delete_cart(user_id)
        
        logger.info(f"Cleared cart for user {user_id}")
        CART_OPERATIONS.labels(operation="clear").inc()
        await refresh_cart_gauges()
        
        return {"message": "Cart cleared", "user_id": user_id}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8082"))
    logger.info(f"Starting Cart Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
