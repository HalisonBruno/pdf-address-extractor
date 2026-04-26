"""
demo.py  –  PDF Address Extractor  |  Executable Demo
=====================================================
Run this file to see the extractor in action.
It creates a sample PDF and extracts all addresses from it.

    python demo.py
"""

import json
import sys
from pathlib import Path

# ── 1. Create a sample PDF ─────────────────────────────────────────────────

def create_sample_pdf(path: str) -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        print("  Installing reportlab...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "reportlab", "-q", "--break-system-packages"])
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    # ── Page 1: inline addresses ──────────────────────────────────────────
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h - 50, "DAILY INCIDENT REPORT  –  Page 1")
    c.setFont("Helvetica", 11)

    incidents_p1 = [
        ("INC-001", "10:32", "742 Evergreen Terrace, Springfield, IL 62704",  "Noise complaint"),
        ("INC-002", "11:15", "1600 Pennsylvania Avenue, Washington, DC 20500","Security alert"),
        ("INC-003", "13:47", "221B Baker Street, London, CA 90210",           "Trespassing"),
        ("INC-004", "14:05", "4 Privet Drive, Little Whinging, CA 94102",     "Disturbance"),
        ("INC-005", "15:22", "1 Infinite Loop, Cupertino, CA 95014",          "Vandalism"),
    ]

    y = h - 100
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, f"{'ID':<10} {'TIME':<8} {'ADDRESS':<50} {'TYPE'}")
    c.line(50, y - 5, 560, y - 5)
    c.setFont("Helvetica", 10)

    for inc_id, time, addr, kind in incidents_p1:
        y -= 22
        c.drawString(50,  y, inc_id)
        c.drawString(110, y, time)
        c.drawString(170, y, addr)
        c.drawString(480, y, kind)

    c.showPage()

    # ── Page 2: multi-line address blocks ────────────────────────────────
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h - 50, "DAILY INCIDENT REPORT  –  Page 2")
    c.setFont("Helvetica", 11)

    incidents_p2 = [
        ("INC-006", "09:10", ["350 Fifth Avenue",          "New York, NY 10118"],     "Break-in"),
        ("INC-007", "10:55", ["1000 Colonial Farm Road",   "McLean, VA 22101"],       "Suspicious activity"),
        ("INC-008", "12:30", ["1 Microsoft Way",           "Redmond, WA 98052"],      "Alarm triggered"),
        ("INC-009", "14:15", ["1600 Amphitheatre Pkwy",    "Mountain View, CA 94043"],"Access violation"),
        ("INC-010", "16:45", ["410 Terry Avenue North",    "Seattle, WA 98109"],      "Vandalism"),
    ]

    y = h - 100
    for inc_id, time, addr_lines, kind in incidents_p2:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, f"{inc_id}  |  {time}  |  {kind}")
        c.setFont("Helvetica", 10)
        for line in addr_lines:
            y -= 16
            c.drawString(70, y, line)
        y -= 26

    c.save()


# ── 2. Run extraction and print results ────────────────────────────────────

def print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def run_demo() -> None:
    print("\n" + "=" * 60)
    print("  PDF ADDRESS EXTRACTOR  –  Live Demo")
    print("=" * 60)

    # Create sample PDF
    pdf_path = "sample_report.pdf"
    print_section("Step 1 / 3  –  Creating sample PDF")
    create_sample_pdf(pdf_path)
    print(f"  ✓  Created: {pdf_path}")

    # Import extractor
    print_section("Step 2 / 3  –  Extracting addresses")
    from extractor import extract
    addresses = extract(pdf_path)

    # Show results
    print_section("Step 3 / 3  –  Results")
    print(f"\n  Found {len(addresses)} unique address(es)\n")

    col = {"street": 34, "city": 18, "st": 4, "zip": 10, "pg": 4, "conf": 7}
    header = (
        f"  {'STREET':<{col['street']}} "
        f"{'CITY':<{col['city']}} "
        f"{'ST':<{col['st']}} "
        f"{'ZIP':<{col['zip']}} "
        f"{'PG':<{col['pg']}} "
        f"CONF"
    )
    print(header)
    print("  " + "-" * 84)

    for a in addresses:
        conf_icon = "●" if a.confidence == "high" else ("◑" if a.confidence == "medium" else "○")
        print(
            f"  {a.street[:col['street']]:<{col['street']}} "
            f"{a.city[:col['city']]:<{col['city']}} "
            f"{a.state:<{col['st']}} "
            f"{a.zip_code:<{col['zip']}} "
            f"{a.page:<{col['pg']}} "
            f"{conf_icon} {a.confidence}"
        )

    print("\n  Confidence legend:  ● high (full address)  ◑ medium  ○ low (street only)")

    # Save outputs
    print_section("Saving output files")
    from extractor import Address
    import csv

    csv_path = "addresses.csv"
    fields = ["street", "city", "state", "zip_code", "full", "page", "confidence"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(a.to_dict() for a in addresses)

    json_path = "addresses.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in addresses], f, indent=2)

    print(f"  ✓  CSV   →  {csv_path}")
    print(f"  ✓  JSON  →  {json_path}")

    print("\n" + "=" * 60)
    print("  Demo complete.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_demo()
