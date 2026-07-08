"""Questionnaire structure schema + skip-logic evaluator (pure, deterministic).

The survey ``structure`` is a JSON document::

    {
      "sections": [
        {"id": "s1", "title": "...", "questions": [
          {"id": "q1", "type": "single", "text": "...", "required": true,
           "options": ["A", "B"]},
          {"id": "q2", "type": "scale", "text": "...", "scale": {"min": 1, "max": 5}}
        ]}
      ],
      "logic": [
        {"if": {"qid": "q1", "op": "eq", "value": "A"},
         "then": {"action": "skip_to", "target": "q5"}},
        {"if": {"qid": "q2", "op": "lt", "value": 2},
         "then": {"action": "screen_out"}}
      ]
    }

Skip logic is **forward-only**: a ``skip_to`` target must appear after its trigger question in
document order (enforced at ``validate_structure`` time), so traversal always terminates.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Sentinels returned by traversal in place of a question id.
SCREENED_OUT = "__screened_out__"
END = "__end__"

QUESTION_TYPES = frozenset({"single", "multi", "scale", "open_text", "number"})
LOGIC_OPS = frozenset({"eq", "ne", "gt", "lt", "in"})
LOGIC_ACTIONS = frozenset({"skip_to", "screen_out"})


# ----------------------------- structure access -----------------------------

def iter_questions(structure: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all questions across sections, preserving document order."""
    questions: list[dict[str, Any]] = []
    for section in structure.get("sections", []) or []:
        for question in section.get("questions", []) or []:
            questions.append(question)
    return questions


def ordered_qids(structure: dict[str, Any]) -> list[str]:
    return [str(q.get("id")) for q in iter_questions(structure)]


def question_by_id(structure: dict[str, Any], qid: str) -> dict[str, Any] | None:
    for question in iter_questions(structure):
        if str(question.get("id")) == qid:
            return question
    return None


# ----------------------------- validation -----------------------------

def validate_structure(structure: dict[str, Any]) -> list[str]:
    """Return a list of human-readable errors; empty list means the structure is valid."""
    errors: list[str] = []
    if not isinstance(structure, dict):
        return ["structure must be an object"]

    questions = iter_questions(structure)
    if not questions:
        errors.append("structure has no questions")

    qids = [str(q.get("id", "")) for q in questions]
    seen: set[str] = set()
    for qid in qids:
        if not qid:
            errors.append("every question needs a non-empty id")
        elif qid in seen:
            errors.append(f"duplicate question id: {qid}")
        seen.add(qid)

    position = {qid: i for i, qid in enumerate(qids)}

    for question in questions:
        qid = str(question.get("id", ""))
        qtype = question.get("type")
        if qtype not in QUESTION_TYPES:
            errors.append(f"question {qid}: unknown type {qtype!r}")
        if qtype in ("single", "multi"):
            options = question.get("options")
            if not isinstance(options, list) or not options:
                errors.append(f"question {qid}: {qtype} needs a non-empty options list")
        if qtype == "scale":
            scale = question.get("scale") or {}
            lo, hi = scale.get("min"), scale.get("max")
            if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)) or lo >= hi:
                errors.append(f"question {qid}: scale needs numeric min < max")

    for i, rule in enumerate(structure.get("logic", []) or []):
        cond = rule.get("if") or {}
        then = rule.get("then") or {}
        cond_qid = str(cond.get("qid", ""))
        if cond_qid not in position:
            errors.append(f"logic[{i}]: if.qid {cond_qid!r} is not a question")
        if cond.get("op") not in LOGIC_OPS:
            errors.append(f"logic[{i}]: unknown op {cond.get('op')!r}")
        action = then.get("action")
        if action not in LOGIC_ACTIONS:
            errors.append(f"logic[{i}]: unknown action {action!r}")
        if action == "skip_to":
            target = str(then.get("target", ""))
            if target not in position:
                errors.append(f"logic[{i}]: skip_to target {target!r} is not a question")
            elif cond_qid in position and position[target] <= position[cond_qid]:
                errors.append(
                    f"logic[{i}]: skip_to target {target!r} must come after {cond_qid!r}"
                    " (forward-only)"
                )
    return errors


# ----------------------------- answer validation -----------------------------

