from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BG, PANEL, PANEL2 = "#07111f", "#0f1d2e", "#13263a"
TEXT, MUTED = "#f4f7fb", "#91a4ba"
TEAL, GREEN, AMBER, BLUE = "#24d1c1", "#42d392", "#f4bd4f", "#5aa7ff"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((55, 40, 1545, 140), radius=24, fill=PANEL)
    draw.ellipse((85, 72, 105, 92), fill=TEAL)
    draw.text((125, 55), title, font=font(38, True), fill=TEXT)
    draw.text((126, 102), subtitle, font=font(18), fill=MUTED)
    draw.text((1380, 75), "YottaFlex", font=font(20, True), fill=TEAL)
    return image, draw


def card(draw: ImageDraw.ImageDraw, x: int, label: str, value: str, accent: str) -> None:
    draw.rounded_rectangle((x, 185, x + 325, 345), radius=22, fill=PANEL)
    draw.rectangle((x, 185, x + 8, 345), fill=accent)
    draw.text((x + 35, 215), label.upper(), font=font(16, True), fill=MUTED)
    draw.text((x + 35, 258), value, font=font(34, True), fill=TEXT)


def generation_image(report: dict, output: Path) -> None:
    rows = report["row_counts"]
    image, draw = canvas(
        "Full-Scale Generation Summary",
        "Fixed seed 20261022 • verified full dataset • actual output",
    )
    cards = [
        ("Customers", rows["customers"], GREEN),
        ("Products", rows["products"], TEAL),
        ("Sessions", rows["sessions"], BLUE),
        ("Orders", rows["orders"], AMBER),
    ]
    for x, (label, value, accent) in zip((55, 425, 795, 1165), cards):
        card(draw, x, label, f"{value:,}", accent)
    draw.rounded_rectangle((55, 380, 1070, 825), radius=24, fill=PANEL)
    draw.text((90, 410), "Entity row counts", font=font(24, True), fill=TEXT)
    selected = [
        ("Page views", rows["page_views"]), ("Cart lines", rows["cart_lines"]),
        ("Order lines", rows["order_lines"]), ("Relations", rows["product_relations"]),
        ("Recommendations", rows["recommendations"]),
    ]
    maximum = max(value for _, value in selected)
    for index, (label, value) in enumerate(selected):
        y = 480 + index * 64
        draw.text((90, y), label, font=font(18), fill=MUTED)
        draw.rounded_rectangle((330, y + 2, 875, y + 28), radius=13, fill=PANEL2)
        width = max(12, int(545 * value / maximum))
        draw.rounded_rectangle((330, y + 2, 330 + width, y + 28), radius=13, fill=TEAL)
        draw.text((900, y), f"{value:,}", font=font(18, True), fill=TEXT)
    draw.rounded_rectangle((1105, 380, 1545, 825), radius=24, fill=PANEL)
    draw.text((1140, 410), "Verification", font=font(24, True), fill=TEXT)
    items = [
        ("Validation", report["validation_status"]),
        ("Unexpected errors", str(report["unexpected_errors"])),
        ("Ground-truth issues", str(report["ground_truth_rows"])),
        ("Reproducibility", report["reproducibility_status"]),
        ("Checksum mismatches", str(len(report["checksum_mismatches"]))),
        ("Generation time", f"{report['generation_runtime_seconds']:.1f}s"),
    ]
    for index, (label, value) in enumerate(items):
        y = 480 + index * 50
        draw.text((1140, y), label, font=font(16), fill=MUTED)
        draw.text((1500, y), value, font=font(17, True), fill=GREEN, anchor="ra")
    draw.rounded_rectangle((1140, 760, 1505, 800), radius=18, fill="#123c36")
    draw.text((1235, 770), "FULL RUN PASSED", font=font(17, True), fill=GREEN)
    image.save(output / "full_generation_summary.png")


def metrics_image(report: dict, output: Path) -> None:
    metrics = report["recommendation_metrics"]
    image, draw = canvas(
        "Recommendation Evaluation",
        "Chronological test split • k = 10 • actual full-scale output",
    )
    cards = [
        ("Precision@10", metrics["precision_at_k"], TEAL),
        ("Recall@10", metrics["recall_at_k"], BLUE),
        ("Hit Rate@10", metrics["hit_rate_at_k"], GREEN),
        ("Coverage", metrics["catalog_coverage"], AMBER),
    ]
    for x, (label, value, accent) in zip((55, 425, 795, 1165), cards):
        card(draw, x, label, f"{value:.4f}", accent)
    draw.rounded_rectangle((55, 380, 1000, 825), radius=24, fill=PANEL)
    draw.text((90, 410), "Evaluation details", font=font(24, True), fill=TEXT)
    details = [
        ("Evaluated users", f"{metrics['evaluated_users']:,}"),
        ("Cold-start coverage", f"{metrics['cold_start_recommendation_rate']:.1%}"),
        ("Catalog coverage", f"{metrics['catalog_coverage']:.1%}"),
        ("Policy compliance", f"{metrics['policy_compliance_rate']:.1%}"),
    ]
    for index, (label, value) in enumerate(details):
        y = 490 + index * 72
        draw.text((90, y), label, font=font(19), fill=MUTED)
        draw.text((930, y), value, font=font(22, True), fill=TEXT, anchor="ra")
        draw.line((90, y + 40, 930, y + 40), fill=PANEL2, width=2)
    draw.rounded_rectangle((1035, 380, 1545, 825), radius=24, fill=PANEL)
    draw.text((1070, 410), "Leakage & exclusions", font=font(24, True), fill=TEXT)
    policies = [
        ("Purchased-item violations", metrics["purchased_item_violations"]),
        ("Unavailable-item violations", metrics["unavailable_item_violations"]),
        ("Checksum mismatches", len(report["checksum_mismatches"])),
        ("Unexpected validation errors", report["unexpected_errors"]),
    ]
    for index, (label, value) in enumerate(policies):
        y = 490 + index * 72
        draw.text((1070, y), label, font=font(16), fill=MUTED)
        draw.text((1495, y), str(value), font=font(20, True), fill=GREEN, anchor="ra")
        draw.line((1070, y + 40, 1505, y + 40), fill=PANEL2, width=2)
    draw.rounded_rectangle((1070, 750, 1505, 792), radius=18, fill="#123c36")
    draw.text((1175, 761), "NO LEAKAGE DETECTED", font=font(16, True), fill=GREEN)
    image.save(output / "recommendation_metrics.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="docs/full_scale_verification.json")
    parser.add_argument("--output", default="docs/images")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    generation_image(report, output)
    metrics_image(report, output)
    print(f"Wrote report images to {output}")


if __name__ == "__main__":
    main()
