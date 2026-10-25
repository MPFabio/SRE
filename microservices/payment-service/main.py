from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge
import uvicorn
import os
import time
import random
from datetime import datetime
from enum import Enum
import asyncio


from _shared import (setup_telemetry, setup_app, ChaosController,
                     register_metrics_middleware, register_ops_endpoints)

logger, tracer = setup_telemetry("payment-service")


REQUEST_COUNT = Counter('payment_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('payment_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
PAYMENT_PROCESSED = Counter('payments_processed_total', 'Payments processed', ['status'])
PAYMENT_AMOUNT = Histogram('payment_amount_dollars', 'Payment amount distribution', buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000])
CIRCUIT_BREAKER_STATE = Gauge('circuit_breaker_state', 'Circuit breaker state (0=closed, 1=open, 2=half-open)')
EXTERNAL_PROVIDER_LATENCY = Histogram('external_payment_provider_latency_seconds', 'External payment provider latency')
EXTERNAL_PROVIDER_ERRORS = Counter('external_payment_provider_errors_total', 'External payment provider errors')

app = FastAPI(title="Payment Service", version="1.0.0")

setup_app(app)

chaos = ChaosController("payment-service", logger)

PROVIDER_SLOW_THRESHOLD = float(os.getenv("PROVIDER_SLOW_THRESHOLD", "1.0"))


