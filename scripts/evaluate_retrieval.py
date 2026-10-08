"""Run the 30-question retrieval and not-found evaluation on three public repos."""

import asyncio
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.services.service_manager import get_service_manager_sync

EVAL_PATH = ROOT / "tests" / "eval_questions.json"


def main() -> int:
    logging.disable(logging.CRITICAL)
    evaluation = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    hits = 0
    false_not_found = 0
    total = 0

    with TestClient(app) as client:
        manager = get_service_manager_sync()
        for repo_name, repo_data in evaluation["repos"].items():
            ingest = client.post("/api/ingest", json={"repository_url": repo_data["source"]})
            if ingest.status_code != 200:
                print(f"{repo_name}: ingest failed ({ingest.status_code})")
                return 1
            repo_id = ingest.json()["repo_id"]
            print(
                f"{repo_name}: ingested {ingest.json()['file_count']} files, "
                f"{ingest.json()['chunks_indexed']} chunks"
            )

            for item in repo_data["questions"]:
                results = asyncio.run(
                    manager.query_processing_service.retrieve_relevant_chunks(
                        item["question"], top_k=5, repo_id=repo_id
                    )
                )
                expected_file = item["expected_file"]
                hit = expected_file in [result.chunk.file_path for result in results]
                response = asyncio.run(
                    manager.query_processing_service.process_query(
                        item["question"], repo_id=repo_id
                    )
                )
                not_found = response.answer.startswith("Not found in repo")
                hits += int(hit)
                false_not_found += int(not_found)
                total += 1
                status = "HIT" if hit else "MISS"
                guard_status = "FALSE_NOT_FOUND" if not_found else "ANSWERED"
                print(f"{status} {guard_status} {repo_name}: {expected_file} <- {item['question']}")

    print(f"HIT_RATE_AT_5={hits}/{total} ({hits / total:.0%})")
    print(f"FALSE_NOT_FOUND_RATE={false_not_found}/{total} ({false_not_found / total:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
