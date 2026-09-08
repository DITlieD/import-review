# Import Review

Supplier CSV import validation with an audit trail. This is the deterministic core of a planned Strands agent; live agent integration is not implemented yet.

Python 3.11+; no dependencies for the core.

```sh
python3 -m unittest discover -s tests -v
python3 import_review.py examples/supplier.csv examples/policy.json outputs
```

Each content-addressed job contains `accepted.csv`, `review.json`, and `manifest.json`. Original inputs remain unchanged. Ambiguous rows go to review; malformed files fail before publishing artifacts. Repeat runs verify existing output bytes and refuse altered results. Record numbers count CSV records including the header, rather than physical lines when quoted cells span multiple lines.

Policies explicitly define aliases, trimming, SKU case and decimal separator. Unknown columns are reviewed, not discarded. Identical duplicate records are retained; conflicting values for a SKU put every conflicting record into review. Inventory values are snapshots, not additive transactions.

The example uses synthetic inventory only. Output CSV is intended for programmatic import; text is preserved and is not escaped for spreadsheet formula evaluation.

Remaining: Strands tools and agent, watched inbox, real model integration test, demonstration video and contest submission. No prize or payment has been earned by this project.
