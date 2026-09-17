"""Curated question bank: deterministic fallback only (no random filler)."""

from app.ai.schemas import QuestionOutput

BANK: list[QuestionOutput] = [
    QuestionOutput(question_text="Explain how a Python dictionary works internally and when you would prefer it over a list for lookups, including time-complexity trade-offs.", question_type="TECHNICAL", category="data-structures", skill="Python", difficulty="MEDIUM", expected_concepts=["hash-table", "average-O(1)-lookup", "key-hashability"], evaluation_rubric="Credit hashing, average O(1), hashable keys, list-vs-dict trade-off.", follow_up_allowed=True, max_follow_ups=1),
    QuestionOutput(question_text="Describe a time you resolved a disagreement with a teammate about a technical approach. What did you do and what was the outcome?", question_type="BEHAVIORAL", category="teamwork", skill="communication", difficulty="MEDIUM", expected_concepts=["conflict-resolution", "listening", "ownership"], evaluation_rubric="Credit STAR structure, specific actions, measurable outcome.", follow_up_allowed=True, max_follow_ups=1),
    QuestionOutput(question_text="Explain Python list vs tuple differences and when you would choose a tuple in a backend service.", question_type="TECHNICAL", category="data-structures", skill="Python", difficulty="EASY", expected_concepts=["mutability", "hashability", "use-cases"], evaluation_rubric="Credit mutability, hashability, and practical guidance.", follow_up_allowed=True, max_follow_ups=1),
    QuestionOutput(question_text="Design a rate limiter for a backend API serving a Backend Developer workload. Discuss algorithm choice, edge cases, and scaling.", question_type="TECHNICAL", category="system-design", skill="backend", difficulty="HARD", expected_concepts=["token-bucket", "edge-cases", "distributed-state"], evaluation_rubric="Credit algorithm, correctness under concurrency, scaling trade-offs.", follow_up_allowed=True, max_follow_ups=2),
    QuestionOutput(question_text="Walk through how you would design a REST API endpoint for user authentication, covering input validation, error responses, and rate-limiting considerations.", question_type="TECHNICAL", category="backend", skill="Python", difficulty="MEDIUM", expected_concepts=["input-validation", "http-status-codes", "rate-limiting"], evaluation_rubric="Credit validation strategy, correct status codes, abuse prevention, and secure token handling.", follow_up_allowed=True, max_follow_ups=1),
    QuestionOutput(question_text="Tell me about a time you had to learn a new technology quickly for a project. How did you approach it and what was the result?", question_type="BEHAVIORAL", category="adaptability", skill="communication", difficulty="MEDIUM", expected_concepts=["learning-strategy", "time-management", "outcome-reflection"], evaluation_rubric="Credit a concrete situation, a deliberate learning approach, and a reflective outcome.", follow_up_allowed=True, max_follow_ups=1),
]


def _norm(text: str) -> str:
    import re

    return re.sub(r"\s+", " ", text.strip().lower())


class QuestionBank:
    def __init__(self, entries: list[QuestionOutput] | None = None) -> None:
        self.entries = list(entries) if entries is not None else list(BANK)

    def find_one(self, *, role: str, language: str | None, interview_type: str, difficulty: str, exclude: list[str]) -> QuestionOutput | None:
        excluded = {_norm(q) for q in exclude}
        role_key = role.strip().lower()
        for entry in self.entries:
            if interview_type != "MIXED" and entry.question_type != interview_type:
                continue
            if entry.difficulty != difficulty:
                continue
            if language and entry.question_type == "TECHNICAL" and language.lower() not in (entry.skill + " " + entry.category + " " + entry.question_text).lower():
                continue
            if "backend" in role_key and entry.question_type == "TECHNICAL" and "backend" not in (entry.skill + " " + entry.category + " " + entry.question_text).lower() and "python" not in (entry.skill + " " + entry.category).lower():
                if entry.difficulty == "HARD":
                    pass
                else:
                    continue
            if _norm(entry.question_text) in excluded:
                continue
            return entry
        return None


def get_default_bank() -> QuestionBank:
    return QuestionBank()
