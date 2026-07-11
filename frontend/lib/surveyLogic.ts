// Client-side mirror of the backend skip-logic evaluator (labs/fieldwork/runtime).
// Forward-only skips; the server re-validates on complete, so this is UX only.

import type { LogicRule, SurveyStructure } from "@/lib/api";

export const SCREENED_OUT = "__screened_out__";
export const END = "__end__";

export function orderedQids(structure: SurveyStructure): string[] {
  return structure.sections.flatMap((s) => s.questions.map((q) => q.id));
}

function conditionMet(op: string, answer: unknown, target: unknown): boolean {
  switch (op) {
    case "eq":
      return answer === target;
    case "ne":
      return answer !== target;
    case "gt":
      return typeof answer === "number" && typeof target === "number" && answer > target;
    case "lt":
      return typeof answer === "number" && typeof target === "number" && answer < target;
    case "in":
      return Array.isArray(answer) ? answer.includes(target) : answer === target;
    default:
      return false;
  }
}

function actionAfter(
  structure: SurveyStructure,
  answers: Record<string, unknown>,
  qid: string,
): LogicRule["then"] | null {
  for (const rule of structure.logic ?? []) {
    if (rule.if.qid !== qid) continue;
    if (conditionMet(rule.if.op, answers[qid], rule.if.value)) return rule.then;
  }
  return null;
}

export function nextQuestionId(
  structure: SurveyStructure,
  answers: Record<string, unknown>,
  currentQid: string | null,
): string {
  const order = orderedQids(structure);
  if (order.length === 0) return END;
  if (currentQid === null) return order[0];
  if (!order.includes(currentQid)) return END;

  const action = actionAfter(structure, answers, currentQid);
  if (action) {
    if (action.action === "screen_out") return SCREENED_OUT;
    if (action.action === "skip_to" && action.target && order.includes(action.target))
      return action.target;
  }
  const idx = order.indexOf(currentQid);
  return idx + 1 < order.length ? order[idx + 1] : END;
}

export function firstUnanswered(
  structure: SurveyStructure,
  answers: Record<string, unknown>,
): string {
  let current = nextQuestionId(structure, answers, null);
  while (current !== END && current !== SCREENED_OUT) {
    const v = answers[current];
    if (v === undefined || v === "" || (Array.isArray(v) && v.length === 0)) return current;
    current = nextQuestionId(structure, answers, current);
  }
  return current;
}
