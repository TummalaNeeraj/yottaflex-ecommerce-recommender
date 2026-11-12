from __future__ import annotations

import csv
import hashlib
import itertools
import json
import random
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


TABLE_ORDER = [
    "categories",
    "customers",
    "products",
    "sessions",
    "page_views",
    "carts",
    "cart_lines",
    "orders",
    "order_lines",
    "product_relations",
    "recommendations",
]

PRIMARY_KEYS = {
    "categories": "category_id",
    "customers": "customer_id",
    "products": "product_id",
    "sessions": "session_id",
    "page_views": "event_id",
    "carts": "cart_id",
    "cart_lines": "cart_line_id",
    "orders": "order_id",
    "order_lines": "order_line_id",
    "product_relations": "relation_id",
    "recommendations": "recommendation_id",
}


def money(value: Decimal | float | int) -> str:
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def random_time(rng: random.Random, start: datetime, end: datetime) -> datetime:
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, max(0, seconds)))


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    required = {"seed", "year", "customers", "products", "categories", "sessions", "orders"}
    missing = required - config.keys()
    if missing:
        raise ValueError(f"Missing config keys: {sorted(missing)}")
    if config["orders"] > config["sessions"]:
        raise ValueError("orders cannot exceed sessions")
    return config


def build_categories(config: dict[str, Any]) -> list[dict[str, str]]:
    names = [
        "Electronics", "Home", "Fashion", "Sports", "Mobiles", "Computers",
        "Kitchen", "Furniture", "Men", "Women", "Fitness", "Outdoor",
    ]
    rows: list[dict[str, str]] = []
    roots = min(4, config["categories"])
    for index in range(1, config["categories"] + 1):
        parent = "" if index <= roots else f"CAT-{((index - roots - 1) % roots) + 1:04d}"
        rows.append({
            "category_id": f"CAT-{index:04d}",
            "category_name": names[index - 1] if index <= len(names) else f"Category {index}",
            "parent_category_id": parent,
            "level": "0" if not parent else "1",
            "is_seasonal": "true" if index % 5 == 0 else "false",
            "effective_from": f"{config['year']}-01-01",
            "effective_to": "",
            "lifecycle_state": "active",
        })
    return rows


def build_customers(config: dict[str, Any], rng: random.Random) -> list[dict[str, str]]:
    start = dt(config["start_date"]) - timedelta(days=365)
    end = dt(config["start_date"])
    regions = ["north", "south", "east", "west", "central"]
    rows = []
    for index in range(1, config["customers"] + 1):
        rows.append({
            "customer_id": f"CUS-{index:06d}",
            "created_at": iso(random_time(rng, start, end)),
            "region": rng.choice(regions),
            "segment": rng.choices(["regular", "sparse", "high_value"], [70, 23, 7])[0],
            "marketing_opt_in": rng.choices(["true", "false"], [65, 35])[0],
            "lifecycle_state": rng.choices(["active", "inactive"], [94, 6])[0],
        })
    return rows


def build_products(
    config: dict[str, Any], rng: random.Random, categories: list[dict[str, str]]
) -> list[dict[str, str]]:
    rows = []
    for index in range(1, config["products"] + 1):
        status = rng.choices(["active", "unavailable", "discontinued"], [88, 8, 4])[0]
        category = rng.choice(categories)
        price = Decimal(str(rng.uniform(5, 1000)))
        rows.append({
            "product_id": f"SKU-{index:06d}",
            "product_name": f"Synthetic Product {index:06d}",
            "category_id": category["category_id"],
            "unit_price": money(price),
            "currency": "USD",
            "availability_status": status,
            "stock_quantity": "0" if status != "active" else str(rng.randint(1, 500)),
            "is_cold_start": "true" if index > int(config["products"] * 0.95) else "false",
            "effective_from": f"{config['year']}-01-01",
            "effective_to": f"{config['year']}-08-31" if status == "discontinued" else "",
        })
    if rows and not any(row["availability_status"] == "discontinued" for row in rows):
        rows[-1]["availability_status"] = "discontinued"
        rows[-1]["stock_quantity"] = "0"
    return rows


