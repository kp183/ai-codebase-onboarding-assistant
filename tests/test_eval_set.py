import json
from pathlib import Path


def test_eval_set_has_twenty_questions_and_five_paraphrases_per_repo():
    eval_path = Path(__file__).parent / "fixtures" / "retrieval_eval.json"
    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))

    assert set(evaluation["repos"]) == {"fixture", "public"}
    assert sum(len(repo["questions"]) for repo in evaluation["repos"].values()) == 20
    for repo in evaluation["repos"].values():
        paraphrase_groups = {
            question["paraphrase_set"]
            for question in repo["questions"]
            if "paraphrase_set" in question
        }
        assert len(paraphrase_groups) == 1
        group = next(iter(paraphrase_groups))
        assert sum(
            question.get("paraphrase_set") == group for question in repo["questions"]
        ) == 5
