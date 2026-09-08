import tempfile
from pathlib import Path
import unittest
from test_core import POLICY
from workflow import ImportSession


class WorkflowTests(unittest.TestCase):
    def test_export_requires_validation_and_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ImportSession(b"Code,Qty,Price\nA,1,2\n", POLICY, Path(directory))
            with self.assertRaises(ValueError):
                session.export_result()
            with self.assertRaises(ValueError):
                session.propose_mapping({"sku": "Code", "quantity": "Qty", "unit_price": "Price"})
            session.read_policy()
            session.inspect_csv()
            session.propose_mapping({"sku": "Code", "quantity": "Qty", "unit_price": "Price"})
            summary = session.validate_import()
            self.assertEqual(summary["accepted"], 1)
            self.assertTrue(Path(session.export_result()["directory"]).is_dir())
            self.assertEqual([e["tool"] for e in session.trace], [
                "read_policy", "inspect_csv", "propose_mapping", "validate_import", "export_result"])

    def test_unapproved_mapping_and_changed_mapping_invalidate(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ImportSession(b"sku,quantity,unit_price\nA,1,2\n", POLICY, Path(directory))
            session.read_policy()
            session.inspect_csv()
            session.propose_mapping({"sku": "sku", "quantity": "quantity", "unit_price": "unit_price"})
            session.validate_import()
            with self.assertRaises(ValueError):
                session.propose_mapping({"sku": "quantity", "quantity": "sku", "unit_price": "unit_price"})
            with self.assertRaises(ValueError):
                session.export_result()

    def test_unmapped_file_can_be_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ImportSession(b"unknown\nx\n", POLICY, Path(directory))
            session.read_policy()
            session.inspect_csv()
            result = session.validate_import()
            self.assertEqual(result["review"], 1)
            session.export_result()

    def test_constructor_snapshots_policy(self):
        import copy
        with tempfile.TemporaryDirectory() as directory:
            policy = copy.deepcopy(POLICY)
            session = ImportSession(b"sku,quantity,unit_price\nA,1,2\n", policy, Path(directory))
            policy["columns"]["sku"] = ["oops"]
            self.assertIn("sku", session.read_policy()["columns"]["sku"])
