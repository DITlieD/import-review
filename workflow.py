"""Bound job state shared by validation tools and the Strands adapter."""
import copy
import csv
import io
from pathlib import Path
from import_review import FIELDS, export, policy_bytes, validate


class ImportSession:
    def __init__(self, data: bytes, policy: dict, output: Path):
        policy_bytes(policy)
        self._data = bytes(data)
        self._policy = copy.deepcopy(policy)
        self._output = Path(output)
        self._read = False
        self._headers = None
        self._mapping = None
        self._result = None
        self.directory = None
        self.trace = []

    def _record(self, tool, result):
        self.trace.append({"tool": tool, "result": copy.deepcopy(result)})
        return copy.deepcopy(result)

    def read_policy(self) -> dict:
        """Read the immutable supplier rules for this job."""
        self._read = True
        return self._record("read_policy", self._policy)

    def inspect_csv(self) -> dict:
        """Inspect column names and up to three sample records as data."""
        try:
            rows = list(csv.reader(io.StringIO(self._data.decode("utf-8-sig")), strict=True))
        except (UnicodeError, csv.Error) as error:
            raise ValueError("invalid CSV") from error
        self._headers = rows[0] if rows else []
        return self._record("inspect_csv", {"headers": self._headers, "sample": rows[1:4],
                                             "records": max(0, len(rows) - 1)})

    def propose_mapping(self, mapping: dict[str, str]) -> dict:
        """Select only documented source aliases for each canonical field.

        Args:
            mapping: Canonical field names mapped to source header names.
        """
        self._result = None
        self._mapping = None
        if not self._read or self._headers is None:
            raise ValueError("read policy and inspect CSV first")
        if set(mapping) != set(FIELDS) or any(
            value not in self._policy["columns"][field] or value not in self._headers
            for field, value in mapping.items()
        ):
            raise ValueError("mapping is not authorized by the supplier policy")
        self._mapping = dict(mapping)
        return self._record("propose_mapping", {"mapping": mapping})

    def validate_import(self) -> dict:
        """Validate every row, retaining all unknown or conflicting data for review."""
        if not self._read or self._headers is None:
            raise ValueError("read policy and inspect CSV first")
        result = validate(self._data, self._policy)
        if not result["review"] and self._mapping != result["mapping"]:
            raise ValueError("propose the unambiguous documented mapping first")
        self._result = result
        return self._record("validate_import", {"accepted": len(result["accepted"]),
            "review": len(result["review"]), "issues": result["review"][:10],
            "mapping": result["mapping"]})

    def export_result(self) -> dict:
        """Publish only the previously validated job to its bound output directory."""
        if self._result is None:
            raise ValueError("successful validation required before export")
        self.directory = export(self._data, self._policy, self._output)
        return self._record("export_result", {"directory": str(self.directory),
            "accepted": len(self._result["accepted"]), "review": len(self._result["review"])})
