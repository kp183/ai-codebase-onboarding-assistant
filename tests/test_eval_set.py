import json
from pathlib import Path


def test_eval_set_has_thirty_questions_for_three_public_repositories():
    eval_path = Path(__file__).parent / "eval_questions.json"
    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))

    assert set(evaluation["repos"]) == {"flask", "click", "requests"}
    assert sum(len(repo["questions"]) for repo in evaluation["repos"].values()) == 30
    for repo in evaluation["repos"].values():
        assert repo["source"].startswith("https://github.com/")
        assert len(repo["questions"]) == 10
        for question in repo["questions"]:
            assert set(question) == {"question", "expected_file"}
            assert question["question"].strip()
            assert question["expected_file"].strip()
