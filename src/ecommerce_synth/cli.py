from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import generate_project, reproducibility_check, validate_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecommerce-synth",
        description="Generate and validate reproducible synthetic e-commerce data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="Generate CSV, JSONL and SQL seed data")
    generate.add_argument("--config", default="config/starter.json")
    generate.add_argument("--output", default="data/generated")

    validate = sub.add_parser("validate", help="Validate an existing generated dataset")
    validate.add_argument("--input", default="data/generated")

    reproduce = sub.add_parser("reproduce", help="Generate twice and compare checksums")
    reproduce.add_argument("--config", default="config/starter.json")
    reproduce.add_argument("--workdir", default="data")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "generate":
        summary = generate_project(Path(args.config), Path(args.output))
        print(f"Generated {summary['table_count']} tables in {args.output}")
        print(f"Validation status: {summary['validation_status']}")
    elif args.command == "validate":
        report = validate_directory(Path(args.input), write_report=True)
        print(f"Validation status: {report['status']}")
        print(f"Unexpected errors: {report['unexpected_error_count']}")
        if report["status"] != "PASS":
            raise SystemExit(1)
    else:
        report = reproducibility_check(Path(args.config), Path(args.workdir))
        print(f"Reproducibility status: {report['status']}")
        if report["status"] != "PASS":
            raise SystemExit(1)

