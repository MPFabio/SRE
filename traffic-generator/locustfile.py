#!/usr/bin/env python3
"""
Traffic Generator - Génération de trafic réaliste pour le lab SRE
Utilise Locust pour simuler des utilisateurs e-commerce
"""

from locust import HttpUser, task, between, events
import os
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("traffic-generator")

PRODUCT_IDS = list(range(1, 16))

# Avis produits : seulement si le module d'exemple est branché sur la boutique.
REVIEWS_ENABLED = os.getenv("REVIEWS_ENABLED", "false") == "true"
REVIEW_COMMENTS = ["Très bon produit", "Livraison rapide", "Conforme à la description",
                   "Correct sans plus", "Un peu cher", "Je recommande"]

CATEGORIES = ["computers", "smartphones", "audio", "watches", "accessories"]

SEARCH_QUERIES = ["macbook", "iphone", "pixel", "airpods", "sony", "watch",
                  "thinkpad", "galaxy", "dock", "clavier", "souris", "casque"]

USERS = [
    {"email": "alice@example.com", "password": "password123"},
    {"email": "bob@example.com", "password": "password123"},
    {"email": "charlie@example.com", "password": "password123"},
    {"email": "diana@example.com", "password": "password123"},
    {"email": "eric@example.com", "password": "password123"},
]


