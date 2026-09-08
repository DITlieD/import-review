# Import Review

Supplier CSV import validation with an audit trail. A Strands adapter exposes five job-bound tools. A real model run through an OpenAI-compatible gateway has been verified; Bedrock access in the development account remains unavailable.

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

For a tool-capable OpenAI-compatible provider, set `OPENAI_API_KEY` in your environment and add `--base-url`:

```sh
.venv/bin/python agent_runner.py examples/supplier.csv examples/policy.json outputs --model MODEL_ID --base-url http://127.0.0.1:9020/v1
```

The gateway is configured by the operator and is not bundled. Both commands support the same provider options. Gateway calls use a 90-second request timeout, no transport retries, and provider-default temperature. The verified development run used ZenoV with `devin-free/glm-5-2`; availability and pricing depend on your own provider account. See [architecture and verification](ARCHITECTURE.md).

For a Linux inbox using a single supplier policy:

```sh
.venv/bin/python inbox.py incoming examples/policy.json outputs --state outputs/inbox-state.json --model MODEL_ID --watch
```

Deliver files by writing a temporary filename then atomically renaming to `.csv` in the inbox. The runner freezes input and policy, records progress before invoking the model, verifies returned artifact hashes, and skips previously seen content across restarts. Failed or interrupted jobs require `--retry-failed` (applied once, not on every watch cycle). A process lock prevents two runners sharing a state file. Keep state and outputs together. Core validation works without Strands; the inbox and agent entry points require the installed SDK and configured model credentials.

## Demonstration

[Watch the captioned demo](demo/import-review-demo.mp4) (2 minutes 53 seconds). It presents a fresh successful inbox invocation and its outputs; model waiting time is omitted. The captured command, result, duplicate check, input and actual tool transcript are in `examples/demo-run/`. These are recorded evidence, not fixtures used by the agent at runtime.

To render the video again from that recorded evidence, install Pillow in a separate environment and make FFmpeg and the DejaVu fonts available, then run `python3 tools/render_demo.py`. The renderer writes to `outputs/demo-video/` and makes no model calls.

Remaining: public YouTube/Vimeo upload and contest submission. No prize or payment has been earned by this project.