class CircuitBreakerState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker: transitioning to HALF_OPEN")
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                CIRCUIT_BREAKER_STATE.set(2)
                return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self):
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1
            
            if self.success_count >= self.half_open_max_calls:
                logger.info("Circuit breaker: transitioning to CLOSED")
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                CIRCUIT_BREAKER_STATE.set(0)
        else:
            self.failure_count = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.warning("Circuit breaker: HALF_OPEN -> OPEN (failure in half-open)")
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            CIRCUIT_BREAKER_STATE.set(1)
        elif self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit breaker: CLOSED -> OPEN (threshold reached: {self.failure_count})")
            self.state = CircuitBreakerState.OPEN
            CIRCUIT_BREAKER_STATE.set(1)
    
    def get_state(self):
        return {
            "state": self.state.name,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


circuit_breaker = CircuitBreaker()
CIRCUIT_BREAKER_STATE.set(0)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentRequest(BaseModel):
    order_id: str
    user_id: str
    amount: float
    currency: str = "EUR"
    card_last_four: Optional[str] = "4242"

class Payment(BaseModel):
    payment_id: str
    order_id: str
    user_id: str
    amount: float
    currency: str
    status: PaymentStatus
    provider_reference: Optional[str] = None
    created_at: str
    updated_at: str


payments_db: dict = {}
payment_counter = 0

def generate_payment_id():
    global payment_counter
    payment_counter += 1
    return f"PAY-{datetime.now().strftime('%Y%m%d')}-{payment_counter:05d}"

async def call_external_payment_provider(amount: float, currency: str) -> dict:
    start_time = time.time()
    
    try:

        base_latency = random.uniform(0.1, 0.5)
        

        if chaos.enabled:
            if chaos.latency_ms > 0:
                additional_latency = chaos.latency_ms / 1000
                base_latency += additional_latency
            
            if chaos.error_rate > 0 and random.random() < chaos.error_rate:
                await asyncio.sleep(base_latency)
                EXTERNAL_PROVIDER_ERRORS.inc()
                raise Exception("External payment provider error: upstream returned 503")
        
        await asyncio.sleep(base_latency)
        

        if random.random() < 0.02:
            EXTERNAL_PROVIDER_ERRORS.inc()
            raise Exception("External payment provider temporarily unavailable")
        
        elapsed = time.time() - start_time
        EXTERNAL_PROVIDER_LATENCY.observe(elapsed)
        if elapsed > PROVIDER_SLOW_THRESHOLD:
            logger.warning(
                f"External payment provider slow response: {elapsed:.2f}s "
                f"(threshold {PROVIDER_SLOW_THRESHOLD:.1f}s)")

        return {
            "success": True,
            "provider_reference": f"EXT-{random.randint(100000, 999999)}",
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        EXTERNAL_PROVIDER_LATENCY.observe(time.time() - start_time)
        raise e

register_metrics_middleware(app, REQUEST_COUNT, REQUEST_LATENCY)

register_ops_endpoints(app, "payment-service", chaos)

@app.get("/api/circuit-breaker")
async def get_circuit_breaker_status():
    """Retourne l'état du circuit breaker"""
    return circuit_breaker.get_state()

@app.post("/api/circuit-breaker/reset")
async def reset_circuit_breaker():
    """Reset manuel du circuit breaker (admin)"""
    circuit_breaker.state = CircuitBreakerState.CLOSED
    circuit_breaker.failure_count = 0
    circuit_breaker.success_count = 0
    CIRCUIT_BREAKER_STATE.set(0)
    logger.info("Circuit breaker manually reset")
    return {"message": "Circuit breaker reset", "state": circuit_breaker.get_state()}

@app.post("/api/payments", response_model=Payment)
async def process_payment(request: PaymentRequest):
    """Traite un paiement"""
    with tracer.start_as_current_span("process_payment") as span:
        span.set_attribute("order_id", request.order_id)
        span.set_attribute("amount", request.amount)
        span.set_attribute("currency", request.currency)
        

        if not circuit_breaker.can_execute():
            logger.warning(f"Payment blocked by circuit breaker for order {request.order_id}")
            PAYMENT_PROCESSED.labels(status="circuit_open").inc()
            raise HTTPException(
                status_code=503,
                detail="Payment service temporarily unavailable due to external provider issues"
            )
        

        payment_id = generate_payment_id()
        span.set_attribute("payment_id", payment_id)
        
        payment = Payment(
            payment_id=payment_id,
            order_id=request.order_id,
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            status=PaymentStatus.PROCESSING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        payments_db[payment_id] = payment
        

        try:
            result = await call_external_payment_provider(request.amount, request.currency)
            
            payment.status = PaymentStatus.COMPLETED
            payment.provider_reference = result["provider_reference"]
            payment.updated_at = datetime.now().isoformat()
            
            circuit_breaker.record_success()
            PAYMENT_PROCESSED.labels(status="completed").inc()
            PAYMENT_AMOUNT.observe(request.amount)
            
            logger.info(f"Payment {payment_id} completed for order {request.order_id}")
            
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.updated_at = datetime.now().isoformat()
            
            circuit_breaker.record_failure()
            PAYMENT_PROCESSED.labels(status="failed").inc()
            
            logger.error(f"Payment {payment_id} failed for order {request.order_id}: {e}")
            
            raise HTTPException(status_code=500, detail=f"Payment failed: {str(e)}")
        
        payments_db[payment_id] = payment
        return payment

@app.get("/api/payments/{payment_id}", response_model=Payment)
async def get_payment(payment_id: str):
    """Récupère un paiement par son ID"""
    with tracer.start_as_current_span("get_payment") as span:
        span.set_attribute("payment_id", payment_id)
        
        if payment_id not in payments_db:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return payments_db[payment_id]

@app.post("/api/payments/{payment_id}/refund")
async def refund_payment(payment_id: str):
    """Rembourse un paiement"""
    with tracer.start_as_current_span("refund_payment") as span:
        span.set_attribute("payment_id", payment_id)
        
        if payment_id not in payments_db:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        payment = payments_db[payment_id]
        
        if payment.status != PaymentStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Can only refund completed payments")
        
        payment.status = PaymentStatus.REFUNDED
        payment.updated_at = datetime.now().isoformat()
        payments_db[payment_id] = payment
        
        PAYMENT_PROCESSED.labels(status="refunded").inc()
        logger.info(f"Payment {payment_id} refunded")
        
        return {"message": "Payment refunded", "payment_id": payment_id}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8084"))
    logger.info(f"Starting Payment Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
