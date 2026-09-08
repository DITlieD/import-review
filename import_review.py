"""Deterministic supplier import validation and auditable export."""
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile

FIELDS = ("sku", "quantity", "unit_price")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def policy_bytes(policy):
    if not isinstance(policy, dict) or set(policy) != {
        "version", "columns", "trim", "sku_case", "decimal_separator"
    }:
        raise ValueError("policy fields must match the documented schema")
    if type(policy["version"]) is not int or policy["version"] < 1:
        raise ValueError("positive integer policy version required")
    if type(policy["trim"]) is not bool or policy["sku_case"] not in ("upper", "lower", "preserve"):
        raise ValueError("invalid normalization policy")
    if policy["decimal_separator"] not in (".", ","):
        raise ValueError("invalid decimal separator")
    columns = policy["columns"]
    if not isinstance(columns, dict) or set(columns) != set(FIELDS):
        raise ValueError("all canonical columns required")
    aliases = []
    for names in columns.values():
        if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n for n in names):
            raise ValueError("nonempty string alias lists required")
        aliases.extend(names)
    if len(aliases) != len(set(aliases)):
        raise ValueError("aliases must be unique across the policy")
    return json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()


def validate(data, policy):
    """Return row decisions. Malformed CSV/policy raises before any export."""
    encoded_policy = policy_bytes(policy)
    try:
        rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as error:
        raise ValueError("invalid UTF-8 CSV") from error
    if not rows or not rows[0] or len(set(rows[0])) != len(rows[0]):
        raise ValueError("nonempty unique headers required")
    headers, records = rows[0], rows[1:]
    if any(len(row) != len(headers) for row in records):
        raise ValueError("record width differs from header width")
    mapping, header_errors = {}, []
    allowed = {alias for names in policy["columns"].values() for alias in names}
    if set(headers) - allowed:
        header_errors.append("unknown headers")
    for field in FIELDS:
        matches = [h for h in headers if h in policy["columns"][field]]
        if len(matches) != 1:
            header_errors.append(f"missing or ambiguous header: {field}")
        else:
            mapping[field] = headers.index(matches[0])
    decisions, transformations = [], []
    for number, raw in enumerate(records, 2):
        reasons, values = list(header_errors), {}
        if not header_errors:
            for field, index in mapping.items():
                value = raw[index]
                normalized = value.strip() if policy["trim"] else value
                if field == "sku" and policy["sku_case"] != "preserve":
                    normalized = getattr(normalized, policy["sku_case"])()
                if field == "unit_price" and policy["decimal_separator"] == ",":
                    # A dot is not a documented decimal separator under this policy.
                    if "." in normalized:
                        reasons.append("unexpected decimal separator")
                    normalized = normalized.replace(",", ".")
                if normalized != value:
                    transformations.append({"row": number, "field": field, "from": value, "to": normalized})
                values[field] = normalized
                if not normalized:
                    reasons.append(f"missing {field}")
            if not re.fullmatch(r"[0-9]+", values["quantity"]):
                reasons.append("quantity must be a nonnegative integer")
            if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", values["unit_price"]):
                reasons.append("price must be a finite nonnegative decimal")
            else:
                values["unit_price"] = str(Decimal(values["unit_price"]))
        decisions.append({"row": number, "raw": dict(zip(headers, raw)), "values": values, "reasons": reasons})
    groups = {}
    for row in decisions:
        sku = row["values"].get("sku")
        if sku:
            groups.setdefault(sku, []).append(row)
    for group in groups.values():
        signatures = {(r["values"].get("quantity"), r["values"].get("unit_price")) for r in group}
        if len(signatures) > 1:
            for row in group:
                row["reasons"].append("conflicting duplicate SKU")
    return {
        "accepted": [r["values"] for r in decisions if not r["reasons"]],
        "review": [r for r in decisions if r["reasons"]],
        "input_rows": len(records), "transformations": transformations,
        "mapping": {field: headers[index] for field, index in mapping.items()},
        "input_sha256": digest(data), "policy_sha256": digest(encoded_policy),
    }


def export(data, policy, output_root):
    """Publish complete artifacts atomically; refuse altered cached results."""
    result = validate(data, policy)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    job = digest((result["input_sha256"] + result["policy_sha256"]).encode())
    destination = root / job
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(result["accepted"])
    artifacts = {"accepted.csv": stream.getvalue().encode(),
                 "review.json": (json.dumps(result["review"], indent=2) + "\n").encode()}
    manifest = {**result, "accepted": len(result["accepted"]), "review": len(result["review"]),
                "artifacts": {name: digest(body) for name, body in artifacts.items()}}
    artifacts["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    if destination.exists():
        if destination.is_symlink() or any(
            (destination / name).is_symlink() or not (destination / name).is_file()
            or (destination / name).read_bytes() != body for name, body in artifacts.items()
        ):
            raise ValueError("existing output failed integrity verification")
        return destination
    with tempfile.TemporaryDirectory(prefix=".import-", dir=root) as temp:
        staging = Path(temp) / "result"
        staging.mkdir()
        for name, body in artifacts.items():
            (staging / name).write_bytes(body)
        staging.rename(destination)
    return destination


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(export(args.csv.read_bytes(), json.loads(args.policy.read_text()), args.output))
    except (OSError, ValueError) as error:
        parser.exit(2, f"Import failed: {error}\n")
