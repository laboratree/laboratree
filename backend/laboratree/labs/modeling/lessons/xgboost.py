"""The XGBoost deep lesson — the gold-standard "live show".

Eighteen chapters from zero to verdict: the ensemble idea, what a tree/stump is, the live
data, gradients & hessians (broken all the way down), the similarity score, the split
AUDITIONS (every candidate threshold scrubbable), branch growth with γ-pruning, leaf values,
the η update, the residual-morphed table for rounds 2–3, prediction assembly through the
sigmoid, testing, every hyperparameter, and the pros/cons verdict. Every number in the
narration is computed from the user's real data by the exact-math tracer (viz/xgboost.py).
"""

from __future__ import annotations

from ..explain.facts import ModelFacts
from ..viz.schema import ModelTrace, XGBNode
from . import register_lesson
from ._steps import (
    DUR_SCENE,
    DUR_SHOW,
    AnimDirective,
    Chapter,
    MathBlock,
    Symbol,
    chapter,
    data_chapter,
    explainer_for_chain,
    hyperparams_chapter,
    quiz_chapter,
    roadmap_chapter,
    step,
    testing_chapter,
    verdict_chapter,
)


def _nodes(root: XGBNode) -> list[XGBNode]:
    out, queue = [], [root]
    while queue:
        n = queue.pop(0)
        out.append(n)
        if n.left:
            queue.append(n.left)
        if n.right:
            queue.append(n.right)
    return out


def _leaves(root: XGBNode) -> list[XGBNode]:
    return [n for n in _nodes(root) if n.leaf]


def _sym(*pairs: tuple[str, str]) -> list[Symbol]:
    return [Symbol(sym=s, means=m) for s, m in pairs]


