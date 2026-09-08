# Import Review

Supplier CSV import validation with an audit trail. A Strands adapter exposes five job-bound tools. A live model integration run has not yet been verified.

Python 3.11+; no dependencies for the core.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
python3 import_review.py examples/supplier.csv examples/policy.json outputs
```

Each content-addressed job contains `accepted.csv`, `review.json`, and `manifest.json`. Original inputs remain unchanged. Ambiguous rows go to review; malformed files fail before publishing artifacts. Repeat runs verify existing output bytes and refuse altered results. Record numbers count CSV records including the header, rather than physical lines when quoted cells span multiple lines.

Policies explicitly define aliases, trimming, SKU case and decimal separator. Unknown columns are reviewed, not discarded. Identical duplicate records are retained; conflicting values for a SKU put every conflicting record into review. Inventory values are snapshots, not additive transactions.

The example uses synthetic inventory only. Output CSV is intended for programmatic import; text is preserved and is not escaped for spreadsheet formula evaluation.

With AWS credentials configured for an eligible Bedrock model, run:

```sh
.venv/bin/python agent_runner.py examples/supplier.csv examples/policy.json outputs --model MODEL_ID
```

The adapter requires successful tool validation before export, limits the job to eight model calls, and saves actual SDK messages in `agent-trace.json`. Model inference can incur provider costs; the local core command makes no model calls. Never put credentials in this repository.

Remaining: watched inbox, real model integration test, demonstration video and contest submission. No prize or payment has been earned by this project.
