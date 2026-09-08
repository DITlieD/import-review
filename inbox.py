"""Process atomically delivered CSV files with persistent job tracking."""
import argparse
import fcntl
import json
from pathlib import Path
import tempfile
import time
from import_review import digest, policy_bytes


def save_state(path, state):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
        json.dump(state, file, indent=2)
        temp = Path(file.name)
    temp.replace(path)


def scan_once(incoming, policy_file, output, state_file, process, retry_failed=False):
    """Process new content once. Producers must rename completed files to .csv."""
    incoming, policy_file, output, state_file = map(Path, (incoming, policy_file, output, state_file))
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        policy_data = policy_bytes(json.loads(policy_file.read_text()))
        events = []
        for source in sorted(incoming.glob("*.csv")):
            if source.is_symlink() or not source.is_file():
                continue
            data = source.read_bytes()
            job = digest(data + b"\0" + policy_data)
            previous = state.get(job)
            if previous and not (retry_failed and previous["status"] in ("failed", "running")):
                continue
            entry = {"source": source.name, "status": "running", "job": job}
            state[job] = entry
            save_state(state_file, state)
            try:
                # The model sees frozen copies, even if a producer replaces its files.
                with tempfile.TemporaryDirectory(dir=state_file.parent) as directory:
                    snapshot = Path(directory)
                    frozen_csv = snapshot / "input.csv"
                    frozen_policy = snapshot / "policy.json"
                    frozen_csv.write_bytes(data)
                    frozen_policy.write_bytes(policy_data)
                    destination = Path(process(frozen_csv, frozen_policy, output))
                    if not (destination / "manifest.json").is_file():
                        raise ValueError("processor did not produce a manifest")
                    manifest = json.loads((destination / "manifest.json").read_text())
                    if (manifest.get("input_sha256") != digest(data)
                            or manifest.get("policy_sha256") != digest(policy_data)
                            or set(manifest.get("artifacts", {})) != {"accepted.csv", "review.json"}):
                        raise ValueError("manifest does not match this job")
                    for name, expected in manifest["artifacts"].items():
                        if digest((destination / name).read_bytes()) != expected:
                            raise ValueError("output artifact integrity mismatch")
                    entry.update(status="complete", directory=str(destination))
            except Exception as error:
                entry.update(status="failed", error=f"{type(error).__name__}: {error}")
            save_state(state_file, state)
            events.append(dict(entry))
        return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inbox", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--region", default="ap-southeast-2")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    from strands.models import BedrockModel
    from agent_runner import run_job
    model = BedrockModel(model_id=args.model, region_name=args.region, max_tokens=1500, temperature=0)
    retry = args.retry_failed
    while True:
        events = scan_once(args.inbox, args.policy, args.output, args.state,
                           lambda source, policy, output: run_job(source, policy, output, model), retry)
        for event in events:
            print(json.dumps(event), flush=True)
        retry = False
        if not args.watch:
            break
        time.sleep(5)


if __name__ == "__main__":
    main()
