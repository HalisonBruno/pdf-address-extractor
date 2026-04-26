"""
pdf-address-extractor  –  CLI
Usage:
    python cli.py input.pdf
    python cli.py input.pdf --out results.json
    python cli.py input.pdf --format csv
    python cli.py input.pdf --confidence high
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from extractor import extract, Address


def _to_csv(addresses: list[Address], out_path: str) -> None:
    fields = ["street", "city", "state", "zip_code", "full", "page", "confidence"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(a.to_dict() for a in addresses)


def _to_json(addresses: list[Address], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in addresses], f, indent=2)


def _print_table(addresses: list[Address]) -> None:
    if not addresses:
        print("No addresses found.")
        return

    col_w = {"street": 35, "city": 20, "state": 5, "zip": 10, "pg": 4, "conf": 7}
    header = (
        f"{'STREET':<{col_w['street']}} "
        f"{'CITY':<{col_w['city']}} "
        f"{'ST':<{col_w['state']}} "
        f"{'ZIP':<{col_w['zip']}} "
        f"{'PG':<{col_w['pg']}} "
        f"{'CONF':<{col_w['conf']}}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for a in addresses:
        print(
            f"{a.street[:col_w['street']]:<{col_w['street']}} "
            f"{a.city[:col_w['city']]:<{col_w['city']}} "
            f"{a.state:<{col_w['state']}} "
            f"{a.zip_code:<{col_w['zip']}} "
            f"{a.page:<{col_w['pg']}} "
            f"{a.confidence:<{col_w['conf']}}"
        )
    print(sep)
    print(f"Total: {len(addresses)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pdf-address-extractor",
        description="Extract structured address data from PDF files.",
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument(
        "--out", "-o", metavar="FILE",
        help="Output file path (auto-detects format from extension)",
    )
    parser.add_argument(
        "--format", "-f", choices=["csv", "json", "table"],
        default="table", help="Output format when --out is not set (default: table)",
    )
    parser.add_argument(
        "--confidence", "-c", choices=["high", "medium", "low", "all"],
        default="all", help="Filter by confidence level (default: all)",
    )
    args = parser.parse_args()

    try:
        addresses = extract(args.pdf)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter by confidence
    if args.confidence != "all":
        levels = {"high": {"high"}, "medium": {"high", "medium"}, "low": {"high", "medium", "low"}}
        keep = levels[args.confidence]
        addresses = [a for a in addresses if a.confidence in keep]

    # Output
    if args.out:
        out = Path(args.out)
        if out.suffix.lower() == ".json":
            _to_json(addresses, str(out))
        else:
            _to_csv(addresses, str(out))
        print(f"Saved {len(addresses)} address(es) to {out}")
    else:
        if args.format == "json":
            print(json.dumps([a.to_dict() for a in addresses], indent=2))
        elif args.format == "csv":
            import io
            import csv as _csv
            buf = io.StringIO()
            fields = ["street", "city", "state", "zip_code", "full", "page", "confidence"]
            w = _csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(a.to_dict() for a in addresses)
            print(buf.getvalue())
        else:
            _print_table(addresses)


if __name__ == "__main__":
    main()
