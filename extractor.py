"""
PDF Address Extractor
Extracts structured address data from PDF files using multiple strategies.
"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import pdfplumber
from pypdf import PdfReader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Address:
    street: str
    city: str = ""
    state: str = ""
    zip_code: str = ""
    raw_text: str = ""
    page: int = 0
    confidence: str = "high"      # high | medium | low

    @property
    def full(self) -> str:
        parts = [self.street]
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.zip_code:
            parts.append(self.zip_code)
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "street":     self.street,
            "city":       self.city,
            "state":      self.state,
            "zip_code":   self.zip_code,
            "full":       self.full,
            "raw_text":   self.raw_text,
            "page":       self.page,
            "confidence": self.confidence,
        }


# ── Regex patterns ─────────────────────────────────────────────────────────

# Street suffixes (abbreviated and full)
_SUFFIXES = (
    r"(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Rd|Road|Dr(?:ive)?|"
    r"Ln|Lane|Way|Cir(?:cle)?|Ct|Court|Pkwy|Parkway|Pl(?:ace)?|"
    r"Ter(?:race)?|Hwy|Highway|Fwy|Freeway|Loop|Run|Trl|Trail)"
)

# Full inline address:  "123 Main St, San Francisco, CA 94102"
_INLINE = re.compile(
    r"(\d{1,5}[A-Za-z]?\s+[A-Za-z0-9 .#\-']+?" + _SUFFIXES + r"\.?)"
    r"(?:[,\s]+([A-Za-z ]{2,30}))?"          # city
    r"(?:[,\s]+([A-Z]{2}))?"                  # state
    r"(?:[,\s]+(\d{5}(?:-\d{4})?))?",        # zip
    re.IGNORECASE,
)

# State + zip on their own line (multi-line addresses)
_STATE_ZIP = re.compile(r"\b([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\b")

# City, State  Zip  (city on the same chunk)
_CITY_STATE_ZIP = re.compile(
    r"([A-Za-z][A-Za-z .'-]{1,28}),?\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)"
)


# ── Text extraction ────────────────────────────────────────────────────────

def _extract_pages_pdfplumber(path: str) -> list[tuple[int, str]]:
    """Primary extractor – preserves layout well."""
    pages = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                pages.append((i, text))
    except Exception as exc:
        log.warning("pdfplumber failed (%s), falling back to pypdf", exc)
        pages = _extract_pages_pypdf(path)
    return pages


def _extract_pages_pypdf(path: str) -> list[tuple[int, str]]:
    """Fallback extractor."""
    pages = []
    reader = PdfReader(path)
    for i, page in enumerate(reader.pages, start=1):
        pages.append((i, page.extract_text() or ""))
    return pages


# ── Address parsing ────────────────────────────────────────────────────────

def _parse_inline(text: str, page: int) -> list[Address]:
    """Try to find complete addresses on a single line."""
    results = []
    for m in _INLINE.finditer(text):
        street   = m.group(1).strip().title()
        city     = (m.group(2) or "").strip().title()
        state    = (m.group(3) or "").strip().upper()
        zip_code = (m.group(4) or "").strip()

        if len(street) < 8:
            continue

        # Skip if street looks like a header fragment
        if _HEADER_WORDS.search(street):
            continue

        confidence = "high" if (city and state and zip_code) else \
                     "medium" if (state or zip_code) else "low"

        results.append(Address(
            street=street, city=city, state=state,
            zip_code=zip_code, raw_text=m.group(0).strip(),
            page=page, confidence=confidence,
        ))
    return results


_HEADER_WORDS = re.compile(
    r"\b(id|time|addr|address|type|incident|date|report|page)\b", re.IGNORECASE
)


def _parse_multiline(text: str, page: int) -> list[Address]:
    """
    Handle multi-line address blocks common in incident/form PDFs:

        123 Main Street
        San Francisco, CA 94102
    """
    results = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        # Does this line look like a street?
        street_match = re.match(
            r"^(\d{1,5}[A-Za-z]?\s+[A-Za-z0-9 .#\-']+?" + _SUFFIXES + r"\.?)$",
            line, re.IGNORECASE
        )
        if not street_match:
            continue

        # Skip lines that are clearly table headers, not addresses
        if _HEADER_WORDS.search(line) and not re.search(r"^\d+", line):
            continue

        street = street_match.group(1).strip().title()

        # Look at the next 1-2 lines for city/state/zip
        city = state = zip_code = ""
        for j in range(i + 1, min(i + 3, len(lines))):
            csz = _CITY_STATE_ZIP.search(lines[j])
            if csz:
                city     = csz.group(1).strip().title()
                state    = csz.group(2).strip().upper()
                zip_code = csz.group(3).strip()
                break
            sz = _STATE_ZIP.search(lines[j])
            if sz:
                state    = sz.group(1).strip().upper()
                zip_code = sz.group(2).strip()
                break

        confidence = "high" if (city and state and zip_code) else \
                     "medium" if (state or zip_code) else "low"

        results.append(Address(
            street=street, city=city, state=state,
            zip_code=zip_code, raw_text=line,
            page=page, confidence=confidence,
        ))
    return results


def _deduplicate(addresses: list[Address]) -> list[Address]:
    seen: set[str] = set()
    unique = []
    for addr in addresses:
        key = addr.full.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(addr)
    return unique


# ── Public API ─────────────────────────────────────────────────────────────

def extract(pdf_path: str) -> list[Address]:
    """
    Extract all addresses from a PDF file.

    Returns a deduplicated list of Address objects sorted by page number.
    Confidence levels: 'high' (street + city + state + zip),
                       'medium' (street + state or zip),
                       'low'    (street only).
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    log.info("Extracting addresses from: %s", path.name)
    pages = _extract_pages_pdfplumber(str(path))

    all_addresses: list[Address] = []
    for page_num, text in pages:
        if not text.strip():
            log.debug("Page %d: no text found", page_num)
            continue
        found_inline     = _parse_inline(text, page_num)
        found_multiline  = _parse_multiline(text, page_num)
        # prefer inline matches; multiline fills gaps
        if found_inline:
            all_addresses.extend(found_inline)
        else:
            all_addresses.extend(found_multiline)

    result = _deduplicate(all_addresses)
    result.sort(key=lambda a: a.page)

    counts = {"high": 0, "medium": 0, "low": 0}
    for a in result:
        counts[a.confidence] += 1

    log.info(
        "Found %d unique addresses across %d page(s) "
        "[high=%d medium=%d low=%d]",
        len(result), len(pages),
        counts["high"], counts["medium"], counts["low"],
    )
    return result
