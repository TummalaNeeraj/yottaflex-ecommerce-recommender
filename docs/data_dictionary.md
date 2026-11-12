# Data dictionary

All identifiers are immutable strings. All timestamps use ISO-8601 without a timezone and represent UTC. Money uses decimal values with two fractional digits.

| Entity | Primary key | Required foreign keys | Important fields and rules |
|---|---|---|---|
| Customer | `customer_id` | None | `CUS-000001`; segment is regular, sparse, or high_value; lifecycle is active/inactive. |
| Category | `category_id` | Optional `parent_category_id` | Parent is blank for root categories; hierarchy level is 0 or 1; effective dates preserve lifecycle. |
| Product | `product_id` | `category_id` | `SKU-000001`; price >= 0; currency is USD; status is active, unavailable, or discontinued; stock >= 0. |
| Session | `session_id` | `customer_id` | `SES-2026-000001`; end >= start; split is train/test; `is_bot` labels noisy sessions. |
| PageView | `event_id` | `session_id`, `customer_id`, `product_id` | `EVT-SES-2026-000001-001`; event is within its session; dwell seconds >= 0. |
| Cart | `cart_id` | `session_id`, `customer_id`; optional converted order | `CART-2026-000001`; status is active, abandoned, or converted. |
| CartLine | `cart_line_id` | `cart_id`, `product_id` | Quantity > 0; unit price is copied from the product at event time. |
| Order | `order_id` | `customer_id`, `session_id`, `cart_id` | `ORD-2026-000001`; monetary fields are derived from order lines. |
| OrderLine | `order_line_id` | `order_id`, `product_id` | `line_total = quantity * unit_price`; quantity > 0. |
| ProductRelation | `relation_id` | source and related product IDs | Relation type is co_purchase or same_category; strength is 0..1; effective dates retain history. |
| Recommendation | `recommendation_id` | `customer_id`, `product_id` | Rank starts at 1; score is 0..1; purchased/unavailable/discontinued products are excluded in baseline data. |

The complete SQL types, nullability, enum checks, uniqueness rules and foreign keys are defined in `schema/schema.sql`.

## Cardinality

- Customer 1:N Session, Cart, Order, Recommendation.
- Category 1:N Product; Category 1:N child Category (optional self-reference).
- Session 1:N PageView and 0:1 Cart.
- Cart 1:N CartLine and 0:1 Order.
- Order 1:N OrderLine.
- Product N:M Product through ProductRelation.
- Customer N:M Product through PageView, OrderLine and Recommendation.

