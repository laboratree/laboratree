"""Clustering expansion — hierarchical (agglomerative) and spectral clustering.

Reuses the package's shared _cluster_run loop (scale -> fit -> silhouette + sizes -> emit).
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, RunContext, register

from . import _cluster_run, _spec


@register
class HierarchicalClusteringModel(Component):
    spec = _spec(
        "model.clustering.hierarchical", "Hierarchical Clustering",
        "Repeatedly merges the two closest groups until k remain — no random start, "
        "great for dendrogram-style structure.",
        {
            "n_clusters": {"type": "integer", "default": 3, "title": "Clusters (k)"},
            "linkage": {
                "type": "string", "default": "ward", "title": "Linkage",
                "enum": ["ward", "complete", "average", "single"],
            },
        },
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.cluster import AgglomerativeClustering

        k = int(ctx.params.get("n_clusters", 3))
        link = ctx.params.get("linkage", "ward")
        return _cluster_run(
            self, ctx, lambda X: AgglomerativeClustering(n_clusters=k, linkage=link).fit_predict(X)
        )


@register
class SpectralClusteringModel(Component):
    spec = _spec(
        "model.clustering.spectral", "Spectral Clustering",
        "Clusters on a similarity graph — finds non-blob shapes (rings, moons) k-means misses.",
        {"n_clusters": {"type": "integer", "default": 3, "title": "Clusters (k)"}},
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.cluster import SpectralClustering

        k = int(ctx.params.get("n_clusters", 3))
        return _cluster_run(
            self, ctx,
            lambda X: SpectralClustering(
                n_clusters=k, assign_labels="kmeans", random_state=0
            ).fit_predict(X),
        )
