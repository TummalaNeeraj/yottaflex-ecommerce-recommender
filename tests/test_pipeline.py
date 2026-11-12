import json
import tempfile
import unittest
from pathlib import Path

from ecommerce_synth.pipeline import generate_project, read_csv, validate_directory


class PipelineTests(unittest.TestCase):
    def test_starter_generation_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            config = {
                "seed": 20261022,
                "year": 2026,
                "start_date": "2026-01-01T00:00:00",
                "end_date": "2026-01-31T23:59:59",
                "customers": 30,
                "products": 25,
                "categories": 6,
                "sessions": 80,
                "orders": 20,
                "recommendations_per_customer": 3,
                "anomalies_per_type": 1,
            }
            config_path = tmp_path / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            output = tmp_path / "generated"
            result = generate_project(config_path, output)
            self.assertEqual(result["validation_status"], "PASS")
            self.assertEqual(len(list((output / "csv").glob("*.csv"))), 11)
            self.assertEqual(validate_directory(output)["unexpected_error_count"], 0)

            metrics = json.loads((output / "recommendation_metrics.json").read_text())
            self.assertEqual(metrics["purchased_item_violations"], 0)
            self.assertEqual(metrics["unavailable_item_violations"], 0)
            self.assertEqual(metrics["policy_compliance_rate"], 1.0)

            issue_types = {row["issue_type"] for row in read_csv(output / "ground_truth.csv")}
            self.assertEqual(issue_types, {
                "purchase_before_session_view",
                "product_category_missing",
                "test_event_in_training",
                "recommendation_discontinued_product",
            })

    def test_same_seed_produces_same_customer_file(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            source = Path("config/starter.json")
            out_a, out_b = tmp_path / "a", tmp_path / "b"
            generate_project(source, out_a)
            generate_project(source, out_b)
            self.assertEqual(
                (out_a / "csv/customers.csv").read_bytes(),
                (out_b / "csv/customers.csv").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()

