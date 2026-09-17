"""Deterministic scoring (single source of truth, no LLM formula)."""

from app.ai.schemas import EvaluationOutput


def round_half_up(value: float) -> int:
    import math

    return int(math.floor(value + 0.5))


def technical_overall_0_10(result: EvaluationOutput) -> int:
    t = result.technical
    return round_half_up((t.correctness + t.relevance + t.completeness + t.technical_depth) / 4.0)


def communication_overall_0_10(result: EvaluationOutput) -> int:
    c = result.communication
    return round_half_up((c.clarity + c.structure + c.conciseness) / 3.0)


def to_0_100(score_0_10: int) -> int:
    return max(0, min(100, int(score_0_10) * 10))


def overall_0_100(technical_100: int, communication_100: int) -> int:
    return round_half_up((technical_100 + communication_100) / 2.0)


def report_scores(results: list[EvaluationOutput]) -> tuple[int, int, int]:
    if not results:
        raise ValueError("No evaluations to aggregate")
    tech = round_half_up(sum(to_0_100(technical_overall_0_10(r)) for r in results) / len(results))
    comm = round_half_up(sum(to_0_100(communication_overall_0_10(r)) for r in results) / len(results))
    return tech, comm, overall_0_100(tech, comm)
