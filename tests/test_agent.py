from pathlib import Path
import tempfile
import unittest
from test_core import POLICY
from workflow import ImportSession
from agent_runner import build_tools, RequestLimit


class AdapterTests(unittest.TestCase):
    def test_request_limit(self):
        from types import SimpleNamespace
        limit = RequestLimit(2)
        for _ in range(2):
            event = SimpleNamespace(cancel=False)
            limit.before_call(event)
            self.assertFalse(event.cancel)
        event = SimpleNamespace(cancel=False)
        limit.before_call(event)
        self.assertTrue(event.cancel)

    def test_registered_tools_are_bound_and_mapping_has_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            session = ImportSession(b"sku,quantity,unit_price\nA,1,2\n", POLICY, Path(directory))
            tools = build_tools(session)
            self.assertEqual({t.tool_name for t in tools}, {
                "read_policy", "inspect_csv", "propose_mapping", "validate_import", "export_result"})
            mapping = next(t for t in tools if t.tool_name == "propose_mapping")
            schema = mapping.tool_spec["inputSchema"]["json"]
            self.assertIn("mapping", schema["required"])
