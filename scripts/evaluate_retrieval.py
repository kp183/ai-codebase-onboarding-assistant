"""Run the offline fixture and live public-repository retrieval evaluation."""

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.services.service_manager import get_service_manager_sync


EVAL_PATH = ROOT / "tests" / "fixtures" / "retrieval_eval.json"


def main() -> int:
    evaluation = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    hits = 0
    total = 0

    with TestClient(app) as client:
        manager = get_service_manager_sync()
        for repo_name, repo_data in evaluation["repos"].items():
            source = repo_data["source"]
            if repo_name == "fixture":
                source = str((ROOT / source).resolve())
            ingest = client.post("/api/ingest", json={"repository_url": source})
            if ingest.status_code != 200:
                print(f"{repo_name}: ingest failed ({ingest.status_code}) {ingest.text}")
                return 1
            repo_id = ingest.json()["repo_id"]

            for item in repo_data["questions"]:
                results = asyncio.run(
                    manager.query_processing_service.retrieve_relevant_chunks(
                        item["question"], top_k=5, repo_id=repo_id
                    )
                )
                paths = [result.chunk.file_path for result in results]
                hit = item["expected_file"] in paths
                hits += int(hit)
                total += 1
                print(
                    f"{'HIT ' if hit else 'MISS'} {repo_name}: "
                    f"{item['expected_file']} <- {item['question']}"
                )

    print(f"HIT_RATE_AT_5={hits}/{total} ({hits / total:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
