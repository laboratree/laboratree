"""Paper Experiment API — reproduce a paper's pipeline, then fork nodes and compare to the paper."""

from __future__ import annotations

import io
import logging
import uuid
from datetime import UTC
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from ..agents.run_executor import RunFailed, execute_component
from ..core.deps import PrincipalDep, SessionDep
from ..core.llm.context import use_llm_context
from ..core.repro import dataframe_hash
from ..core.storage import get_blob_store
from ..labs.paper import llm as paper_llm
from ..labs.paper.experiment.demo import generate_demo_dataset
from ..labs.paper.experiment.service import _paper_text, create_experiment, load_dataset_df
from ..papers.models import Experiment, ExperimentStatus, Paper
from ..projects.models import Dataset, GateStatus, GateTask

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["experiments"])


class NodeRunIn(BaseModel):
    dataset_id: uuid.UUID
    component_id: str | None = None       # override the node's component to "fork"
    params: dict[str, Any] = {}


class ExplainStepIn(BaseModel):
    title: str
    detail: str = ""


@router.post("/preprocess-explainer")
async def preprocess_explainer(
    body: ExplainStepIn, principal: PrincipalDep, session: SessionDep
) -> dict[str, Any]:
    """Explain an unusual pipeline step (fixed effects, clustered SEs, IV, …) to a beginner with a
    worked example table — generated on demand and cached (the explanation is the same everywhere)."""
    import asyncio

    from ..core.cache import cache_key, cached_json
    from ..core.config import settings
    from ..labs.paper.experiment.explain import explain_step

    def _run() -> dict[str, Any]:
        with use_llm_context("paper", "preprocess_explain"):
            return explain_step(body.title, body.detail, paper_llm.default_complete)

    key = cache_key("ppexplain", "global", body.title.strip().lower(), body.detail.strip().lower()[:300])
    return await cached_json(key, settings.ideation_cache_ttl_s, lambda: asyncio.to_thread(_run))


async def _require_experiment(session, principal, experiment_id: uuid.UUID) -> Experiment:
    exp = await session.get(Experiment, experiment_id)
    if exp is None or exp.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="experiment not found")
    return exp


def _detail(exp: Experiment) -> dict[str, Any]:
    return {
        "id": str(exp.id),
        "paper_id": str(exp.paper_id),
        "status": exp.status.value,
        "walkthrough": exp.walkthrough,
        "fetch_report": exp.fetch_report,
    }


@router.post("/papers/{paper_id}/experiment", status_code=201)
async def start_experiment(
    paper_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> dict[str, Any]:
    paper = await session.get(Paper, paper_id)
    if paper is None or paper.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="paper not found")
    if not paper.card:
        raise HTTPException(status_code=409, detail="generate the Paper Card first")

    with use_llm_context("paper", "experiment_fetch", project_id=paper.project_id,
                         org_id=principal.org_id):
        result = await create_experiment(
            session,
            org_id=principal.org_id,
            project_id=paper.project_id,
            paper=paper,
            complete_fn=paper_llm.default_complete,
        )
    detail = _detail(result.experiment)
    detail["gate_id"] = str(result.gate.id) if result.gate else None
    return detail