def build_sessions_and_views(
    config: dict[str, Any],
    rng: random.Random,
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], datetime]:
    start, end = dt(config["start_date"]), dt(config["end_date"])
    cutoff = start + (end - start) * 0.8
    sessions, views = [], []
    product_ids = [row["product_id"] for row in products]
    cold_start_ids = [row["product_id"] for row in products if row["is_cold_start"] == "true"]
    established_ids = [row["product_id"] for row in products if row["is_cold_start"] == "false"]
    seasonal_category_ids = {
        f"CAT-{index:04d}" for index in range(1, config["categories"] + 1) if index % 5 == 0
    }
    seasonal_ids = [
        row["product_id"] for row in products if row["category_id"] in seasonal_category_ids
    ]
    products_by_category: dict[str, list[str]] = defaultdict(list)
    established_by_category: dict[str, list[str]] = defaultdict(list)
    for product in products:
        products_by_category[product["category_id"]].append(product["product_id"])
        if product["is_cold_start"] == "false":
            established_by_category[product["category_id"]].append(product["product_id"])
    sparse_ids = [row["customer_id"] for row in customers if row["segment"] == "sparse"]
    normal_ids = [row["customer_id"] for row in customers if row["segment"] != "sparse"]
    for index in range(1, config["sessions"] + 1):
        session_id = f"SES-{config['year']}-{index:06d}"
        is_bot = rng.random() < 0.03
        customer_pool = sparse_ids if sparse_ids and rng.random() < 0.12 else normal_ids or sparse_ids
        customer_id = rng.choice(customer_pool)
        started = random_time(rng, start, end)
        view_count = rng.randint(10, 18) if is_bot else rng.randint(1, 6)
        event_gap = rng.randint(15, 120)
        ended = started + timedelta(seconds=(view_count + 1) * event_gap)
        sessions.append({
            "session_id": session_id,
            "customer_id": customer_id,
            "started_at": iso(started),
            "ended_at": iso(ended),
            "channel": rng.choice(["web", "mobile", "app"]),
            "is_bot": str(is_bot).lower(),
            "split": "train" if started < cutoff else "test",
            "lifecycle_state": "completed",
        })
        for event_number in range(1, view_count + 1):
            event_at = started + timedelta(seconds=event_number * event_gap)
            available_pool = established_ids if started < cutoff else product_ids
            customer_number = int(customer_id.split("-")[-1])
            preferred_category = f"CAT-{((customer_number - 1) % config['categories']) + 1:04d}"
            preferred_pool = (
                established_by_category[preferred_category]
                if started < cutoff else products_by_category[preferred_category]
            )
            if preferred_pool and rng.random() < 0.75:
                available_pool = preferred_pool
            if seasonal_ids and started.month in {9, 10} and rng.random() < 0.35:
                available_pool = seasonal_ids
            if started >= cutoff and cold_start_ids and rng.random() < 0.08:
                available_pool = cold_start_ids
            views.append({
                "event_id": f"EVT-{session_id}-{event_number:03d}",
                "session_id": session_id,
                "customer_id": customer_id,
                "product_id": rng.choice(available_pool),
                "event_type": "product_view",
                "event_at": iso(event_at),
                "dwell_seconds": str(rng.randint(2, 300)),
            })
    return sessions, views, cutoff


