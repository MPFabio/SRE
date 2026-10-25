from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge
import uvicorn
from contextlib import asynccontextmanager
import os
import hashlib
import secrets
from datetime import datetime, timedelta
import jwt


from _shared import (setup_telemetry, setup_app, ChaosController,
                     register_metrics_middleware,
                     register_ops_endpoints, Database)

logger, tracer = setup_telemetry("users-service")


REQUEST_COUNT = Counter('users_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('users_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
ACTIVE_SESSIONS = Gauge('users_active_sessions', 'Active user sessions')
LOGIN_ATTEMPTS = Counter('users_login_attempts_total', 'Login attempts', ['result'])
REGISTRATIONS = Counter('users_registrations_total', 'User registrations')

@asynccontextmanager
async def lifespan(_app):
    await db.connect()
    await init_seed_users()
    await refresh_session_gauge()
    yield
    await db.disconnect()

app = FastAPI(title="Users Service", version="1.0.0", lifespan=lifespan)

setup_app(app)


JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

chaos = ChaosController("users-service", logger)
db = Database("users-service", logger)


class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    created_at: str
    last_login: Optional[str] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${derived.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    salt, _, _ = password_hash.partition("$")
    return secrets.compare_digest(hash_password(password, salt), password_hash)


async def generate_user_id() -> str:
    seq = await db.fetchrow(
        "SELECT nextval('users.user_seq') AS n", operation="user_id")
    return f"USR-{seq['n']:05d}"

def _profile(row) -> UserProfile:
    return UserProfile(
        id=row["id"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        created_at=row["created_at"].isoformat(),
        last_login=row["last_login"].isoformat() if row["last_login"] else None,
    )

async def get_user_by_email(email: str):
    return await db.fetchrow(
        "SELECT * FROM users.users WHERE email = $1",
        email, operation="get_user_by_email")

async def refresh_session_gauge():
    row = await db.fetchrow(
        "SELECT count(*) AS n FROM users.sessions", operation="session_count")
    ACTIVE_SESSIONS.set(row["n"])

async def init_seed_users():
    seed_users = [
        {"email": "alice@example.com", "password": "password123", "first_name": "Alice", "last_name": "Dupont"},
        {"email": "bob@example.com", "password": "password123", "first_name": "Bob", "last_name": "Martin"},
        {"email": "charlie@example.com", "password": "password123", "first_name": "Charlie", "last_name": "Bernard"},
        {"email": "diana@example.com", "password": "password123", "first_name": "Diana", "last_name": "Petit"},
        {"email": "eric@example.com", "password": "password123", "first_name": "Eric", "last_name": "Robert"},
    ]
    created = 0
    for user in seed_users:
        if await get_user_by_email(user["email"]) is not None:
            continue
        user_id = await generate_user_id()
        await db.execute(
            "INSERT INTO users.users (id, email, password_hash, first_name, last_name) "
            "VALUES ($1, $2, $3, $4, $5) ON CONFLICT (email) DO NOTHING",
            user_id, user["email"], hash_password(user["password"]),
            user["first_name"], user["last_name"], operation="seed_users")
        created += 1
    logger.info(f"Seed users : {created} créé(s), {len(seed_users) - created} déjà présent(s)")

def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

register_metrics_middleware(app, REQUEST_COUNT, REQUEST_LATENCY)

register_ops_endpoints(app, "users-service", chaos, db=db)

@app.post("/api/users/register", response_model=UserProfile)
async def register_user(user_data: UserCreate):
    """Enregistre un nouvel utilisateur"""
    with tracer.start_as_current_span("register_user") as span:
        await chaos.inject()

        span.set_attribute("email", user_data.email)

        if await get_user_by_email(user_data.email) is not None:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = await generate_user_id()
        span.set_attribute("user_id", user_id)

        row = await db.fetchrow(
            "INSERT INTO users.users (id, email, password_hash, first_name, last_name) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING *",
            user_id, user_data.email, hash_password(user_data.password),
            user_data.first_name, user_data.last_name, operation="register_user")

        REGISTRATIONS.inc()
        logger.info("User registered: %s (%s)", user_id, user_data.email)

        return _profile(row)

@app.post("/api/users/login")
async def login_user(credentials: UserLogin):
    """Authentifie un utilisateur"""
    with tracer.start_as_current_span("login_user") as span:
        await chaos.inject()

        span.set_attribute("email", credentials.email)

        user = await get_user_by_email(credentials.email)
        if user is None:
            LOGIN_ATTEMPTS.labels(result="user_not_found").inc()
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(credentials.password, user["password_hash"]):
            LOGIN_ATTEMPTS.labels(result="wrong_password").inc()
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = await db.fetchrow(
            "UPDATE users.users SET last_login = now() WHERE id = $1 RETURNING *",
            user["id"], operation="update_last_login")

        token = create_jwt_token(user["id"], credentials.email)

        await db.execute(
            "INSERT INTO users.sessions (user_id, email, login_time) VALUES ($1, $2, now()) "
            "ON CONFLICT (user_id) DO UPDATE SET login_time = now()",
            user["id"], credentials.email, operation="create_session")
        await refresh_session_gauge()

        LOGIN_ATTEMPTS.labels(result="success").inc()
        logger.info("User logged in: %s (%s)", user["id"], credentials.email)

        return {"token": token, "user": _profile(user)}

@app.post("/api/users/logout")
async def logout_user(authorization: str = Header(None)):
    """Déconnecte un utilisateur"""
    with tracer.start_as_current_span("logout_user"):
        await chaos.inject()

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")

        token = authorization.split(" ")[1]
        payload = verify_jwt_token(token)

        user_id = payload["user_id"]

        await db.execute("DELETE FROM users.sessions WHERE user_id = $1",
                         user_id, operation="delete_session")
        await refresh_session_gauge()

        logger.info("User logged out: %s", user_id)

        return {"message": "Logged out successfully"}

@app.get("/api/users/me", response_model=UserProfile)
async def get_current_user(authorization: str = Header(None)):
    """Récupère le profil de l'utilisateur connecté"""
    with tracer.start_as_current_span("get_current_user"):
        await chaos.inject()

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")

        token = authorization.split(" ")[1]
        payload = verify_jwt_token(token)

        user = await get_user_by_email(payload["email"])
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return _profile(user)

@app.get("/api/users/{user_id}", response_model=UserProfile)
async def get_user(user_id: str, authorization: str = Header(None)):
    """Récupère un profil utilisateur par ID (utilisateur authentifié uniquement)"""
    with tracer.start_as_current_span("get_user") as span:
        await chaos.inject()

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")

        token = authorization.split(" ")[1]
        verify_jwt_token(token)

        span.set_attribute("user_id", user_id)

        row = await db.fetchrow("SELECT * FROM users.users WHERE id = $1",
                                user_id, operation="get_user")
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")

        return _profile(row)

@app.put("/api/users/me", response_model=UserProfile)
async def update_current_user(update_data: UserUpdate, authorization: str = Header(None)):
    """Met à jour le profil de l'utilisateur connecté"""
    with tracer.start_as_current_span("update_current_user"):
        await chaos.inject()

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")

        token = authorization.split(" ")[1]
        payload = verify_jwt_token(token)

        user = await get_user_by_email(payload["email"])
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")


        row = await db.fetchrow(
            "UPDATE users.users SET first_name = COALESCE($2, first_name), "
            "last_name = COALESCE($3, last_name) WHERE id = $1 RETURNING *",
            user["id"], update_data.first_name, update_data.last_name,
            operation="update_user")

        logger.info("User profile updated: %s", row["id"])

        return _profile(row)

@app.get("/api/users")
async def list_users(authorization: str = Header(None)):
    """Liste tous les utilisateurs (utilisateur authentifié uniquement)"""
    with tracer.start_as_current_span("list_users"):
        await chaos.inject()

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")

        token = authorization.split(" ")[1]
        verify_jwt_token(token)

        rows = await db.fetch("SELECT * FROM users.users ORDER BY id",
                              operation="list_users")
        return [_profile(r) for r in rows]

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8085"))
    logger.info(f"Starting Users Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