def validate_answer(question: dict[str, Any], value: Any) -> str | None:
    """Validate a single answer's type/domain (presence/required is the caller's concern)."""
    qtype = question.get("type")
    qid = question.get("id")
    if qtype == "single":
        if value not in (question.get("options") or []):
            return f"{qid}: {value!r} is not an allowed option"
    elif qtype == "multi":
        if not isinstance(value, list):
            return f"{qid}: expected a list of options"
        options = question.get("options") or []
        for item in value:
            if item not in options:
                return f"{qid}: {item!r} is not an allowed option"
    elif qtype == "scale":
        scale = question.get("scale") or {}
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"{qid}: expected a number"
        if not (scale.get("min", float("-inf")) <= value <= scale.get("max", float("inf"))):
            return f"{qid}: {value} is outside the scale range"
    elif qtype == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"{qid}: expected a number"
    elif qtype == "open_text":
        if not isinstance(value, str):
            return f"{qid}: expected text"
    return None


# ----------------------------- traversal -----------------------------

def _condition_met(op: str, answer: Any, target_value: Any) -> bool:
    try:
        if op == "eq":
            return answer == target_value
        if op == "ne":
            return answer != target_value
        if op == "gt":
            return answer is not None and answer > target_value
        if op == "lt":
            return answer is not None and answer < target_value
        if op == "in":
            if isinstance(answer, list):
                return target_value in answer
            return answer in (target_value or [])
    except TypeError:
        # incomparable types (e.g. gt on a string) -> condition simply does not fire
        return False
    return False


def _action_after(structure: dict[str, Any], answers: dict[str, Any], qid: str):
    """First matching logic action triggered by the answer to ``qid``, or ``None``."""
    for rule in structure.get("logic", []) or []:
        cond = rule.get("if") or {}
        if str(cond.get("qid", "")) != qid:
            continue
        if _condition_met(cond.get("op", ""), answers.get(qid), cond.get("value")):
            then = rule.get("then") or {}
            return then.get("action"), then.get("target")
    return None


def next_question_id(
    structure: dict[str, Any], answers: dict[str, Any], current_qid: str | None
) -> str:
    """Given the answers so far, return the next question id, ``SCREENED_OUT``, or ``END``.

    ``current_qid=None`` returns the first question (or ``END`` for an empty survey).
    """
    order = ordered_qids(structure)
    if not order:
        return END
    if current_qid is None:
        return order[0]
    if current_qid not in order:
        log.warning("next_question_id: unknown current_qid %r", current_qid)
        return END

    action = _action_after(structure, answers, current_qid)
    if action is not None:
        kind, target = action
        if kind == "screen_out":
            return SCREENED_OUT
        if kind == "skip_to" and target in order:
            return str(target)

    idx = order.index(current_qid)
    return order[idx + 1] if idx + 1 < len(order) else END


def visible_path(structure: dict[str, Any], answers: dict[str, Any]) -> list[str]:
    """The ordered question ids a respondent with these answers actually sees.

    Stops at ``END`` normally; returns the path collected so far if answers screen the
    respondent out (the caller inspects whether the terminal step was a screen-out separately
    via :func:`is_screened_out`).
    """
    path: list[str] = []
    current = next_question_id(structure, answers, None)
    guard = 0
    limit = len(ordered_qids(structure)) + 1
    while current not in (END, SCREENED_OUT) and guard < limit:
        path.append(current)
        current = next_question_id(structure, answers, current)
        guard += 1
    return path


def is_screened_out(structure: dict[str, Any], answers: dict[str, Any]) -> bool:
    """True if traversing with these answers hits a screen-out action."""
    current = next_question_id(structure, answers, None)
    guard = 0
    limit = len(ordered_qids(structure)) + 1
    while current not in (END, SCREENED_OUT) and guard < limit:
        current = next_question_id(structure, answers, current)
        guard += 1
    return current == SCREENED_OUT


def missing_required(structure: dict[str, Any], answers: dict[str, Any]) -> list[str]:
    """Required questions on the respondent's visible path that lack a (non-empty) answer."""
    missing: list[str] = []
    for qid in visible_path(structure, answers):
        question = question_by_id(structure, qid)
        if not question or not question.get("required"):
            continue
        value = answers.get(qid)
        if value is None or value == "" or value == []:
            missing.append(qid)
    return missing


__all__ = [
    "SCREENED_OUT",
    "END",
    "QUESTION_TYPES",
    "LOGIC_OPS",
    "LOGIC_ACTIONS",
    "iter_questions",
    "ordered_qids",
    "question_by_id",
    "validate_structure",
    "validate_answer",
    "next_question_id",
    "visible_path",
    "is_screened_out",
    "missing_required",
]
