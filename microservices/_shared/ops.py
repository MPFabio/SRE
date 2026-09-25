from datetime import datetime

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .chaos import ChaosConfig, ChaosController


def register_ops_endpoints(app: FastAPI, service_name: str,
                           chaos: ChaosController = None, db=None):

    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": service_name,
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/ready")
    async def ready():
        """Readiness check endpoint"""
        if db is None:
            return {"status": "ready", "service": service_name}
        db_ok = await db.healthy()
        payload = {
            "status": "ready" if db_ok else "not-ready",
            "service": service_name,
            "database": "up" if db_ok else "down",
        }
        return JSONResponse(payload, status_code=200 if db_ok else 503)

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    if chaos is not None:
        @app.get("/api/chaos")
        async def get_chaos():
            """Etat courant de l'injection de chaos (consomme par 'make chaos-status')"""
            return chaos.state()

        @app.post("/api/chaos")
        async def set_chaos(config: ChaosConfig):
            """Active/desactive l'injection de chaos a chaud (pilote par le Lab Controller)"""
            return chaos.apply(config)

    return app
