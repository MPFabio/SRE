from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from prometheus_client import Counter, Histogram, Gauge
import uvicorn
from contextlib import asynccontextmanager
import json
import os
import time
from datetime import datetime
from enum import Enum
import httpx


from _shared import (setup_telemetry, setup_app, ChaosController,
                     register_metrics_middleware,
                     register_ops_endpoints, Database)

logger, tracer = setup_telemetry("orders-service")


REQUEST_COUNT = Counter('orders_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('orders_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
ORDERS_CREATED = Counter('orders_created_total', 'Total orders created')
ORDERS_BY_STATUS = Gauge('orders_by_status', 'Orders by status', ['status'])
ORDER_VALUE = Histogram('order_value_dollars', 'Order value distribution', buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000])
PAYMENT_CALLS = Counter('orders_payment_calls_total', 'Calls to payment service', ['result'])

@asynccontextmanager
async def lifespan(_app):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(title="Orders Service", version="1.0.0", lifespan=lifespan)

setup_app(app)


CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://cart-service:8082")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8084")
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8081")

chaos = ChaosController("orders-service", logger)
db = Database("orders-service", logger)


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_FAILED = "payment_failed"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float
    name: str

class ShippingAddress(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str

class CreateOrderRequest(BaseModel):
    user_id: str
    shipping_address: ShippingAddress

class Order(BaseModel):
    id: str
    user_id: str
    items: List[OrderItem]
    total: float
    status: OrderStatus
    shipping_address: ShippingAddress
    payment_id: Optional[str] = None
    created_at: str
    updated_at: str


async def generate_order_id() -> str:
    seq = await db.fetchrow(
        "SELECT nextval('orders.order_seq') AS n", operation="order_id")
    return f"ORD-{datetime.now().strftime('%Y%m%d')}-{seq['n']:05d}"

async def refresh_order_gauges():
    """Recompte les commandes par statut: la jauge etait declaree sans etre alimentee."""
    try:
        rows = await db.fetch(
            "SELECT status, count(*) AS n FROM orders.orders GROUP BY status",
            operation="orders_by_status")
    except Exception:
        return
    for status in OrderStatus:
        ORDERS_BY_STATUS.labels(status=status.value).set(0)
    for row in rows:
        ORDERS_BY_STATUS.labels(status=row["status"]).set(row["n"])


async def save_order(order: Order, insert: bool = False):
    async with db.acquire("save_order") as conn:
        async with conn.transaction():
            if insert:
                await conn.execute(
                    "INSERT INTO orders.orders "
                    "(id, user_id, status, total_amount, payment_id, shipping_address) "
                    "VALUES ($1, $2, $3, $4, $5, $6)",
                    order.id, order.user_id, order.status.value, order.total,
                    order.payment_id, json.dumps(order.shipping_address.model_dump()))
                for item in order.items:
                    await conn.execute(
                        "INSERT INTO orders.order_items "
                        "(order_id, product_id, name, quantity, price) "
                        "VALUES ($1, $2, $3, $4, $5)",
                        order.id, item.product_id, item.name, item.quantity, item.price)
            else:
                await conn.execute(
                    "UPDATE orders.orders SET status = $2, payment_id = $3, "
                    "total_amount = $4, updated_at = now() WHERE id = $1",
                    order.id, order.status.value, order.payment_id, order.total)

async def load_order(order_id: str):
    row = await db.fetchrow(
        "SELECT * FROM orders.orders WHERE id = $1",
        order_id, operation="load_order")
    if row is None:
        return None
    items = await db.fetch(
        "SELECT product_id, name, quantity, price FROM orders.order_items "
        "WHERE order_id = $1 ORDER BY id",
        order_id, operation="load_order_items")
    return _build_order(row, items)


def _build_order(row, items):
    return Order(
        id=row["id"],
        user_id=row["user_id"],
        items=[OrderItem(product_id=i["product_id"], name=i["name"],
                         quantity=i["quantity"], price=float(i["price"]))
               for i in items],
        total=float(row["total_amount"]),
        status=OrderStatus(row["status"]),
        shipping_address=ShippingAddress(**json.loads(row["shipping_address"])),
        payment_id=row["payment_id"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


register_metrics_middleware(app, REQUEST_COUNT, REQUEST_LATENCY)

register_ops_endpoints(app, "orders-service", chaos, db=db)

async def get_cart(user_id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=5.0)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error calling cart service: {e}")
            return None

async def process_payment(order_id: str, user_id: str, amount: float):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{PAYMENT_SERVICE_URL}/api/payments",
                json={
                    "order_id": order_id,
                    "user_id": user_id,
                    "amount": amount,
                    "currency": "EUR"
                },
                timeout=10.0
            )
            PAYMENT_CALLS.labels(result="success" if response.status_code == 200 else "failure").inc()
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error calling payment service: {e}")
            PAYMENT_CALLS.labels(result="error").inc()
            return None

async def clear_cart(user_id: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.delete(f"{CART_SERVICE_URL}/api/cart/{user_id}", timeout=5.0)
        except Exception as e:
            logger.warning(f"Could not clear cart: {e}")

async def reserve_stock(items: List[dict]):
    async with httpx.AsyncClient() as client:
        for item in items:
            try:
                await client.post(
                    f"{CATALOG_SERVICE_URL}/api/products/{item['product_id']}/reserve",
                    params={"quantity": item['quantity']},
                    timeout=5.0
                )
            except Exception as e:
                logger.warning(f"Could not reserve stock for product {item['product_id']}: {e}")

@app.post("/api/orders", response_model=Order)
async def create_order(request: CreateOrderRequest):
    """Crée une nouvelle commande depuis le panier"""
    with tracer.start_as_current_span("create_order") as span:
        chaos.inject()

        span.set_attribute("user_id", request.user_id)


        cart = await get_cart(request.user_id)
        if not cart or not cart.get("items"):
            raise HTTPException(status_code=400, detail="Cart is empty")


        order_id = await generate_order_id()
        span.set_attribute("order_id", order_id)

        now = datetime.now().isoformat()
        order = Order(
            id=order_id,
            user_id=request.user_id,
            items=[OrderItem(**item) for item in cart["items"]],
            total=cart["total"],
            status=OrderStatus.PENDING,
            shipping_address=request.shipping_address,
            created_at=now,
            updated_at=now
        )

        await save_order(order, insert=True)
        ORDER_VALUE.observe(order.total)


        order.status = OrderStatus.PAYMENT_PROCESSING
        await save_order(order)

        payment_result = await process_payment(order_id, request.user_id, order.total)

        if payment_result:
            order.status = OrderStatus.CONFIRMED
            order.payment_id = payment_result.get("payment_id")


            await reserve_stock([item.model_dump() for item in order.items])


            await clear_cart(request.user_id)

            logger.info(f"Order {order_id} created successfully for user {request.user_id}")
            ORDERS_CREATED.inc()
            await refresh_order_gauges()
        else:
            order.status = OrderStatus.PAYMENT_FAILED
            logger.warning(f"Payment failed for order {order_id}")

        order.updated_at = datetime.now().isoformat()
        await save_order(order)


        if order.status == OrderStatus.PAYMENT_FAILED:
            raise HTTPException(
                status_code=502,
                detail={"error": "payment_failed", "order_id": order_id},
            )

        return order

@app.get("/api/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """Récupère une commande par son ID"""
    with tracer.start_as_current_span("get_order") as span:
        chaos.inject()

        span.set_attribute("order_id", order_id)

        order = await load_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        return order

@app.get("/api/orders/user/{user_id}")
async def get_user_orders(user_id: str, limit: int = 50, offset: int = 0):
    """Récupère toutes les commandes d'un utilisateur"""
    with tracer.start_as_current_span("get_user_orders") as span:
        chaos.inject()

        span.set_attribute("user_id", user_id)


        rows = await db.fetch(
            "SELECT * FROM orders.orders WHERE user_id = $1 "
            "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            user_id, limit, offset, operation="get_user_orders")
        if not rows:
            return []

        order_ids = [r["id"] for r in rows]
        item_rows = await db.fetch(
            "SELECT order_id, product_id, name, quantity, price "
            "FROM orders.order_items WHERE order_id = ANY($1::text[]) ORDER BY id",
            order_ids, operation="get_user_order_items")

        items_by_order = {}
        for item in item_rows:
            items_by_order.setdefault(item["order_id"], []).append(item)

        span.set_attribute("orders_returned", len(rows))
        return [_build_order(r, items_by_order.get(r["id"], [])) for r in rows]

@app.put("/api/orders/{order_id}/status")
async def update_order_status(order_id: str, status: OrderStatus):
    """Met à jour le statut d'une commande"""
    with tracer.start_as_current_span("update_order_status") as span:
        chaos.inject()

        span.set_attribute("order_id", order_id)
        span.set_attribute("new_status", status.value)

        order = await load_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        old_status = order.status
        order.status = status
        order.updated_at = datetime.now().isoformat()
        await save_order(order)

        logger.info(f"Order {order_id} status updated from {old_status} to {status}")

        return order

@app.post("/api/orders/{order_id}/cancel")
async def cancel_order(order_id: str):
    """Annule une commande"""
    with tracer.start_as_current_span("cancel_order") as span:
        chaos.inject()

        span.set_attribute("order_id", order_id)

        order = await load_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            raise HTTPException(status_code=400, detail="Cannot cancel shipped/delivered order")

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now().isoformat()
        await save_order(order)

        logger.info(f"Order {order_id} cancelled")

        return {"message": "Order cancelled", "order_id": order_id}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8083"))
    logger.info(f"Starting Orders Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
