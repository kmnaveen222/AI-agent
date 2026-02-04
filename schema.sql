-- schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS restaurants (
  id              INTEGER PRIMARY KEY,
  name            TEXT NOT NULL,
  area            TEXT,             -- e.g., T. Nagar, OMR
  city            TEXT,             -- e.g., Chennai
  cuisine_tags    TEXT,             -- CSV tags: 'South Indian,Biryani'
  rating          REAL,             -- 0-5
  price_level     INTEGER,          -- 1=cheap, 2=mid, 3=premium
  is_open         INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS menu_items (
  id              INTEGER PRIMARY KEY,
  restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  description     TEXT,
  price_cents     INTEGER NOT NULL,
  is_available    INTEGER DEFAULT 1,
  category        TEXT              -- e.g., 'Main Course','Dessert'
);

CREATE TABLE IF NOT EXISTS carts (
  id              TEXT PRIMARY KEY, -- a session/user UUID
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cart_items (
  id              INTEGER PRIMARY KEY,
  cart_id         TEXT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  menu_item_id    INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE RESTRICT,
  quantity        INTEGER NOT NULL CHECK(quantity > 0),
  -- snapshot price to protect against menu changes
  unit_price_cents INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id              TEXT PRIMARY KEY, -- UUID
  cart_id         TEXT NOT NULL REFERENCES carts(id),
  status          TEXT NOT NULL CHECK(status IN ('PLACED','CONFIRMED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','CANCELLED')),
  subtotal_cents  INTEGER NOT NULL,
  delivery_fee_cents INTEGER NOT NULL,
  total_cents     INTEGER NOT NULL,
  placed_at       TEXT NOT NULL DEFAULT (datetime('now')),
  eta_minutes     INTEGER,          -- mock ETA
  tracking_code   TEXT              -- mock tracking ref
);

CREATE TABLE IF NOT EXISTS order_items (
  id              INTEGER PRIMARY KEY,
  order_id        TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  menu_item_name  TEXT NOT NULL,          -- snapshot
  unit_price_cents INTEGER NOT NULL,      -- snapshot
  quantity        INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city);
CREATE INDEX IF NOT EXISTS idx_menu_restaurant ON menu_items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id);
CREATE INDEX IF NOT EXISTS idx_orders_cart ON orders(cart_id);


CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cart_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
  content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
ON messages(conversation_id);