@register_lesson("xgboost")
def xgboost_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    b = trace.boosting
    if b is None:  # tracer fell back (shouldn't happen) — play the guided generic lesson
        from . import generic

        return generic.build(trace, facts, ["xgboost", "trees"])

    cls = trace.task == "classification"
    lam, gamma, eta = b.reg_lambda, b.gamma, b.eta
    r1 = b.rounds[0]
    root = r1.root
    rs = root.stats
    winner = next((t for t in root.trials if t.kept), None)
    leaves = _leaves(root)
    pos = trace.labels[1] if (cls and trace.labels) else None
    guide = explainer_for_chain(["trees"])

    # ---- concept ladder ------------------------------------------------------------------
    ensembles = chapter(
        "ensembles",
        "Why many small trees?",
        [
            step(
                "crowd",
                "One giant model can memorise the data and fall apart on new rows. XGBoost's "
                "answer is a CROWD of small, weak trees: each new tree only has one job — fix "
                "what the trees before it still get wrong — and their answers add up. That's a "
                "'boosted ensemble', and it's the reigning champion on tables like yours.",
                duration_ms=DUR_SCENE,
                anim=AnimDirective(kind="note"),
            )
        ],
        kicker="The ensemble idea in one breath",
    )
    tree_intro = chapter(
        "what-is-a-tree",
        "What is a decision tree?",
        [
            step(
                "tree",
                f"A decision tree is a chain of yes/no questions about your columns — this one "
                f"starts with “is {root.feature} ≤ {root.threshold}?”"
                if winner
                else "A decision tree is a chain of yes/no questions about your columns."
                " Rows flow down the branches until they land in a leaf, and the leaf is the "
                "answer. Watch one grow on your data.",
                duration_ms=DUR_SCENE,
                anim=AnimDirective(kind="tree-grow", ref={"round": 0}, substeps=len(_nodes(root))),
            )
        ],
        kicker="Prerequisite #1",
    )
    stump = chapter(
        "what-is-a-stump",
        "What is a stump?",
        [
            step(
                "stump",
                "Cut a tree down to ONE question and you get a stump — the weakest useful "
                "learner there is. Alone it's barely better than guessing. XGBoost's trick: "
                "hundreds of shallow trees, each nudging the answer a little, beat one deep "
                "know-it-all. Weak + weak + weak = strong.",
                duration_ms=DUR_SCENE,
                anim=AnimDirective(kind="tree-grow", ref={"round": 0, "max_depth": 1}, substeps=3),
            )
        ],
        kicker="Prerequisite #2 — the weak learner",
    )

    # ---- the math, live ------------------------------------------------------------------
    base_narr = (
        f"Every prediction starts from the same base guess. For a yes/no outcome XGBoost "
        f"starts at a raw score of {b.base_score:g} — a 50/50 probability — before any tree "
        f"has spoken."
        if cls
        else f"Every prediction starts from the same base guess: the average outcome, "
        f"{b.base_score:g}. The trees only learn the CORRECTIONS to that guess."
    )
    base_chapter = chapter(
        "base-score",
        "The starting guess",
        [
            step(
                "base",
                base_narr,
                duration_ms=DUR_SCENE,
                anim=AnimDirective(kind="note"),
                math=[
                    MathBlock(
                        name="The prediction so far",
                        formula="F₀(x) = base",
                        plain="Before round 1, every row gets the same score.",
                        symbols=_sym(("F₀(x)", "the model's raw score before any tree"),
                                     ("base", "the starting guess")),
                        worked=f"base = {b.base_score:g}"
                        + (" → p = 1/(1+e⁰) = 0.5, a coin flip" if cls else ""),
                    )
                ],
            )
        ],
        kicker="Round 0 — before any tree",
    )

    demo = r1.table[0] if r1.table else None
    g_worked = (
        f"a row with actual = {demo['actual']} and current p = {demo['current']} → "
        f"g = {demo['current']} − {'1' if demo['residual'] < 0 or demo['g'] < 0 else '0'}"
        f" = {demo['g']:+g}"
        if cls and demo
        else "g = prediction − truth for every row"
    )
    gh = chapter(
        "residuals-g-h",
        "Residuals, g and h",
        [
            step(
                "residuals",
                "Here is the training table as round 1 actually sees it: everyone's current "
                "prediction is the base guess, and the RESIDUAL column is what's still wrong "
                "(truth − prediction). XGBoost summarises each row's error with two numbers: "
                "the gradient g (which way, and how hard, to push) and the hessian h (how much "
                "this row's opinion should count).",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="round-table", ref={"round": 0}, substeps=len(r1.table) or 1),
                math=[
                    MathBlock(
                        name="Gradient — the push",
                        formula="g = p − y" if cls else "g = ŷ − y",
                        plain="Positive g = the guess is too high, push down; negative = too low, push up.",
                        symbols=_sym(("g", "gradient — the direction and size of the error"),
                                     ("p" if cls else "ŷ", "the current prediction"),
                                     ("y", "the true answer (1/0)" if cls else "the true value")),
                        worked=g_worked,
                    )
                ],
            ),
            step(
                "hessian",
                "The hessian sounds scary, so let's break it down. The loss is a curve; the "
                "gradient is its SLOPE; the hessian is the slope OF the slope — how quickly the "
                "curve bends. For yes/no problems h = p·(1−p): it peaks at p = 0.5 (the model "
                "is unsure — lots to learn from this row) and shrinks near 0 or 1 (already "
                "confident). For number targets h is just 1 — every row counts equally.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="widget"),
                widget="hessian-bowl",
                math=[
                    MathBlock(
                        name="Hessian — the confidence weight",
                        formula="h = p·(1 − p)" if cls else "h = 1",
                        plain="How much evidence this row contributes to a leaf.",
                        symbols=_sym(("h", "hessian — curvature of the loss, used as a weight"),
                                     ("p", "the current predicted probability")),
                        worked=(
                            f"p = 0.5 → h = 0.5·0.5 = 0.25 for every row in round 1 — "
                            f"the root collects Σh = {rs.sum_h:g}"
                            if cls
                            else "h = 1 per row → Σh at the root is just the row count "
                            f"({rs.n})"
                        ),
                    )
                ],
            ),
        ],
        kicker="How XGBoost measures 'wrong'",
    )

    derivation = chapter(
        "where-similarity-comes-from",
        "Where the formula comes from",
        [
            step(
                "g-cancel",
                "First, the intuition for (Σg)²: gradients are pushes with DIRECTION. In a "
                "mixed group the pushes point both ways and CANCEL — Σg lands near zero, "
                "similarity near zero, nothing to learn. Gather rows that agree and the pushes "
                "STACK — Σg grows, and squaring rewards that agreement hard. Watch the same "
                "g's cancel, then stack.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="widget"),
                widget="g-cancel",
            ),
            step(
                "derivation",
                "And the honest origin (exam gold): XGBoost approximates the loss around the "
                "current prediction with a second-order Taylor expansion — g and h are exactly "
                "its two coefficients. Minimising that quadratic for a leaf gives the best leaf "
                "value w* = −Σg/(Σh+λ); plug w* back in and the loss REDUCTION the leaf earns "
                "is ½·(Σg)²/(Σh+λ) — the similarity score. Gain is just 'reduction after the "
                "split minus before, minus the γ toll'. Nothing was pulled from a hat.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="note"),
                math=[
                    MathBlock(
                        name="The derivation in three lines",
                        formula="loss ≈ Σ (gᵢ·w + ½hᵢ·w²) + ½λw² → w* = −Σg/(Σh+λ) → "
                        "reduction = ½·(Σg)²/(Σh+λ)",
                        plain="Approximate the loss as a parabola in the leaf value w, take the "
                        "minimum, read off how much loss the leaf removes.",
                        symbols=_sym(("w", "the leaf's output value (what we're choosing)"),
                                     ("g, h", "slope and curvature of the loss per row"),
                                     ("w*", "the parabola's minimum — the leaf value formula"),
                                     ("½", "a constant that cancels when comparing splits")),
                        worked=f"root: w* = −({rs.sum_g:+g})/({rs.sum_h:g}+{lam:g}) and the "
                        f"reduction ∝ {rs.similarity:g} — the numbers you just saw",
                    )
                ],
            ),
        ],
        kicker="The Taylor-expansion origin of similarity, leaf values, and gain",
    )

    similarity = chapter(
        "root-similarity",
        "The similarity score",
        [
            step(
                "similarity",
                f"Before splitting, score the whole group: similarity = (Σg)²/(Σh+λ). Read it "
                f"as 'how much do these rows agree about which way to push?' Your root: the "
                f"{rs.n} training rows carry Σg = {rs.sum_g:+g} and Σh = {rs.sum_h:g}, and with "
                f"λ = {lam:g} the similarity is {rs.similarity:g}. A good split makes two "
                f"groups whose similarities BEAT the parent's — g's that agree, gathered "
                f"together.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="note"),
                math=[
                    MathBlock(
                        name="Similarity score",
                        formula="similarity = (Σg)² / (Σh + λ)",
                        plain="Agreement squared, damped by evidence and the regulariser.",
                        symbols=_sym(("Σg", "sum of the group's gradients — cancels out when they disagree"),
                                     ("Σh", "sum of the group's hessians — the group's evidence"),
                                     ("λ", "L2 regularisation — keeps small groups humble")),
                        worked=f"root: ({rs.sum_g:+g})² / ({rs.sum_h:g} + {lam:g}) = {rs.similarity:g}",
                    )
                ],
            )
        ],
        kicker="The number every split tries to raise",
    )

    trials_steps = []
    if winner and root.trials:
        trials_steps.append(
            step(
                "auditions",
                f"Now the show-piece: the split auditions. XGBoost tries "
                f"{len(root.trials)} candidate cut-points across {', '.join(b.trial_features)} "
                f"— for each one it splits the rows, computes both sides' similarity, and "
                f"scores the gain. Watch the leaderboard build, one candidate at a time.",
                duration_ms=DUR_SHOW + 6_000,
                anim=AnimDirective(
                    kind="split-trials", ref={"round": 0, "node": "r"}, substeps=len(root.trials)
                ),
                math=[
                    MathBlock(
                        name="Gain — is the split worth it?",
                        formula="gain = sim_L + sim_R − sim_parent − γ",
                        plain="How much more agreement the two sides have than the un-split group.",
                        symbols=_sym(("sim_L, sim_R", "similarity of the left / right group"),
                                     ("sim_parent", "similarity before splitting"),
                                     ("γ", "the toll a split must pay — below it, prune")),
                        worked=(
                            f"winner “{winner.feature} ≤ {winner.threshold:g}”: "
                            f"{winner.left.similarity:g} + {winner.right.similarity:g} − "
                            f"{rs.similarity:g} − {gamma:g} = {winner.gain:g}"
                        ),
                    )
                ],
            )
        )
    trials = chapter(
        "root-trials",
        "The split auditions",
        trials_steps
        or [step("no-split", "This data is so uniform the root couldn't find a worthwhile "
                 "split — the tree stays a single leaf.", anim=AnimDirective(kind="note"))],
        kicker="Every candidate, scored live",
    )

    grow = chapter(
        "grow-branches",
        "Growing the branches",
        [
            step(
                "grow",
                f"The winning question splits the rows, and each side runs its OWN auditions — "
                f"same hunt, smaller crowd — down to depth {max(n.depth for n in _nodes(root))}. "
                f"Whenever the best gain can't beat γ = {gamma:g}, the branch is PRUNED and "
                f"becomes a leaf: the split isn't worth the complexity it adds.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="tree-grow", ref={"round": 0}, substeps=len(_nodes(root))),
            )
        ],
        kicker="Repeat per depth, prune what doesn't pay",
    )

    lv = leaves[0] if leaves else None
    leaf_chapter = chapter(
        "leaf-values",
        "What the leaves say",
        [
            step(
                "leaves",
                f"Each leaf turns its rows' errors into ONE correction: −Σg/(Σh+λ). Tree 1 "
                f"grew {len(leaves)} leaves; their values are the amounts this tree will "
                f"nudge each row's score.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="leaf-values", ref={"round": 0}, substeps=max(1, len(leaves))),
                math=[
                    MathBlock(
                        name="Leaf output",
                        formula="value = −Σg / (Σh + λ)",
                        plain="Push opposite to the group's average error, damped by λ.",
                        symbols=_sym(("Σg", "the leaf's summed gradients"),
                                     ("Σh", "the leaf's summed evidence"),
                                     ("λ", "the regulariser")),
                        worked=(
                            f"first leaf ({lv.stats.n} rows): −({lv.stats.sum_g:+g}) / "
                            f"({lv.stats.sum_h:g} + {lam:g}) = {lv.value:g}"
                            if lv
                            else ""
                        ),
                    )
                ],
            )
        ],
        kicker="−Σg/(Σh+λ), per leaf",
    )

    r2 = b.rounds[1] if len(b.rounds) > 1 else None
    eta_update = chapter(
        "eta-update",
        "The η update",
        [
            step(
                "eta",
                f"Tree 1's corrections aren't applied at full strength — they're scaled by the "
                f"learning rate η = {eta:g}. Watch the table transform: every row's prediction "
                f"moves, and the residuals SHRINK. Whatever error is left becomes the next "
                f"tree's whole world.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="residual-morph", ref={"from": 0, "to": 1},
                                   substeps=len((r2 or r1).table) or 1),
                math=[
                    MathBlock(
                        name="The boosting update",
                        formula="F₁(x) = F₀(x) + η · tree₁(x)",
                        plain="New score = old score + a shrunken step in the tree's direction.",
                        symbols=_sym(("η", "learning rate — trust per tree"),
                                     ("tree₁(x)", "the leaf value row x lands in")),
                        worked=(
                            f"row 1: {b.base_score:g} + {eta:g}·(leaf) → current moves from "
                            f"{r1.table[0]['current']} to {r2.table[0]['current']}"
                            if r2 and r1.table and r2.table
                            else f"F₁ = {b.base_score:g} + {eta:g}·tree₁(x)"
                        ),
                    )
                ],
            )
        ],
        kicker="Shrink the step, keep the direction",
    )

    later_rounds: list[Chapter] = []
    for r in b.rounds[1:]:
        w = next((t for t in r.root.trials if t.kept), None)
        later_rounds.append(
            chapter(
                f"round-{r.index + 1}",
                f"Round {r.index + 1}: a new tree for what's left",
                [
                    step(
                        f"round-{r.index + 1}",
                        f"The transformed table IS the new training set — residuals are the "
                        f"new target. Tree {r.index + 1} runs the same auditions on it"
                        + (
                            f" and picks “{w.feature} ≤ {w.threshold:g}” (gain {w.gain:g})"
                            if w
                            else ""
                        )
                        + ". Notice the gains getting smaller: each round has less error left "
                        "to explain.",
                        duration_ms=DUR_SHOW,
                        anim=AnimDirective(
                            kind="split-trials",
                            ref={"round": r.index, "node": "r"},
                            substeps=max(1, len(r.root.trials)),
                        ),
                    )
                ],
                kicker="Fit the leftovers, again",
            )
        )

    n_test = len(trace.test_rows or [])
    assembly = chapter(
        "assembly",
        "Assembling a prediction",
        [
            step(
                "assemble",
                "Time to predict a row the model has never seen. It walks down EVERY tree, "
                "collects each leaf's η-scaled correction, and adds them to the base score"
                + (
                    f" — then the sigmoid squeezes that raw score into a probability of "
                    f"“{pos}”."
                    if cls and pos
                    else "."
                ),
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="boosting-assembly", ref={"row": 0},
                                   substeps=len(b.rounds) + 2),
                math=(
                    [
                        MathBlock(
                            name="Score → probability",
                            formula="p = 1 / (1 + e^(−F))",
                            plain="Big negative score → near 0; big positive → near 1.",
                            symbols=_sym(("F", "base + η·(tree₁ + tree₂ + …)"),
                                         ("p", f"probability of “{pos}”" if pos else "probability")),
                            worked=(
                                f"row 1: F = {trace.test_rows[0].get('boost_score')} → "
                                f"p = {trace.test_rows[0].get('boost_prob')}"
                                if cls and trace.test_rows
                                else ""
                            ),
                        )
                    ]
                    if cls
                    else []
                ),
            )
        ],
        kicker=f"base + η·Σ trees, on {n_test} held-out rows next",
    )

    chapters = [
        ensembles, tree_intro, stump, data_chapter(trace), base_chapter, gh, similarity,
        derivation, trials, grow, leaf_chapter, eta_update, *later_rounds, assembly,
        testing_chapter(trace), hyperparams_chapter(trace, facts),
        verdict_chapter(facts, guide, "XGBoost"),
    ]
    quiz = quiz_chapter(facts, "XGBoost")
    if quiz:
        chapters.append(quiz)
    return [roadmap_chapter("XGBoost, from zero", chapters,
                            str(guide.get("one_liner", ""))), *chapters]
