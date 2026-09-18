from __future__ import annotations

import argparse
import json

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument(
        "--requirement",
        default="Build the initial URL shortening API with analytics.",
    )
    parser.add_argument("--scenario", default="greenfield")
    args = parser.parse_args()
    response = boto3.client("bedrock-agentcore").invoke_agent_runtime(
        agentRuntimeArn=args.runtime_arn,
        runtimeSessionId="linkops-cli-demo-session-001",
        payload=json.dumps({"requirement": args.requirement, "scenario": args.scenario}).encode(),
        qualifier="DEFAULT",
    )
    print(response["response"].read().decode())


if __name__ == "__main__":
    main()
