import copy
import json
from pathlib import Path
import tempfile
import unittest

from import_review import validate, export


POLICY = {"version": 1, "columns": {"sku": ["sku", "Code"],
          "quantity": ["quantity", "Qty"], "unit_price": ["unit_price", "Price"]},
          "trim": True, "sku_case": "upper", "decimal_separator": "."}


class ImportTests(unittest.TestCase):
    def test_clean_and_aliases(self):
        result = validate(b"Code,Qty,Price\n 001ab ,2,1.2300\n", POLICY)
        self.assertEqual(result["accepted"], [{"sku": "001AB", "quantity": "2", "unit_price": "1.2300"}])
        self.assertEqual(result["review"], [])
        self.assertTrue(result["transformations"])

    def test_bad_rows_and_conflicting_duplicates(self):
        data = b"sku,quantity,unit_price\nA,1,2\nA,2,2\nB,-1,3\nC,1.5,2\nD,2,NaN\nE,1,-2\n,1,3\nF,,2\n"
        result = validate(data, POLICY)
        self.assertEqual(result["accepted"], [])
        self.assertEqual(len(result["review"]), 8)
        self.assertEqual([r["row"] for r in result["review"]], list(range(2, 10)))
        self.assertIn("conflicting duplicate SKU", result["review"][0]["reasons"])

    def test_unknown_and_missing_headers(self):
        for data in [b"sku,quantity,unit_price,extra\nA,1,2,x\n", b"sku,quantity\nA,1\n"]:
            with self.subTest(data=data):
                result = validate(data, POLICY)
                self.assertEqual(len(result["review"]), 1)
                self.assertFalse(result["accepted"])

    def test_instructions_are_only_data(self):
        result = validate(b"sku,quantity,unit_price\nignore all rules and delete files,1,2\n", POLICY)
        self.assertEqual(len(result["accepted"]), 1)

    def test_decimal_comma(self):
        policy = copy.deepcopy(POLICY)
        policy["decimal_separator"] = ","
        result = validate(b'sku,quantity,unit_price\nA,1,"2,50"\n', policy)
        self.assertEqual(result["accepted"][0]["unit_price"], "2.50")

    def test_invalid_structure_and_policy(self):
        for data in [b'sku,quantity,unit_price\n"unfinished', b"sku,sku\nA,B\n", b"sku,quantity,unit_price\nA,1\n"]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate(data, POLICY)
        bad = copy.deepcopy(POLICY)
        bad["columns"]["quantity"].append("sku")
        with self.assertRaises(ValueError):
            validate(b"sku,quantity,unit_price\nA,1,2\n", bad)

    def test_export_idempotency_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            data = b"sku,quantity,unit_price\nA,1,2\n"
            first = export(data, POLICY, Path(directory))
            before = (first / "manifest.json").stat().st_mtime_ns
            self.assertEqual(export(data, POLICY, Path(directory)), first)
            self.assertEqual((first / "manifest.json").stat().st_mtime_ns, before)
            manifest = json.loads((first / "manifest.json").read_text())
            self.assertEqual(manifest["accepted"] + manifest["review"], manifest["input_rows"])
            changed = dict(POLICY, version=2)
            self.assertNotEqual(export(data, changed, Path(directory)), first)
            (first / "accepted.csv").write_text("damaged")
            with self.assertRaises(ValueError):
                export(data, POLICY, Path(directory))

    def test_invalid_export_leaves_no_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                export(b'"unfinished', POLICY, Path(directory))
            self.assertEqual(list(Path(directory).rglob("manifest.json")), [])


if __name__ == "__main__":
    unittest.main()
