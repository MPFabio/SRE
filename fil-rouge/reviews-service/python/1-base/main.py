"""Avis produits ShopEasy, étape 1 : API et route de santé."""
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "reviews-service")
PORT = int(os.getenv("PORT", "8086"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(SERVICE_NAME)

FORBIDDEN_WORDS = {"arnaque", "nul"}

app = FastAPI(title=SERVICE_NAME)

reviews: dict[int, list[dict]] = {}


class Review(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/reviews/{product_id}")
def list_reviews(product_id: int):
    items = reviews.get(product_id, [])
    average = round(sum(r["rating"] for r in items) / len(items), 2) if items else None
    return {"product_id": product_id, "count": len(items), "average": average, "reviews": items}


@app.post("/api/reviews/{product_id}", status_code=201)
def create_review(product_id: int, review: Review):
    if FORBIDDEN_WORDS & set(review.comment.lower().split()):
        logger.warning("Avis refusé pour le produit %d : modération", product_id)
        raise HTTPException(status_code=422, detail="Avis refusé par la modération")

    reviews.setdefault(product_id, []).append(review.model_dump())

    logger.info("Avis %d/5 publié pour le produit %d", review.rating, product_id)
    return review


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
