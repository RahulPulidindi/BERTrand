"""Check that every Inspect log in a directory finished. Exit 1, with resume commands, if not.

Usage: python -m analysis.check_logs logs/run1/main
"""

from __future__ import annotations

import sys

from inspect_ai.log import list_eval_logs, read_eval_log


def main() -> None:
    log_dir = sys.argv[1]
    infos = list_eval_logs(log_dir)
    if not infos:
        print(f"no logs in {log_dir}")
        sys.exit(1)
    failed = []
    for info in infos:
        log = read_eval_log(info.name, header_only=True)
        done = log.results.completed_samples if log.results else 0
        total = log.results.total_samples if log.results else "?"
        model = (log.eval.task_args or {}).get("seller_models") and "mixed" or log.eval.model
        print(f"  {log.status:8s} {done}/{total} episodes  {model}  {info.name.split('/')[-1]}")
        if log.status != "success":
            failed.append(info.name)
    if failed:
        print("Some runs did not finish. Resume each with:")
        for name in failed:
            print(f"  .venv/bin/inspect eval-retry {name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
