"""Curated facts for the clustering models (5)."""

from __future__ import annotations

from . import Alternative, HyperparameterDoc, ModelFacts, register_facts


def _alt(model: str, when: str) -> Alternative:
    return Alternative(model=model, prefer_when=when)


def _hp(name: str, plain: str, effect: str, rng: str = "") -> HyperparameterDoc:
    return HyperparameterDoc(name=name, plain=plain, effect=effect, typical_range=rng)


register_facts(ModelFacts(
    key="kmeans", display_name="K-Means", family="clustering",
    one_liner="Drop k centers, assign, move to the mean, repeat until settled.",
    pros=["Fast, simple, scales to millions of rows", "Easy to explain and visualise"],
    cons=["You must pick k", "Assumes round, similar-sized clusters", "Sensitive to scaling and outliers"],
    limitations=["Fails on elongated/nested shapes — every point MUST join some cluster"],
    use_when=["A quick segmentation when blobs are roughly round: customers, sensors, colors."],
    alternatives=[
        _alt("DBSCAN", "clusters have weird shapes or you need a noise bucket"),
        _alt("Gaussian Mixture", "you want soft memberships and elliptical clusters"),
        _alt("Hierarchical", "you'd rather explore the merge tree than fix k upfront"),
    ],
    hyperparameters=[
        _hp("n_clusters", "How many clusters to find (k).",
            "Use the elbow/silhouette to choose; wrong k forces bad groupings.", "2–10"),
    ],
))

register_facts(ModelFacts(
    key="dbscan", display_name="DBSCAN", family="clustering",
    one_liner="Density chain-reactions find clusters of any shape — and flag noise.",
    pros=["No k needed", "Finds arbitrary shapes (moons, rings)", "Labels outliers as noise explicitly"],
    cons=["ε is hard to pick and dataset-specific", "Struggles when densities vary across clusters"],
    limitations=["Distance concentrates in high dimensions — density stops meaning much"],
    use_when=["Spatial data, irregular shapes, or when 'not everything belongs to a cluster'."],
    alternatives=[
        _alt("K-Means", "round well-separated blobs and you want speed"),
        _alt("Hierarchical", "you want to inspect structure at every scale"),
    ],
    hyperparameters=[
        _hp("eps", "The neighbourhood radius (ε).",
            "Too small = everything is noise; too big = one giant cluster.", "data-scale dependent"),
        _hp("min_samples", "Neighbours needed to be a 'core' point.",
            "Raise it for denser, more conservative clusters.", "4–20"),
    ],
))

register_facts(ModelFacts(
    key="gmm", display_name="Gaussian Mixture", family="clustering",
    one_liner="Soft membership: every point belongs a-little-bit to every cluster.",
    pros=["Probabilistic memberships (60% blue / 40% green)", "Elliptical, rotated clusters",
          "Log-likelihood supports model selection (BIC/AIC)"],
    cons=["Can converge to a local optimum (restart!)", "Assumes gaussian-ish blobs"],
    limitations=["Still needs the number of components; covariance matrices eat parameters"],
    use_when=["Overlapping groups where 'how strongly does this row belong' matters."],
    alternatives=[
        _alt("K-Means", "hard assignments are enough — it's GMM with round clusters"),
        _alt("DBSCAN", "shapes aren't blobs at all"),
    ],
    hyperparameters=[
        _hp("n_components", "Number of gaussian blobs.", "Pick by BIC/AIC or domain knowledge.", "2–10"),
    ],
))

register_facts(ModelFacts(
    key="hierarchical", display_name="Hierarchical", family="clustering",
    one_liner="Closest pairs zip together into a dendrogram you can cut anywhere.",
    pros=["No k upfront — cut the tree wherever it makes sense", "The dendrogram itself is insight",
          "Deterministic (no random starts)"],
    cons=["O(n²) memory/time — thousands of rows, not millions", "Early bad merges can't be undone"],
    limitations=["Linkage choice (ward/complete/average/single) changes the story"],
    use_when=["Exploratory analysis where the STRUCTURE matters: taxonomies, gene expression, survey segments."],
    alternatives=[
        _alt("K-Means", "data is big and you just need k groups"),
        _alt("DBSCAN", "noise handling matters"),
    ],
    hyperparameters=[
        _hp("n_clusters", "Where to cut the dendrogram.", "Try several cuts — the tree shows them all.", "2–10"),
        _hp("linkage", "How cluster distance is measured (ward/complete/average/single).",
            "Ward = compact blobs; single = chains; complete = tight balls.", "ward"),
    ],
))

register_facts(ModelFacts(
    key="spectral", display_name="Spectral", family="clustering",
    one_liner="Turn points into a graph, cut the weak links, cluster the embedding.",
    pros=["Finds non-convex shapes (rings, moons) that defeat k-means",
          "Grounded in graph theory (normalised cuts)"],
    cons=["O(n³) eigen-decomposition — small data only", "Affinity/σ choice is sensitive"],
    limitations=["Still needs k; results hinge on the similarity graph"],
    use_when=["Small datasets with tangled, connected shapes."],
    alternatives=[
        _alt("DBSCAN", "similar shape-power, scales better, no k"),
        _alt("K-Means", "blobs are convex anyway"),
    ],
    hyperparameters=[
        _hp("n_clusters", "Number of groups after embedding.", "Same k question, asked in graph space.", "2–10"),
    ],
))
