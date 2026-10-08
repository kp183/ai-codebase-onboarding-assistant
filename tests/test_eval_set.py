import json
from pathlib import Path


def test_eval_set_has_answerable_and_unanswerable_questions():
    eval_path = Path(__file__).parent / "eval_questions.json"
    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))

    assert set(evaluation["repos"]) == {"flask", "click", "requests", "werkzeug"}
    assert sum(len(repo["questions"]) for repo in evaluation["repos"].values()) == 40
    for repo in evaluation["repos"].values():
        assert repo["source"].startswith("https://github.com/")
        assert len(repo["questions"]) == 10
        for question in repo["questions"]:
            assert {"question", "expected_file"} <= set(question)
            assert question["question"].strip()
            assert question.get("answerable", question["expected_file"] is not None) == (
                question["expected_file"] is not None
            )
    werkzeug = evaluation["repos"]["werkzeug"]["questions"]
    assert sum(question["answerable"] for question in werkzeug) == 5
