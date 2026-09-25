
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS orders;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS lab;

CREATE TABLE IF NOT EXISTS catalog.categories (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog.products (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    category    TEXT NOT NULL REFERENCES catalog.categories(name),
    stock       INTEGER NOT NULL CHECK (stock >= 0),
    image_url   TEXT,
    brand       TEXT,
    compare_at_price NUMERIC(10, 2) CHECK (compare_at_price >= 0),
    rating      NUMERIC(2, 1) CHECK (rating >= 0 AND rating <= 5),
    rating_count INTEGER NOT NULL DEFAULT 0 CHECK (rating_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_products_category ON catalog.products(category);

CREATE SEQUENCE IF NOT EXISTS orders.order_seq START 1;

CREATE TABLE IF NOT EXISTS orders.orders (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    status        TEXT NOT NULL,
    total_amount  NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    payment_id    TEXT,
    shipping_address JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders.order_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    TEXT NOT NULL REFERENCES orders.orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL,
    name        TEXT NOT NULL DEFAULT '',
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_orders_user    ON orders.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders.orders(status);
CREATE INDEX IF NOT EXISTS idx_items_order    ON orders.order_items(order_id);

CREATE SEQUENCE IF NOT EXISTS users.user_seq START 1;

CREATE TABLE IF NOT EXISTS users.users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS users.sessions (
    user_id     TEXT PRIMARY KEY REFERENCES users.users(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    login_time  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab.incidents (
    id         TEXT PRIMARY KEY,
    content    JSONB NOT NULL,
    status     TEXT GENERATED ALWAYS AS (content->>'status') STORED,
    severity   TEXT GENERATED ALWAYS AS (content->>'severity') STORED,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab.postmortems (
    id          TEXT PRIMARY KEY,
    content     JSONB NOT NULL,
    incident_id TEXT GENERATED ALWAYS AS (content->>'incident_id') STORED,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lab.toil_tasks (
    id         TEXT PRIMARY KEY,
    content    JSONB NOT NULL,
    automated  BOOLEAN GENERATED ALWAYS AS ((content->>'automated')::boolean) STORED,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_incidents_status ON lab.incidents(status);
CREATE INDEX IF NOT EXISTS idx_postmortems_inc  ON lab.postmortems(incident_id);
