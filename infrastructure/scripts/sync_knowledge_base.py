from __future__ import annotations

import argparse
import os

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-base-id", default=os.environ.get("LINKOPS_KNOWLEDGE_BASE_ID"))
    parser.add_argument(
        "--data-source-id",
        default=os.environ.get("LINKOPS_KNOWLEDGE_DATA_SOURCE_ID"),
    )
    args = parser.parse_args()
    if not args.knowledge_base_id or not args.data_source_id:
        raise SystemExit("Provide --knowledge-base-id and --data-source-id.")
    response = boto3.client("bedrock-agent").start_ingestion_job(
        knowledgeBaseId=args.knowledge_base_id,
        dataSourceId=args.data_source_id,
    )
    print(response["ingestionJob"]["ingestionJobId"])


if __name__ == "__main__":
    main()