def build_transactions(
    config: dict[str, Any],
    rng: random.Random,
    sessions: list[dict[str, str]],
    views: list[dict[str, str]],
    products: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    views_by_session: dict[str, list[str]] = defaultdict(list)
    for view in views:
        views_by_session[view["session_id"]].append(view["product_id"])
    product_map = {row["product_id"]: row for row in products}
    eligible_sessions = [s for s in sessions if views_by_session[s["session_id"]]]
    selected = rng.sample(eligible_sessions, config["orders"])
    carts, cart_lines, orders, order_lines = [], [], [], []
    for index, session in enumerate(selected, 1):
        cart_id = f"CART-{config['year']}-{index:06d}"
        order_id = f"ORD-{config['year']}-{index:06d}"
        candidate_ids = list(dict.fromkeys(views_by_session[session["session_id"]]))
        line_count = min(len(candidate_ids), rng.randint(1, 4))
        chosen = rng.sample(candidate_ids, line_count)
        cart_at = dt(session["started_at"]) + timedelta(minutes=rng.randint(1, 20))
        order_at = max(cart_at, dt(session["ended_at"])) + timedelta(minutes=rng.randint(1, 60))
        carts.append({
            "cart_id": cart_id,
            "session_id": session["session_id"],
            "customer_id": session["customer_id"],
            "created_at": iso(cart_at),
            "status": "converted",
            "converted_order_id": order_id,
        })
        subtotal = Decimal("0")
        line_records = []
        for line_number, product_id in enumerate(chosen, 1):
            quantity = rng.randint(1, 3)
            unit_price = Decimal(product_map[product_id]["unit_price"])
            line_total = unit_price * quantity
            subtotal += line_total
            cart_lines.append({
                "cart_line_id": f"{cart_id}-LINE-{line_number:03d}",
                "cart_id": cart_id,
                "product_id": product_id,
                "quantity": str(quantity),
                "unit_price": money(unit_price),
                "added_at": iso(cart_at + timedelta(seconds=line_number * 10)),
                "lifecycle_state": "purchased",
            })
            line_records.append((line_number, product_id, quantity, unit_price, line_total))
        subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        discount = (
            (subtotal * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if rng.random() < 0.2 else Decimal("0.00")
        )
        tax = ((subtotal - discount) * Decimal("0.08")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        shipping = Decimal("0") if subtotal >= 100 else Decimal("8.00")
        total = (subtotal - discount + tax + shipping).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        orders.append({
            "order_id": order_id,
            "customer_id": session["customer_id"],
            "session_id": session["session_id"],
            "cart_id": cart_id,
            "ordered_at": iso(order_at),
            "status": "completed",
            "subtotal": money(subtotal),
            "discount_amount": money(discount),
            "tax_amount": money(tax),
            "shipping_amount": money(shipping),
            "total_amount": money(total),
            "currency": "USD",
        })
        for line_number, product_id, quantity, unit_price, line_total in line_records:
            order_lines.append({
                "order_line_id": f"{order_id}-LINE-{line_number:03d}",
                "order_id": order_id,
                "product_id": product_id,
                "quantity": str(quantity),
                "unit_price": money(unit_price),
                "line_total": money(line_total),
            })
    return carts, cart_lines, orders, order_lines


def build_relations(
    config: dict[str, Any],
    orders: list[dict[str, str]],
    order_lines: list[dict[str, str]],
    products: list[dict[str, str]],
    cutoff: datetime,
) -> list[dict[str, str]]:
    lines_by_order: dict[str, list[str]] = defaultdict(list)
    for line in order_lines:
        lines_by_order[line["order_id"]].append(line["product_id"])
    pair_counts: Counter[tuple[str, str]] = Counter()
    for order in orders:
        if dt(order["ordered_at"]) >= cutoff:
            continue
        ids = sorted(set(lines_by_order[order["order_id"]]))
        pair_counts.update(itertools.combinations(ids, 2))
    rows = []
    for index, ((left, right), count) in enumerate(pair_counts.most_common(5000), 1):
        rows.append({
            "relation_id": f"REL-{index:07d}",
            "source_product_id": left,
            "related_product_id": right,
            "relation_type": "co_purchase",
            "strength": f"{min(1.0, count / 10):.4f}",
            "support_count": str(count),
            "effective_from": config["start_date"],
            "effective_to": "",
        })
    by_category: dict[str, list[str]] = defaultdict(list)
    for product in products:
        by_category[product["category_id"]].append(product["product_id"])
    for ids in by_category.values():
        sorted_ids = sorted(ids)
        if len(sorted_ids) < 2:
            continue
        for position, source_id in enumerate(sorted_ids):
            related_id = sorted_ids[(position + 1) % len(sorted_ids)]
            index = len(rows) + 1
            rows.append({
                "relation_id": f"REL-{index:07d}",
                "source_product_id": source_id,
                "related_product_id": related_id,
                "relation_type": "same_category",
                "strength": "0.2500",
                "support_count": "0",
                "effective_from": config["start_date"],
                "effective_to": "",
            })
    return rows


def build_recommendations(
    config: dict[str, Any],
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
    views: list[dict[str, str]],
    orders: list[dict[str, str]],
    order_lines: list[dict[str, str]],
    cutoff: datetime,
) -> list[dict[str, str]]:
    train_orders = {row["order_id"]: row for row in orders if dt(row["ordered_at"]) < cutoff}
    order_customer = {order_id: row["customer_id"] for order_id, row in train_orders.items()}
    purchased: dict[str, set[str]] = defaultdict(set)
    popularity: Counter[str] = Counter()
    for line in order_lines:
        if line["order_id"] not in order_customer:
            continue
        customer_id = order_customer[line["order_id"]]
        purchased[customer_id].add(line["product_id"])
        popularity[line["product_id"]] += int(line["quantity"])
    viewed_categories: dict[str, Counter[str]] = defaultdict(Counter)
    product_category = {row["product_id"]: row["category_id"] for row in products}
    for view in views:
        if dt(view["event_at"]) < cutoff:
            viewed_categories[view["customer_id"]][product_category[view["product_id"]]] += 1
    active_products = [p for p in products if p["availability_status"] == "active"]
    globally_ranked = sorted(
        active_products,
        key=lambda p: (popularity[p["product_id"]], p["is_cold_start"] == "true", p["product_id"]),
        reverse=True,
    )
    ranked_by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for product in globally_ranked:
        ranked_by_category[product["category_id"]].append(product)
    active_cold_start = [p for p in active_products if p["is_cold_start"] == "true"]
    rows = []
    k = config.get("recommendations_per_customer", 5)
    for customer in customers:
        customer_id = customer["customer_id"]
        preferred = {cat for cat, _ in viewed_categories[customer_id].most_common(2)}
        candidate_map: dict[str, dict[str, str]] = {
            p["product_id"]: p for p in globally_ranked[: max(100, k * 20)]
        }
        for category_id in preferred:
            for product in ranked_by_category[category_id][: max(50, k * 10)]:
                candidate_map[product["product_id"]] = product
        candidates = [
            p for p in candidate_map.values() if p["product_id"] not in purchased[customer_id]
        ]
        candidates.sort(
            key=lambda p: (
                p["category_id"] in preferred,
                popularity[p["product_id"]],
                p["is_cold_start"] == "true",
                p["product_id"],
            ),
            reverse=True,
        )
        selected = candidates[:k]
        if k >= 5 and active_cold_start and not any(p["is_cold_start"] == "true" for p in selected):
            exploration = active_cold_start[(int(customer_id.split("-")[-1]) - 1) % len(active_cold_start)]
            if exploration["product_id"] not in purchased[customer_id]:
                selected[-1] = exploration
        for rank, product in enumerate(selected, 1):
            base_score = 1 / rank
            rows.append({
                "recommendation_id": f"REC-{len(rows) + 1:09d}",
                "customer_id": customer_id,
                "product_id": product["product_id"],
                "generated_at": iso(cutoff),
                "rank": str(rank),
                "score": f"{base_score:.6f}",
                "reason": (
                    "cold_start_exploration" if product["is_cold_start"] == "true"
                    else "preferred_category" if product["category_id"] in preferred
                    else "popular"
                ),
                "model_version": "rules-v1",
                "split": "test",
            })
    return rows


def calculate_recommendation_metrics(
    tables: dict[str, list[dict[str, str]]], cutoff: datetime
) -> dict[str, Any]:
    """Evaluate cutoff-time recommendations against post-cutoff purchases."""
    order_map = {row["order_id"]: row for row in tables["orders"]}
    test_truth: dict[str, set[str]] = defaultdict(set)
    train_purchases: dict[str, set[str]] = defaultdict(set)
    for line in tables["order_lines"]:
        order = order_map[line["order_id"]]
        target = test_truth if dt(order["ordered_at"]) >= cutoff else train_purchases
        target[order["customer_id"]].add(line["product_id"])

    recs_by_customer: dict[str, list[str]] = defaultdict(list)
    for rec in tables["recommendations"]:
        recs_by_customer[rec["customer_id"]].append(rec["product_id"])

    evaluated_users = sorted(test_truth)
    total_hits = 0
    total_recommended = 0
    total_relevant = 0
    users_with_hit = 0
    for customer_id in evaluated_users:
        predicted = set(recs_by_customer[customer_id])
        relevant = test_truth[customer_id]
        hits = len(predicted & relevant)
        total_hits += hits
        total_recommended += len(predicted)
        total_relevant += len(relevant)
        users_with_hit += int(hits > 0)

    products = {row["product_id"]: row for row in tables["products"]}
    recommended_ids = {row["product_id"] for row in tables["recommendations"]}
    active_ids = {pid for pid, row in products.items() if row["availability_status"] == "active"}
    purchased_violations = sum(
        rec["product_id"] in train_purchases[rec["customer_id"]]
        for rec in tables["recommendations"]
    )
    unavailable_violations = sum(
        products[rec["product_id"]]["availability_status"] != "active"
        for rec in tables["recommendations"]
    )
    cold_start_ids = {pid for pid, row in products.items() if row["is_cold_start"] == "true"}
    total_recs = len(tables["recommendations"])
    return {
        "evaluation_cutoff": iso(cutoff),
        "k": max((int(row["rank"]) for row in tables["recommendations"]), default=0),
        "evaluated_users": len(evaluated_users),
        "precision_at_k": round(total_hits / total_recommended, 6) if total_recommended else 0.0,
        "recall_at_k": round(total_hits / total_relevant, 6) if total_relevant else 0.0,
        "hit_rate_at_k": round(users_with_hit / len(evaluated_users), 6) if evaluated_users else 0.0,
        "catalog_coverage": round(len(recommended_ids & active_ids) / len(active_ids), 6) if active_ids else 0.0,
        "cold_start_recommendation_rate": round(len(recommended_ids & cold_start_ids) / len(cold_start_ids), 6) if cold_start_ids else 0.0,
        "purchased_item_violations": purchased_violations,
        "unavailable_item_violations": unavailable_violations,
        "policy_compliance_rate": round(
            1 - ((purchased_violations + unavailable_violations) / total_recs), 6
        ) if total_recs else 1.0,
    }


def inject_anomalies(
    config: dict[str, Any], tables: dict[str, list[dict[str, str]]]
) -> list[dict[str, str]]:
    truth: list[dict[str, str]] = []
    count = max(1, config.get("anomalies_per_type", 1))
    session_map = {row["session_id"]: row for row in tables["sessions"]}
    for order in tables["orders"][:count]:
        session = session_map[order["session_id"]]
        order["ordered_at"] = iso(dt(session["started_at"]) - timedelta(days=1))
        truth.append({
            "issue_id": f"ISSUE-{len(truth) + 1:05d}", "table_name": "orders",
            "record_id": order["order_id"], "issue_type": "purchase_before_session_view",
            "expected_decision": "flag_temporal_anomaly",
            "details": "Order timestamp is earlier than its originating session.",
        })
    for product in tables["products"][:count]:
        product["category_id"] = ""
        truth.append({
            "issue_id": f"ISSUE-{len(truth) + 1:05d}", "table_name": "products",
            "record_id": product["product_id"], "issue_type": "product_category_missing",
            "expected_decision": "flag_missing_required_fk",
            "details": "Required product category is blank.",
        })
    test_sessions = [row for row in tables["sessions"] if row["split"] == "test"]
    for session in test_sessions[:count]:
        session["split"] = "train"
        truth.append({
            "issue_id": f"ISSUE-{len(truth) + 1:05d}", "table_name": "sessions",
            "record_id": session["session_id"], "issue_type": "test_event_in_training",
            "expected_decision": "exclude_from_training",
            "details": "Post-cutoff session was deliberately labelled train.",
        })
    discontinued = next(p for p in tables["products"] if p["availability_status"] == "discontinued")
    for rec in tables["recommendations"][:count]:
        rec["product_id"] = discontinued["product_id"]
        truth.append({
            "issue_id": f"ISSUE-{len(truth) + 1:05d}", "table_name": "recommendations",
            "record_id": rec["recommendation_id"], "issue_type": "recommendation_discontinued_product",
            "expected_decision": "remove_recommendation",
            "details": "Recommendation deliberately references a discontinued product.",
        })
    return truth


def build_tables(config: dict[str, Any]) -> tuple[dict[str, list[dict[str, str]]], datetime]:
    rng = random.Random(config["seed"])
    categories = build_categories(config)
    customers = build_customers(config, rng)
    products = build_products(config, rng, categories)
    sessions, views, cutoff = build_sessions_and_views(config, rng, customers, products)
    carts, cart_lines, orders, order_lines = build_transactions(
        config, rng, sessions, views, products
    )
    relations = build_relations(config, orders, order_lines, products, cutoff)
    recommendations = build_recommendations(
        config, customers, products, views, orders, order_lines, cutoff
    )
    tables = {
        "categories": categories, "customers": customers, "products": products,
        "sessions": sessions, "page_views": views, "carts": carts,
        "cart_lines": cart_lines, "orders": orders, "order_lines": order_lines,
        "product_relations": relations, "recommendations": recommendations,
    }
    return tables, cutoff


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def sql_value(value: str) -> str:
    if value == "":
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def write_sql_seed(path: Path, tables: dict[str, list[dict[str, str]]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("-- Generated deterministic starter seed\nBEGIN TRANSACTION;\n")
        for table in TABLE_ORDER:
            for row in tables[table]:
                columns = ", ".join(row.keys())
                values = ", ".join(sql_value(value) for value in row.values())
                handle.write(f"INSERT INTO {table} ({columns}) VALUES ({values});\n")
        handle.write("COMMIT;\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_project(config_path: Path, output: Path) -> dict[str, Any]:
    config = load_config(config_path)
    formats = set(config.get("output_formats", ["csv", "jsonl", "sql"]))
    if "csv" not in formats:
        raise ValueError("CSV output is required because validation reads the canonical CSV export")
    unknown_formats = formats - {"csv", "jsonl", "sql"}
    if unknown_formats:
        raise ValueError(f"Unsupported output formats: {sorted(unknown_formats)}")
    if output.exists():
        shutil.rmtree(output)
    csv_dir, json_dir, sql_dir = output / "csv", output / "json", output / "sql"
    csv_dir.mkdir(parents=True, exist_ok=True)
    if "jsonl" in formats:
        json_dir.mkdir(parents=True, exist_ok=True)
    if "sql" in formats:
        sql_dir.mkdir(parents=True, exist_ok=True)
    tables, cutoff = build_tables(config)
    metrics = calculate_recommendation_metrics(tables, cutoff)
    truth = inject_anomalies(config, tables)
    for name in TABLE_ORDER:
        write_csv(csv_dir / f"{name}.csv", tables[name])
        if "jsonl" in formats:
            write_jsonl(json_dir / f"{name}.jsonl", tables[name])
    write_csv(output / "ground_truth.csv", truth)
    if "jsonl" in formats:
        write_jsonl(output / "ground_truth.jsonl", truth)
    if "sql" in formats:
        write_sql_seed(sql_dir / "seed.sql", tables)
    (output / "recommendation_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    checksums = {p.relative_to(output).as_posix(): file_sha256(p) for p in sorted(csv_dir.glob("*.csv"))}
    checksums["ground_truth.csv"] = file_sha256(output / "ground_truth.csv")
    manifest = {
        "seed": config["seed"],
        "config": config,
        "train_test_cutoff": iso(cutoff),
        "source": "fully synthetic; no external dataset used",
        "output_formats": sorted(formats),
        "row_counts": {name: len(tables[name]) for name in TABLE_ORDER},
        "ground_truth_rows": len(truth),
        "recommendation_metrics": metrics,
        "checksums_sha256": checksums,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = validate_directory(output, write_report=True)
    return {
        "table_count": len(TABLE_ORDER),
        "validation_status": report["status"],
        "row_counts": manifest["row_counts"],
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_directory(output: Path, write_report: bool = False) -> dict[str, Any]:
    csv_dir = output / "csv"
    tables = {name: read_csv(csv_dir / f"{name}.csv") for name in TABLE_ORDER}
    truth = read_csv(output / "ground_truth.csv")
    expected = {(row["table_name"], row["record_id"], row["issue_type"]) for row in truth}
    expected_records = {(row["table_name"], row["record_id"]) for row in truth}
    errors: list[dict[str, str]] = []

    def add(table: str, record: str, issue: str, message: str) -> None:
        errors.append({"table": table, "record_id": record, "issue_type": issue, "message": message})

    for table, key in PRIMARY_KEYS.items():
        ids = [row[key] for row in tables[table]]
        for duplicate, count in Counter(ids).items():
            if count > 1:
                add(table, duplicate, "duplicate_primary_key", f"appears {count} times")

    ids = {name: {row[PRIMARY_KEYS[name]] for row in rows} for name, rows in tables.items()}
    fk_rules = [
        ("products", "category_id", "categories"), ("sessions", "customer_id", "customers"),
        ("page_views", "session_id", "sessions"), ("page_views", "customer_id", "customers"),
        ("page_views", "product_id", "products"), ("carts", "session_id", "sessions"),
        ("carts", "customer_id", "customers"), ("cart_lines", "cart_id", "carts"),
        ("cart_lines", "product_id", "products"), ("orders", "customer_id", "customers"),
        ("orders", "session_id", "sessions"), ("orders", "cart_id", "carts"),
        ("order_lines", "order_id", "orders"), ("order_lines", "product_id", "products"),
        ("product_relations", "source_product_id", "products"),
        ("product_relations", "related_product_id", "products"),
        ("recommendations", "customer_id", "customers"), ("recommendations", "product_id", "products"),
    ]
    for child, field, parent in fk_rules:
        for row in tables[child]:
            value = row[field]
            if not value or value not in ids[parent]:
                issue = "product_category_missing" if child == "products" and field == "category_id" and not value else "invalid_foreign_key"
                add(child, row[PRIMARY_KEYS[child]], issue, f"{field}={value!r} not found in {parent}")

    allowed_enums = {
        ("products", "availability_status"): {"active", "unavailable", "discontinued"},
        ("customers", "segment"): {"regular", "sparse", "high_value"},
        ("sessions", "channel"): {"web", "mobile", "app"},
        ("sessions", "split"): {"train", "test"},
        ("carts", "status"): {"active", "abandoned", "converted"},
        ("orders", "status"): {"completed", "cancelled", "refunded"},
        ("product_relations", "relation_type"): {"co_purchase", "same_category"},
    }
    for (table, field), allowed in allowed_enums.items():
        for row in tables[table]:
            if row[field] not in allowed:
                add(table, row[PRIMARY_KEYS[table]], "invalid_enum", f"{field}={row[field]!r}")

    sessions = {row["session_id"]: row for row in tables["sessions"]}
    for session in tables["sessions"]:
        if dt(session["ended_at"]) < dt(session["started_at"]):
            add("sessions", session["session_id"], "invalid_session_order", "session ends before start")
    for view in tables["page_views"]:
        session = sessions[view["session_id"]]
        event_at = dt(view["event_at"])
        if not (dt(session["started_at"]) <= event_at <= dt(session["ended_at"])):
            add("page_views", view["event_id"], "event_outside_session", "event is outside session window")
        if view["customer_id"] != session["customer_id"]:
            add("page_views", view["event_id"], "session_customer_mismatch", "view customer differs from session")
    for order in tables["orders"]:
        if dt(order["ordered_at"]) < dt(sessions[order["session_id"]]["started_at"]):
            add("orders", order["order_id"], "purchase_before_session_view", "order precedes session")

    cutoff = dt(json.loads((output / "manifest.json").read_text(encoding="utf-8"))["train_test_cutoff"])
    for session in tables["sessions"]:
        if dt(session["started_at"]) >= cutoff and session["split"] == "train":
            add("sessions", session["session_id"], "test_event_in_training", "post-cutoff session is train")

    product_status = {row["product_id"]: row["availability_status"] for row in tables["products"]}
    order_by_id = {row["order_id"]: row for row in tables["orders"]}
    order_customer = {order_id: row["customer_id"] for order_id, row in order_by_id.items()}
    purchased_before_cutoff: dict[str, set[str]] = defaultdict(set)
    for line in tables["order_lines"]:
        order = order_by_id[line["order_id"]]
        if dt(order["ordered_at"]) < cutoff:
            purchased_before_cutoff[order_customer[line["order_id"]]].add(line["product_id"])
    for rec in tables["recommendations"]:
        if product_status[rec["product_id"]] == "discontinued":
            add("recommendations", rec["recommendation_id"], "recommendation_discontinued_product", "discontinued SKU recommended")
        elif product_status[rec["product_id"]] == "unavailable":
            add("recommendations", rec["recommendation_id"], "recommendation_unavailable_product", "unavailable SKU recommended")
        if (
            ("recommendations", rec["recommendation_id"]) not in expected_records
            and rec["product_id"] in purchased_before_cutoff[rec["customer_id"]]
        ):
            add("recommendations", rec["recommendation_id"], "recommendation_purchased_product", "previously purchased SKU recommended")

    orders_by_cart = {row["cart_id"]: row["order_id"] for row in tables["orders"]}
    carts_by_id = {row["cart_id"]: row for row in tables["carts"]}
    for cart in tables["carts"]:
        if cart["status"] == "converted" and orders_by_cart.get(cart["cart_id"]) != cart["converted_order_id"]:
            add("carts", cart["cart_id"], "invalid_cart_conversion", "converted order does not match")
        if cart["customer_id"] != sessions[cart["session_id"]]["customer_id"]:
            add("carts", cart["cart_id"], "session_customer_mismatch", "cart customer differs from session")
    for order in tables["orders"]:
        cart = carts_by_id[order["cart_id"]]
        if order["customer_id"] != sessions[order["session_id"]]["customer_id"] or order["customer_id"] != cart["customer_id"]:
            add("orders", order["order_id"], "customer_mismatch", "order customer differs from session/cart")

    recommendation_keys: Counter[tuple[str, str, str]] = Counter(
        (row["customer_id"], row["generated_at"], row["rank"])
        for row in tables["recommendations"]
    )
    for key, count in recommendation_keys.items():
        if count > 1:
            add("recommendations", "|".join(key), "duplicate_recommendation_rank", f"appears {count} times")
    for relation in tables["product_relations"]:
        if relation["source_product_id"] == relation["related_product_id"]:
            add("product_relations", relation["relation_id"], "self_relation", "source equals related product")
        strength = Decimal(relation["strength"])
        if not Decimal("0") <= strength <= Decimal("1"):
            add("product_relations", relation["relation_id"], "invalid_strength", "strength outside 0..1")

    line_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for line in tables["order_lines"]:
        expected_line = Decimal(line["unit_price"]) * int(line["quantity"])
        if Decimal(line["line_total"]) != expected_line.quantize(Decimal("0.01")):
            add("order_lines", line["order_line_id"], "line_total_mismatch", "quantity * unit_price mismatch")
        line_totals[line["order_id"]] += Decimal(line["line_total"])
    for order in tables["orders"]:
        subtotal = line_totals[order["order_id"]].quantize(Decimal("0.01"))
        total = subtotal - Decimal(order["discount_amount"]) + Decimal(order["tax_amount"]) + Decimal(order["shipping_amount"])
        if Decimal(order["subtotal"]) != subtotal or Decimal(order["total_amount"]) != total.quantize(Decimal("0.01")):
            add("orders", order["order_id"], "order_total_mismatch", "header totals do not reconcile")

    observed = {(row["table"], row["record_id"], row["issue_type"]) for row in errors}
    unexpected = [row for row in errors if (row["table"], row["record_id"], row["issue_type"]) not in expected]
    missing_expected = sorted(expected - observed)
    report = {
        "status": "PASS" if not unexpected and not missing_expected else "FAIL",
        "table_row_counts": {name: len(rows) for name, rows in tables.items()},
        "expected_anomaly_count": len(expected),
        "observed_anomaly_count": len(errors),
        "unexpected_error_count": len(unexpected),
        "missing_expected_count": len(missing_expected),
        "unexpected_errors": unexpected,
        "missing_expected": missing_expected,
    }
    if write_report:
        (output / "validation_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def reproducibility_check(config_path: Path, workdir: Path) -> dict[str, Any]:
    first, second = workdir / "repro_run_1", workdir / "repro_run_2"
    generate_project(config_path, first)
    generate_project(config_path, second)
    first_manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    second_manifest = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
    mismatches = {
        name: [digest, second_manifest["checksums_sha256"].get(name)]
        for name, digest in first_manifest["checksums_sha256"].items()
        if second_manifest["checksums_sha256"].get(name) != digest
    }
    report = {
        "status": "PASS" if not mismatches else "FAIL",
        "seed": first_manifest["seed"],
        "row_counts_equal": first_manifest["row_counts"] == second_manifest["row_counts"],
        "checksum_mismatches": mismatches,
    }
    (workdir / "reproducibility_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report

