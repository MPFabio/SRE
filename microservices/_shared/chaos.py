import logging
import os
import random
import time

from fastapi import HTTPException
from pydantic import BaseModel


class ChaosConfig(BaseModel):
    enabled: bool = False
    latency_ms: int = 0
    error_rate: float = 0


class ChaosController:

    def __init__(self, service_name: str, logger: logging.Logger = None):
        self.service_name = service_name
        self.logger = logger or logging.getLogger(service_name)

        self.enabled = os.getenv("CHAOS_MODE", "false").lower() == "true"
        self.latency_ms = int(os.getenv("CHAOS_LATENCY_MS", "0"))
        self.error_rate = float(os.getenv("CHAOS_ERROR_RATE", "0"))

    def inject(self):
        if not self.enabled:
            return
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)
        if self.error_rate > 0 and random.random() < self.error_rate:
            self.logger.error("Unhandled exception while processing request")
            raise HTTPException(status_code=500, detail="Internal server error")

    def apply(self, config: ChaosConfig) -> dict:
        self.enabled = config.enabled
        self.latency_ms = config.latency_ms
        self.error_rate = config.error_rate
        self.logger.debug(
            "Chaos config updated: enabled=%s, latency_ms=%s, error_rate=%s",
            self.enabled, self.latency_ms, self.error_rate,
        )
        return self.state()

    def state(self) -> dict:
        return {
            "enabled": self.enabled,
            "latency_ms": self.latency_ms,
            "error_rate": self.error_rate,
        }
