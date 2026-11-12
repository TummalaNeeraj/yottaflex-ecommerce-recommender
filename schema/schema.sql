CREATE TABLE categories (
  category_id TEXT PRIMARY KEY,
  category_name TEXT NOT NULL,
  parent_category_id TEXT REFERENCES categories(category_id),
  level INTEGER NOT NULL,
  is_seasonal BOOLEAN NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('active','inactive'))
);

CREATE TABLE customers (
  customer_id TEXT PRIMARY KEY,
  created_at TIMESTAMP NOT NULL,
  region TEXT NOT NULL,
  segment TEXT NOT NULL CHECK (segment IN ('regular','sparse','high_value')),
  marketing_opt_in BOOLEAN NOT NULL,
  lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('active','inactive'))
);

CREATE TABLE products (
  product_id TEXT PRIMARY KEY,
  product_name TEXT NOT NULL,
  category_id TEXT NOT NULL REFERENCES categories(category_id),
  unit_price DECIMAL(12,2) NOT NULL CHECK (unit_price >= 0),
  currency CHAR(3) NOT NULL,
  availability_status TEXT NOT NULL CHECK (availability_status IN ('active','unavailable','discontinued')),
  stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
  is_cold_start BOOLEAN NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE
);

CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP NOT NULL,
  channel TEXT NOT NULL,
  is_bot BOOLEAN NOT NULL,
  split TEXT NOT NULL CHECK (split IN ('train','test')),
  lifecycle_state TEXT NOT NULL
);

CREATE TABLE page_views (
  event_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  product_id TEXT NOT NULL REFERENCES products(product_id),
  event_type TEXT NOT NULL,
  event_at TIMESTAMP NOT NULL,
  dwell_seconds INTEGER NOT NULL
);

CREATE TABLE carts (
  cart_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  created_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL,
  converted_order_id TEXT
);

CREATE TABLE cart_lines (
  cart_line_id TEXT PRIMARY KEY,
  cart_id TEXT NOT NULL REFERENCES carts(cart_id),
  product_id TEXT NOT NULL REFERENCES products(product_id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price DECIMAL(12,2) NOT NULL,
  added_at TIMESTAMP NOT NULL,
  lifecycle_state TEXT NOT NULL
);

CREATE TABLE orders (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  cart_id TEXT NOT NULL REFERENCES carts(cart_id),
  ordered_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL,
  subtotal DECIMAL(12,2) NOT NULL,
  discount_amount DECIMAL(12,2) NOT NULL,
  tax_amount DECIMAL(12,2) NOT NULL,
  shipping_amount DECIMAL(12,2) NOT NULL,
  total_amount DECIMAL(12,2) NOT NULL,
  currency CHAR(3) NOT NULL
);

CREATE TABLE order_lines (
  order_line_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  product_id TEXT NOT NULL REFERENCES products(product_id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price DECIMAL(12,2) NOT NULL,
  line_total DECIMAL(12,2) NOT NULL
);

CREATE TABLE product_relations (
  relation_id TEXT PRIMARY KEY,
  source_product_id TEXT NOT NULL REFERENCES products(product_id),
  related_product_id TEXT NOT NULL REFERENCES products(product_id),
  relation_type TEXT NOT NULL,
  strength DECIMAL(8,6) NOT NULL,
  support_count INTEGER NOT NULL,
  effective_from TIMESTAMP NOT NULL,
  effective_to TIMESTAMP
);

CREATE TABLE recommendations (
  recommendation_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  product_id TEXT NOT NULL REFERENCES products(product_id),
  generated_at TIMESTAMP NOT NULL,
  rank INTEGER NOT NULL,
  score DECIMAL(10,6) NOT NULL,
  reason TEXT NOT NULL,
  model_version TEXT NOT NULL,
  split TEXT NOT NULL
);

