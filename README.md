# 📄 pdf-address-extractor

> Extract structured address data from PDF files — with a web interface, CLI, and Python API.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

Handles both **inline addresses** (`123 Main St, Austin, TX 78701`) and **multi-line address blocks** (street on one line, city/state/zip on the next). Results export to CSV or JSON.

---

## 🖥️ Web Interface

![Demo screenshot](screenshot.png)

---

## 🚀 Quick Start

### 1 — Clone and install

```bash
git clone https://github.com/HalisonBruno/pdf-address-extractor.git
cd pdf-address-extractor
pip install -r requirements.txt
```

### 2 — Run the web interface

```bash
python app.py
```

Open **http://localhost:5000**, drag your PDF in, and download the results.

### 3 — Or run the terminal demo (no PDF needed)

```bash
python demo.py
```

Generates a sample PDF with 10 incident addresses, extracts them all, and saves `addresses.csv` + `addresses.json`.

---

## 💻 CLI

```bash
# Print results as a table
python cli.py report.pdf

# Save as CSV
python cli.py report.pdf --out results.csv

# Save as JSON
python cli.py report.pdf --out results.json

# High-confidence results only (full address found)
python cli.py report.pdf --confidence high --out results.csv
```

---

## 🐍 Python API

```python
from extractor import extract

addresses = extract("report.pdf")

for a in addresses:
    print(a.full)        # "742 Evergreen Terrace, Springfield, IL, 62704"
    print(a.street)      # "742 Evergreen Terrace"
    print(a.city)        # "Springfield"
    print(a.state)       # "IL"
    print(a.zip_code)    # "62704"
    print(a.page)        # 1
    print(a.confidence)  # "high" | "medium" | "low"
    print(a.to_dict())   # all fields as a plain dict
```

---

## 📊 Confidence Levels

| Level | Meaning |
|-------|---------|
| `high` | Street + city + state + zip all found |
| `medium` | Street + at least state or zip |
| `low` | Street number and name only |

---

## 📁 Output Columns

| Column | Example |
|--------|---------|
| `street` | `742 Evergreen Terrace` |
| `city` | `Springfield` |
| `state` | `IL` |
| `zip_code` | `62704` |
| `full` | `742 Evergreen Terrace, Springfield, IL, 62704` |
| `raw_text` | original matched text from the PDF |
| `page` | `1` |
| `confidence` | `high` |

---

## 🧪 Tests

```bash
python tests.py
```

10 tests, all passing.

---

## 📦 Project Structure

```
pdf-address-extractor/
├── app.py           # Web interface (Flask)
├── extractor.py     # Core extraction logic
├── cli.py           # Command-line interface
├── demo.py          # Terminal demo with auto-generated sample PDF
├── tests.py         # Unit tests
├── requirements.txt
└── README.md
```

---

## License

MIT