class EcommerceUser(HttpUser):
    """Simule un utilisateur e-commerce avec comportement réaliste"""
    
    wait_time = between(1, 5)
    
    def on_start(self):
        """Initialisation de l'utilisateur"""
        self.user_id = f"user-{random.randint(1000, 9999)}"
        self.token = None
        self.cart_items = []
        
        if random.random() < 0.7:
            self.login()
    
    def login(self):
        """Connexion d'un utilisateur"""
        user = random.choice(USERS)
        with self.client.post(
            "/api/users/login",
            json=user,
            catch_response=True,
            name="/api/users/login"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.user_id = data.get("user", {}).get("id", self.user_id)
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    @task(30)
    def browse_products(self):
        """Parcourir les produits (action la plus fréquente)"""
        if random.random() < 0.3:
            category = random.choice(CATEGORIES)
            self.client.get(f"/api/products?category={category}", name="/api/products?category=[cat]")
        else:
            self.client.get("/api/products", name="/api/products")
    
    @task(20)
    def view_product(self):
        """Voir un produit spécifique"""
        product_id = random.choice(PRODUCT_IDS)
        self.client.get(f"/api/products/{product_id}", name="/api/products/[id]")
    
    @task(10)
    def search_products(self):
        """Rechercher des produits"""
        query = random.choice(SEARCH_QUERIES)
        self.client.get(f"/api/search?q={query}", name="/api/search?q=[query]")
    
    @task(5)
    def view_categories(self):
        """Voir les catégories"""
        self.client.get("/api/categories", name="/api/categories")
    
    @task(15)
    def check_stock(self):
        """Vérifier le stock d'un produit"""
        product_id = random.choice(PRODUCT_IDS)
        quantity = random.randint(1, 5)
        self.client.get(
            f"/api/products/{product_id}/stock?quantity={quantity}",
            name="/api/products/[id]/stock"
        )
    
    @task(10)
    def add_to_cart(self):
        """Ajouter un produit au panier"""
        product_id = random.choice(PRODUCT_IDS)
        quantity = random.randint(1, 3)
        
        with self.client.post(
            f"/api/cart/{self.user_id}/items",
            json={"product_id": product_id, "quantity": quantity},
            catch_response=True,
            name="/api/cart/[user]/items"
        ) as response:
            if response.status_code == 200:
                self.cart_items.append(product_id)
                response.success()
            else:
                response.failure(f"Add to cart failed: {response.status_code}")
    
    @task(8)
    def view_cart(self):
        """Voir le panier"""
        self.client.get(f"/api/cart/{self.user_id}", name="/api/cart/[user]")
    
    @task(3)
    def remove_from_cart(self):
        """Retirer un produit du panier"""
        if not self.cart_items:
            return
        product_id = random.choice(self.cart_items)
        with self.client.delete(
            f"/api/cart/{self.user_id}/items/{product_id}",
            catch_response=True,
            name="/api/cart/[user]/items/[id]"
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Remove failed: {response.status_code}")
        self.cart_items = [p for p in self.cart_items if p != product_id]
    
    @task(2)
    def checkout(self):
        """Passer une commande (action rare mais importante)"""
        if not self.cart_items:
            product_id = random.choice(PRODUCT_IDS)
            self.client.post(
                f"/api/cart/{self.user_id}/items",
                json={"product_id": product_id, "quantity": 1},
                name="/api/cart/[user]/items"
            )
        
        order_data = {
            "user_id": self.user_id,
            "shipping_address": {
                "street": "123 Test Street",
                "city": "Paris",
                "postal_code": "75001",
                "country": "France"
            }
        }
        
        with self.client.post(
            "/api/orders",
            json=order_data,
            catch_response=True,
            name="/api/orders"
        ) as response:
            if response.status_code == 200:
                self.cart_items = []
                response.success()
            elif response.status_code in (502, 503):

                response.success()
            elif response.status_code == 400:

                self.cart_items = []
                response.success()
            else:
                response.failure(f"Checkout failed: {response.status_code}")
    
    @task(4)
    def read_reviews(self):
        """Lire les avis d'un produit"""
        if REVIEWS_ENABLED:
            product_id = random.choice(PRODUCT_IDS)
            self.client.get(f"/api/reviews/{product_id}", name="/api/reviews/[id]")

    @task(1)
    def post_review(self):
        """Publier un avis"""
        if REVIEWS_ENABLED:
            self.client.post(
                f"/api/reviews/{random.choice(PRODUCT_IDS)}",
                json={"rating": random.choices([1, 2, 3, 4, 5], [1, 1, 2, 4, 5])[0],
                      "comment": random.choice(REVIEW_COMMENTS)},
                name="/api/reviews/[id] POST",
            )

    @task(2)
    def view_orders(self):
        """Voir ses commandes"""
        self.client.get(f"/api/orders/user/{self.user_id}", name="/api/orders/user/[user]")
    
    @task(1)
    def check_circuit_breaker(self):
        """Vérifier l'état du circuit breaker (monitoring)"""
        self.client.get("/api/circuit-breaker", name="/api/circuit-breaker")
    
    @task(5)
    def check_health(self):
        """Vérifier la santé des services"""
        self.client.get("/health", name="/health")


class AdminUser(HttpUser):
    """Simule un administrateur qui fait des vérifications"""

    wait_time = between(10, 30)
    weight = 1

    def on_start(self):
        """S'authentifie: /api/users exige un jeton."""
        self.token = None
        self.login()

    def login(self):
        user = random.choice(USERS)
        with self.client.post(
            "/api/users/login",
            json=user,
            catch_response=True,
            name="/api/users/login"
        ) as response:
            if response.status_code == 200:
                self.token = response.json().get("token")
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")

    @task(5)
    def check_health(self):
        """Vérifier la santé"""
        self.client.get("/health", name="/health")

    @task(3)
    def list_users(self):
        """Lister les utilisateurs (endpoint authentifie)."""
        if not self.token:
            self.login()
        if not self.token:
            return
        self.client.get("/api/users", name="/api/users",
                        headers={"Authorization": f"Bearer {self.token}"})

    @task(2)
    def check_circuit_breaker(self):
        """Vérifier le circuit breaker"""
        self.client.get("/api/circuit-breaker", name="/api/circuit-breaker")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log custom metrics for each request"""
    if exception:
        logger.warning(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Actions au démarrage du test"""
    logger.info("Traffic generation started")
    logger.info(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Actions à l'arrêt du test"""
    logger.info("Traffic generation stopped")
