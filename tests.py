"""
Tests for pdf_address_extractor.extractor
Run:  python tests.py
"""

import textwrap
import unittest
from unittest.mock import patch
from extractor import (
    Address, _parse_inline, _parse_multiline,
    _deduplicate, _INLINE,
)


class TestInlineParsing(unittest.TestCase):

    def test_full_address(self):
        text = "Incident at 742 Evergreen Terrace, Springfield, IL 62704"
        results = _parse_inline(text, page=1)
        self.assertTrue(results)
        a = results[0]
        self.assertIn("Evergreen", a.street)
        self.assertEqual(a.state, "IL")
        self.assertEqual(a.zip_code, "62704")
        self.assertEqual(a.confidence, "high")

    def test_street_only(self):
        text = "Call received at 100 Main Street"
        results = _parse_inline(text, page=2)
        self.assertTrue(results)
        self.assertEqual(results[0].confidence, "low")

    def test_no_match(self):
        text = "Nothing here, just a sentence."
        self.assertEqual(_parse_inline(text, page=1), [])

    def test_page_stored(self):
        text = "999 Oak Avenue, Dallas, TX 75201"
        results = _parse_inline(text, page=5)
        self.assertEqual(results[0].page, 5)


class TestMultilineParsing(unittest.TestCase):

    def test_two_line_address(self):
        text = textwrap.dedent("""\
            456 Maple Drive
            Portland, OR 97201
        """)
        results = _parse_multiline(text, page=1)
        self.assertTrue(results)
        a = results[0]
        self.assertIn("Maple", a.street)
        self.assertEqual(a.state, "OR")
        self.assertEqual(a.zip_code, "97201")

    def test_three_line_address(self):
        text = textwrap.dedent("""\
            1600 Pennsylvania Avenue
            Washington
            DC 20500
        """)
        results = _parse_multiline(text, page=1)
        self.assertTrue(results)
        self.assertEqual(results[0].state, "DC")


class TestDeduplication(unittest.TestCase):

    def test_removes_duplicates(self):
        a1 = Address("123 Main St", city="NYC", state="NY", zip_code="10001")
        a2 = Address("123 Main St", city="NYC", state="NY", zip_code="10001")
        result = _deduplicate([a1, a2])
        self.assertEqual(len(result), 1)

    def test_keeps_distinct(self):
        a1 = Address("123 Main St", city="NYC", state="NY", zip_code="10001")
        a2 = Address("456 Oak Ave", city="LA",  state="CA", zip_code="90001")
        result = _deduplicate([a1, a2])
        self.assertEqual(len(result), 2)


class TestAddressModel(unittest.TestCase):

    def test_full_property(self):
        a = Address("123 Main St", city="Austin", state="TX", zip_code="78701")
        self.assertEqual(a.full, "123 Main St, Austin, TX, 78701")

    def test_to_dict_keys(self):
        a = Address("1 Broadway", city="New York", state="NY", zip_code="10004")
        d = a.to_dict()
        for key in ("street", "city", "state", "zip_code", "full", "page", "confidence"):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