@router.get("/papers/{paper_id}/experiment")
async def latest_experiment(
    paper_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> dict[str, Any]:
    """Return the most recent experiment for this paper so revisiting the Experiment Lab restores
    the pipeline, fetched/generated datasets, and gate — nothing is lost between visits."""
    exp = (
        await session.execute(
            select(Experiment)
            .where(Experiment.paper_id == paper_id, Experiment.org_id == principal.org_id)
            .order_by(Experiment.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if exp is None:
        raise HTTPException(status_code=404, detail="no experiment yet")
    return _detail(exp)


@router.post("/experiments/{experiment_id}/demo-data", status_code=201)
async def demo_data(
    experiment_id: uuid.UUID,
    principal: PrincipalDep,
    session: SessionDep,
    n_rows: int = 60,
) -> dict[str, Any]:
    """Synthesize a realistic demo dataset from the paper's variables so the user can always proceed."""
    exp = await _require_experiment(session, principal, experiment_id)
    paper = await session.get(Paper, exp.paper_id)
    if paper is None or paper.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="paper not found")

    import pandas as pd

    text = await _paper_text(session, paper)
    with use_llm_context("paper", "demo_data", project_id=exp.project_id, org_id=principal.org_id):
        demo = generate_demo_dataset(text, paper.card or {}, n_rows, paper_llm.default_complete)
    df = pd.DataFrame(demo["records"], columns=demo["columns"] or None)
    if df.empty:
        raise HTTPException(status_code=400, detail="demo-data generation produced no rows")

    key = f"experiments/{exp.project_id}/{uuid.uuid4()}/demo.csv"
    data = df.to_csv(index=False).encode()
    get_blob_store().put(key, data)
    ds = Dataset(
        org_id=principal.org_id, project_id=exp.project_id, name="demo (synthetic)",
        storage_key=key, content_hash=dataframe_hash(df),
        n_rows=int(len(df)), n_cols=int(df.shape[1]), synthetic=True,
    )
    session.add(ds)
    await session.flush()

    report = dict(exp.fetch_report)
    # Build a NEW list (not append to the shared one) so SQLAlchemy sees a real change on the
    # JSONB column — a shallow-copied nested list would be mutated in place and go unpersisted.
    report["fetched"] = [
        *(report.get("fetched") or []),
        {
            "name": "demo (synthetic)", "filename": "demo.csv", "dataset_id": str(ds.id),
            "resolver": "demo_llm", "source": "llm", "n_rows": int(len(df)),
            "n_cols": int(df.shape[1]), "synthetic": True,
        },
    ]
    exp.fetch_report = report
    flag_modified(exp, "fetch_report")
    exp.status = ExperimentStatus.READY
    await session.commit()
    await session.refresh(exp)
    return {**_detail(exp), "caveat": demo["caveat"]}


@router.post("/experiments/{experiment_id}/fetch-data", status_code=201)
async def refetch_data(
    experiment_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> dict[str, Any]:
    """Re-run the dataset auto-fetch (direct URL → OpenML → UCI resolvers) on an EXISTING
    experiment and append anything resolved — so revisiting an old experiment can still pull the
    paper's real data without starting over."""
    import asyncio

    from ..labs.paper.experiment.fetch import DataFetchAgent, extract_dataset_refs
    from ..labs.paper.experiment.service import store_fetched_dataset

    exp = await _require_experiment(session, principal, experiment_id)
    paper = await session.get(Paper, exp.paper_id)
    if paper is None or paper.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="paper not found")

    text = await _paper_text(session, paper)
    with use_llm_context("paper", "refetch_data", project_id=exp.project_id, org_id=principal.org_id):
        refs = extract_dataset_refs(text, paper_llm.default_complete)
    # resolvers do real (rate-limited) HTTP — keep them off the event loop
    outcome = await asyncio.to_thread(DataFetchAgent().resolve, refs)
    if not outcome.fetched:
        why = "; ".join(f"{g.name}: {g.reason}" for g in outcome.unresolved) or "no dataset references found"
        raise HTTPException(status_code=404, detail=f"auto-fetch found nothing this time — {why}")

    added = []
    for fr in outcome.fetched:
        ds = await store_fetched_dataset(
            session, org_id=principal.org_id, project_id=exp.project_id, fr=fr
        )
        added.append({
            "name": fr.ref.name, "filename": fr.filename, "dataset_id": str(ds.id),
            "resolver": fr.resolver, "source": fr.source,
            "n_rows": ds.n_rows, "n_cols": ds.n_cols,
        })
    report = dict(exp.fetch_report)
    report["fetched"] = [*(report.get("fetched") or []), *added]
    report["unresolved"] = [g.__dict__ for g in outcome.unresolved]
    exp.fetch_report = report
    flag_modified(exp, "fetch_report")
    exp.status = ExperimentStatus.READY
    await session.commit()
    await session.refresh(exp)
    return _detail(exp)


@router.post("/experiments/{experiment_id}/master-dataset", status_code=201)
async def build_master_dataset(
    experiment_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> dict[str, Any]:
    """Consolidate every fetched/uploaded dataset into ONE master dataset: align columns by
    (case-insensitive) name, stack the rows, drop exact duplicates and ID-like columns, and
    register the result — the single table the rest of the pipeline runs on."""
    import io as _io

    import pandas as pd

    exp = await _require_experiment(session, principal, experiment_id)
    fetched = (exp.fetch_report or {}).get("fetched") or []
    sources = [f for f in fetched if f.get("resolver") != "master"]
    if not sources:
        raise HTTPException(status_code=400, detail="no datasets to consolidate — fetch or upload first")

    frames: list[pd.DataFrame] = []
    used: list[str] = []
    for f in sources:
        ds = await session.get(Dataset, uuid.UUID(f["dataset_id"]))
        if ds is None:
            continue
        try:
            df = pd.read_csv(_io.BytesIO(get_blob_store().get(ds.storage_key)))
        except Exception as exc:
            log.warning("skipping dataset %r during master build — unreadable CSV: %s",
                        f.get("name") or ds.id, exc)
            continue
        df.columns = [str(c).strip().lower() for c in df.columns]
        frames.append(df)
        used.append(f.get("name") or "dataset")
    if not frames:
        raise HTTPException(status_code=410, detail="dataset bytes missing")

    master = pd.concat(frames, ignore_index=True, sort=False)
    id_like = [c for c in master.columns if c in ("id", "index", "idx", "sno", "unnamed: 0")]
    master = master.drop(columns=id_like, errors="ignore").drop_duplicates().reset_index(drop=True)

    key = f"experiments/{exp.project_id}/{uuid.uuid4()}/master.csv"
    get_blob_store().put(key, master.to_csv(index=False).encode())
    ds = Dataset(
        org_id=principal.org_id, project_id=exp.project_id,
        name=f"master dataset ({len(used)} source{'s' if len(used) != 1 else ''})",
        storage_key=key, content_hash=dataframe_hash(master),
        n_rows=int(len(master)), n_cols=int(master.shape[1]),
        synthetic=all(bool(f.get("synthetic")) for f in sources),
    )
    session.add(ds)
    await session.flush()

    report = dict(exp.fetch_report)
    report["fetched"] = [
        *(report.get("fetched") or []),
        {
            "name": ds.name, "filename": "master.csv", "dataset_id": str(ds.id),
            "resolver": "master", "source": " + ".join(used),
            "n_rows": ds.n_rows, "n_cols": ds.n_cols, "synthetic": ds.synthetic,
        },
    ]
    exp.fetch_report = report
    flag_modified(exp, "fetch_report")
    await session.commit()
    await session.refresh(exp)
    return _detail(exp)


@router.get("/experiments/{experiment_id}/evidence-bundle")
async def evidence_bundle(
    experiment_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
):
    """One-click reproducibility receipts: everything needed to audit this experiment — the
    paper's claims (with their grounded quotes), every dataset's content hash, the pipeline,
    and every run with its provenance-locked Evidence values + repro manifest. Downloads as JSON."""
    import json as _json
    from datetime import datetime

    from fastapi import Response

    from ..projects.models import Evidence, Run

    exp = await _require_experiment(session, principal, experiment_id)
    paper = await session.get(Paper, exp.paper_id)
    card = (paper.card if paper else None) or {}
    grounding = card.get("grounding") or {}

    # claims + their receipts (paper-verified sentences)
    claims = []
    for i, m in enumerate(card.get("models_used") or []):
        if isinstance(m, dict) and m.get("result"):
            refs = grounding.get(f"model:{i}") or []
            claims.append({
                "claim": f"{m.get('name')}: {m.get('result')}",
                "verified_in_paper": bool(refs),
                "supporting_quote": refs[0]["quote"] if refs else None,
            })
    if card.get("results"):
        refs = grounding.get("results") or []
        claims.append({
            "claim": card["results"], "verified_in_paper": bool(refs),
            "supporting_quote": refs[0]["quote"] if refs else None,
        })

    # datasets with content hashes
    datasets = []
    for f in (exp.fetch_report or {}).get("fetched") or []:
        ds = await session.get(Dataset, uuid.UUID(f["dataset_id"]))
        datasets.append({
            **{k: f.get(k) for k in ("name", "resolver", "source", "n_rows", "n_cols", "synthetic")},
            "content_hash": ds.content_hash if ds else None,
        })

    # every run belonging to this experiment + its Evidence entries
    runs_out = []
    run_rows = (
        await session.execute(
            select(Run)
            .where(Run.org_id == principal.org_id,
                   Run.params["experiment_id"].astext == str(exp.id))
            .order_by(Run.created_at)
        )
    ).scalars().all()
    for r in run_rows:
        ev = (
            await session.execute(select(Evidence).where(Evidence.run_id == r.id))
        ).scalars().all()
        params = {k: v for k, v in (r.params or {}).items() if k != "experiment_id"}
        runs_out.append({
            "run_id": str(r.id),
            "component_id": r.component_id,
            "status": str(r.status.value if hasattr(r.status, "value") else r.status),
            "created_at": str(r.created_at),
            "params": params,
            "repro_manifest": r.repro_manifest,
            "evidence": [
                {"label": e.label, "kind": e.kind, "value": (e.value or {}).get("v")} for e in ev
            ],
        })

    bundle = {
        "bundle": "laboratree.evidence",
        "generated_at": datetime.now(UTC).isoformat(),
        "paper": {"title": paper.title if paper else "", "filename": paper.filename if paper else ""},
        "paper_claims": claims,
        "datasets": datasets,
        "pipeline": [
            {k: n.get(k) for k in ("kind", "title", "component_id", "params")}
            for n in (exp.walkthrough or [])
        ],
        "runs": runs_out,
        "note": "Every metric here originates from a real execution (Evidence Ledger); dataset "
        "content hashes + repro manifests let a third party re-run and compare.",
    }
    return Response(
        content=_json.dumps(bundle, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition":
                f'attachment; filename="evidence-bundle-{str(exp.id)[:8]}.json"'
        },
    )


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> dict[str, Any]:
    return _detail(await _require_experiment(session, principal, experiment_id))


@router.post("/experiments/{experiment_id}/data", status_code=201)
async def upload_experiment_data(
    experiment_id: uuid.UUID,
    principal: PrincipalDep,
    session: SessionDep,
    name: str,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Manually provide a dataset the auto-fetch agent could not retrieve (resolves the HITL gate)."""
    exp = await _require_experiment(session, principal, experiment_id)
    data = await file.read()

    import pandas as pd

    key = f"experiments/{exp.project_id}/{uuid.uuid4()}/{file.filename}"
    get_blob_store().put(key, data)
    try:
        df = pd.read_csv(io.BytesIO(data))
        n_rows, n_cols, chash = int(len(df)), int(df.shape[1]), dataframe_hash(df)
    except Exception as exc:
        log.warning("uploaded file %r is not parseable as CSV; storing without shape/hash: %s",
                    file.filename, exc)
        n_rows = n_cols = None
        chash = ""
    ds = Dataset(org_id=principal.org_id, project_id=exp.project_id, name=name,
                 storage_key=key, content_hash=chash, n_rows=n_rows, n_cols=n_cols)
    session.add(ds)
    await session.flush()

    report = dict(exp.fetch_report)
    report["fetched"] = [
        *(report.get("fetched") or []),
        {"name": name, "filename": file.filename, "dataset_id": str(ds.id),
         "resolver": "manual_upload", "source": "human", "n_rows": n_rows, "n_cols": n_cols},
    ]
    remaining = [u for u in report.get("unresolved", []) if u.get("name", "").lower() != name.lower()]
    report["unresolved"] = remaining
    exp.fetch_report = report  # reassign + flag so the JSONB change is detected
    flag_modified(exp, "fetch_report")

    if not remaining:
        exp.status = ExperimentStatus.READY
        run_id = report.get("run_id")
        if run_id:
            gate = (
                await session.execute(
                    select(GateTask).where(
                        GateTask.run_id == uuid.UUID(run_id), GateTask.status == GateStatus.PENDING
                    )
                )
            ).scalar_one_or_none()
            if gate is not None:
                gate.status = GateStatus.APPROVED
                gate.response = {"resolved_by": "manual_upload"}

    await session.commit()
    await session.refresh(exp)
    return _detail(exp)


@router.post("/experiments/{experiment_id}/nodes/{node_id}/run", status_code=201)
async def run_node(
    experiment_id: uuid.UUID,
    node_id: str,
    body: NodeRunIn,
    principal: PrincipalDep,
    session: SessionDep,
) -> dict[str, Any]:
    exp = await _require_experiment(session, principal, experiment_id)
    node = next((n for n in exp.walkthrough if n.get("id") == node_id), None)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")

    # Prefer the explicit fork, then the paper's mapped model, then a stand-in for unknown models
    # (SVM, k-NN, neural nets, custom) so a node is never a dead end.
    component_id = body.component_id or node.get("component_id") or node.get("suggested_component")
    if not component_id:
        raise HTTPException(status_code=400, detail="node has no runnable component; pass component_id to fork")
    stand_in = not node.get("component_id") and not body.component_id

    dataset = await session.get(Dataset, body.dataset_id)
    if dataset is None or dataset.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="dataset not found")

    params = {**(node.get("params") or {}), **body.params, "experiment_id": str(exp.id)}

    df = load_dataset_df(dataset)
    # Resolve the target to a REAL column — demo/uploaded CSVs may name it differently than the
    # Paper Card (e.g. card says 'class' but the demo column is 'classification'). Prefer an exact
    # (case-insensitive) match, then a loose match, then fall back to the last column (the usual
    # target convention). Without this the model raises KeyError and the whole run "fails".
    tgt = params.get("target")
    if tgt is not None and tgt not in df.columns and len(df.columns):
        low = str(tgt).lower()
        match = next((c for c in df.columns if str(c).lower() == low), None)
        if match is None:
            match = next(
                (c for c in df.columns if low in str(c).lower() or str(c).lower() in low), None
            )
        params["target"] = match or df.columns[-1]

    # Pre-flight: for a model node, catch the common 'won't run' cases (no numeric features, a
    # one-value target, too few rows) and return a CLEAR, actionable reason instead of a cryptic
    # sklearn crash deep in the run.
    if component_id.startswith("model."):
        from ..labs.modeling.evaluation.readiness import readiness_reason

        reason = readiness_reason(df, str(params.get("target", "")), params.get("features"))
        if reason:
            raise HTTPException(status_code=422, detail=f"Can't run this model yet — {reason}")

    try:
        result = await execute_component(
            session,
            org_id=principal.org_id,
            project_id=exp.project_id,
            component_id=component_id,
            params={k: v for k, v in params.items() if k != "experiment_id"},
            inputs={"dataset": df},
            lab="paper.experiment",
        )
        # tag the Run so the evidence bundle can gather every run of THIS experiment
        result.run.params = {**(result.run.params or {}), "experiment_id": str(exp.id)}
        flag_modified(result.run, "params")
        await session.commit()
    except RunFailed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    card = {}
    paper = await session.get(Paper, exp.paper_id)
    if paper is not None:
        card = paper.card or {}
    return {
        "run_id": str(result.run.id),
        "component_id": component_id,
        "forked": bool(body.component_id and body.component_id != node.get("component_id")),
        "metrics": result.outputs.get("metrics", {}),
        "task": result.outputs.get("task", ""),
        "predictions": result.outputs.get("predictions", []),
        "paper_reported": card.get("results", ""),
        "synthetic": bool(dataset.synthetic),
        "stand_in": stand_in,
    }
