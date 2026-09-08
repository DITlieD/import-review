import json
from pathlib import Path
import tempfile
import unittest
from test_core import POLICY
from inbox import scan_once


class InboxTests(unittest.TestCase):
    def test_processor_cannot_complete_with_an_empty_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incoming = root / "inbox"
            incoming.mkdir()
            (incoming / "one.csv").write_text("sku,quantity,unit_price\nA,1,2\n")
            policy = root / "policy.json"
            policy.write_text(json.dumps(POLICY))
            def invalid(*args):
                output = root / "out"
                output.mkdir()
                (output / "manifest.json").write_text("{}")
                return output
            result = scan_once(incoming, policy, root / "out", root / "state.json", invalid)
            self.assertEqual(result[0]["status"], "failed")

    def test_completion_skips_unchanged_and_changed_policy_reruns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incoming = root / "inbox"
            incoming.mkdir()
            (incoming / "one.csv").write_text("sku,quantity,unit_price\nA,1,2\n")
            (incoming / "partial.tmp").write_text("ignored")
            policy = root / "policy.json"
            policy.write_text(json.dumps(POLICY))
            calls = []
            def process(source, policy_file, output):
                calls.append(source.read_bytes())
                from import_review import export
                return export(source.read_bytes(), json.loads(policy_file.read_text()), output)
            state = root / "state.json"
            first = scan_once(incoming, policy, root / "out", state, process)
            self.assertEqual(first[0]["status"], "complete")
            self.assertEqual(scan_once(incoming, policy, root / "out", state, process), [])
            policy.write_text(json.dumps(dict(POLICY, version=2)))
            scan_once(incoming, policy, root / "out", state, process)
            self.assertEqual(len(calls), 2)

    def test_failure_is_recorded_and_not_retried_implicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incoming = root / "inbox"
            incoming.mkdir()
            (incoming / "one.csv").write_text("bad")
            policy = root / "policy.json"
            policy.write_text(json.dumps(POLICY))
            calls = []
            def fail(*args):
                calls.append(1)
                raise RuntimeError("model unavailable")
            state = root / "state.json"
            result = scan_once(incoming, policy, root / "out", state, fail)
            self.assertEqual(result[0]["status"], "failed")
            self.assertEqual(scan_once(incoming, policy, root / "out", state, fail), [])
            scan_once(incoming, policy, root / "out", state, fail, retry_failed=True)
            self.assertEqual(len(calls), 2)
