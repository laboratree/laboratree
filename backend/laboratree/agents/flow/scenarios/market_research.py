"""Market Research flow — sizing, competition, and segmentation.

Market-intel phases (sizing, competitor scan, trend scan, pricing) intentionally have NO
executors: the Market Intel Lab doesn't exist yet, so the Supervisor spawns the DeepAgent with
the search toolbelt for each — the designed gap-filler use case. Segmentation runs a real
clustering component on the project dataset; the survey/field/reporting machinery is shared.
"""

from __future__ import annotations

from .. import FlowContext, PhaseResult, alias_flow, phase
from . import ngo_education
from .ngo_education import _component_phase, _ensure_dataset

FLOW_KEY = "market-research"

alias_flow(ngo_education.FLOW_KEY, FLOW_KEY)


@phase(FLOW_KEY, "segmentation", lab="modeling")
async def segmentation(ctx: FlowContext) -> PhaseResult:
    await _ensure_dataset(ctx)
    return await _component_phase(
        ctx, "segmentation", "model.clustering.kmeans", {"n_clusters": 3}, "modeling",
        "respondents clustered into 3 segments")


DEEP_STAGES: dict[str, str] = {
    "market-sizing": "Size the target market (TAM/SAM/SOM where possible): search for credible "
                     "figures, triangulate at least two sources, and state method + confidence.",
    "competitor-scan": "Identify the main competitors: offerings, pricing where public, and "
                       "positioning; every claim must cite a searched source.",
    "trend-scan": "Identify the 3-5 most consequential market trends, incl. community/consumer "
                  "sentiment (reddit) alongside published analyses.",
    "pricing-analysis": "Assess pricing structures and willingness-to-pay signals from public "
                        "sources; recommend a pricing approach with its evidence.",
}
