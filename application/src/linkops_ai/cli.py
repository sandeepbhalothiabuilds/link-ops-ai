from __future__ import annotations

import argparse
import json
from pathlib import Path

from .orchestration.runner import WorkflowRunner

SCENARIOS = {
    "greenfield": "Build the initial URL shortening API with analytics and reliability controls.",
    "brownfield": "Add link expiration to the existing service without breaking current clients.",
    "ambiguous": "Make the analytics privacy-friendly and near real time.",
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="linkops")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scenario = subparsers.add_parser("scenario")
    scenario.add_argument("name", choices=sorted(SCENARIOS))
    scenario.add_argument("--auto-approve", action="store_true")
    scenario.add_argument("--approve-clarification", action="store_true")
    scenario.add_argument("--inject-failure", action="store_true")
    args = parser.parse_args()
    if args.command == "scenario":
        workspace = Path.cwd()
        runner = WorkflowRunner(workspace)
        result = runner.run(
            SCENARIOS[args.name],
            args.name,
            auto_approve=args.auto_approve or args.approve_clarification,
            inject_failure=args.inject_failure,
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
