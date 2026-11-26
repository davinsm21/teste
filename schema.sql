CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    address TEXT DEFAULT '',
    cpf TEXT,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INTEGER NOT NULL CHECK(price >= 0),
    stock INTEGER NOT NULL CHECK(stock >= 0),
    active INTEGER DEFAULT 1,
    image TEXT DEFAULT '',
    brand TEXT DEFAULT '',
    model TEXT DEFAULT '',
    description TEXT DEFAULT '',
    specifications TEXT DEFAULT '',
    warranty TEXT DEFAULT '',
    cost INTEGER CHECK(cost >= 0),
    promotional_price INTEGER CHECK(promotional_price >= 0)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total INTEGER,
    method TEXT,
    address TEXT,
    status TEXT,
    installments INTEGER,
    discount INTEGER DEFAULT 0,
    coupon TEXT DEFAULT '',
    created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS items (
    sale_id INTEGER REFERENCES sales(id),
    product_id INTEGER REFERENCES products(id),
    name TEXT,
    qty INTEGER,
    price INTEGER,
    cost INTEGER
);

CREATE TABLE IF NOT EXISTS movements (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    delta INTEGER,
    reason TEXT,
    created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS coupons (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE COLLATE NOCASE,

    type TEXT NOT NULL DEFAULT 'percent'
        CHECK(type IN ('percent', 'fixed')),

    discount INTEGER NOT NULL
        CHECK(discount > 0),

    min_purchase INTEGER NOT NULL DEFAULT 0
        CHECK(min_purchase >= 0),

    expires TEXT,

    max_uses INTEGER DEFAULT 100
        CHECK(max_uses > 0),

    uses INTEGER NOT NULL DEFAULT 0
        CHECK(uses >= 0),

    active INTEGER NOT NULL DEFAULT 1
        CHECK(active IN (0, 1)),

    created TEXT DEFAULT CURRENT_TIMESTAMP,

    CHECK(type != 'percent' OR discount <= 100)
);