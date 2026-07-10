"""Clustering family — real per-algorithm mechanics on the actual data.

The 2-D map (two highest-variance features) and the k-means Lloyd's loop are the shared base;
on top of that, the chosen algorithm is fitted for real and its OWN mechanism is recorded so
the lesson animates the student's real points, not a canned picture:
  * dbscan       -> per-point core/border/noise + the density growth (visit) order
  * gmm          -> per-point responsibilities (soft memberships) + per-component ellipses
  * hierarchical -> the real merge sequence (pairs + heights) for a dendrogram
  * spectral     -> each point's original position AND its position in the spectral embedding

No "correct answer" exists — clustering discovers structure instead of predicting a label.
"""

from __future__ import annotations

from . import register_tracer
from .common import resolve_params, split_holdout, table_rows
from .schema import ModelTrace

MAX_POINTS = 140
MECH_POINTS = 60  # points shown in the per-algorithm mechanism visuals (kept legible)
DENDRO_LEAVES = 12

SPEC = [
    {"key": "k", "label": "Clusters (k)", "type": "int", "default": 3, "min": 2, "max": 8,
     "step": 1, "help": "How many groups to split the data into (k-means / GMM / hierarchical / spectral)."},
    {"key": "eps", "label": "DBSCAN radius (ε)", "type": "float", "default": 0.0, "min": 0.0,
     "max": 4.0, "step": 0.1, "help": "Neighbourhood radius for DBSCAN (0 = auto from the data)."},
    {"key": "min_samples", "label": "DBSCAN min neighbours", "type": "int", "default": 4, "min": 2,
     "max": 12, "step": 1, "help": "Neighbours (incl. self) a point needs to be a DBSCAN core point."},
]


def _axes(X, feats):
    variances = [(f, float(X[f].std())) for f in feats]
    variances.sort(key=lambda t: -t[1])
    fx, fy = (variances[0][0], variances[1][0]) if len(variances) > 1 else (feats[0], feats[0])
    show = [f for f, _ in variances[:6]]
    return fx, fy, show, feats.index(fx), feats.index(fy)


def _lloyd(Xs, k, scaler, ix, iy):
    """K-means by hand for a few iterations — the shared 'canonical loop' contrast chapter."""
    import numpy as np

    def _unscale(c):
        raw = scaler.inverse_transform(c.reshape(1, -1))[0]
        return {"x": round(float(raw[ix]), 3), "y": round(float(raw[iy]), 3)}

    rng = np.random.default_rng(7)
    centers = Xs[rng.choice(len(Xs), size=k, replace=False)]
    step = max(1, len(Xs) // MAX_POINTS)
    idxs = list(range(0, len(Xs), step))
    iterations = []
    for _ in range(6):
        d = np.linalg.norm(Xs[:, None, :] - centers[None, :, :], axis=2)
        assign = d.argmin(axis=1)
        iterations.append({
            "centers": [_unscale(c) for c in centers],
            "assign": [f"cluster {int(assign[i]) + 1}" for i in idxs],
            "inertia": round(float((d.min(axis=1) ** 2).sum()), 1),
        })
        new_centers = np.array([
            Xs[assign == c].mean(axis=0) if (assign == c).any() else centers[c] for c in range(k)
        ])
        if np.allclose(new_centers, centers, atol=1e-4):
            break
        centers = new_centers
    return iterations


def _dbscan_mechanism(Xs, Xtr, fx, fy, eps, min_samples):
    """Real DBSCAN: core/border/noise per point + the chain-reaction visit order."""
    import numpy as np
    from sklearn.cluster import DBSCAN
    from sklearn.neighbors import NearestNeighbors

    n = len(Xs)
    ms = min(min_samples, max(2, n - 1))
    if eps <= 0:  # auto ε: the knee of the sorted k-distance graph (median of the ms-th nn distance)
        nn = NearestNeighbors(n_neighbors=ms).fit(Xs)
        kd = np.sort(nn.kneighbors(Xs)[0][:, -1])
        eps = float(np.quantile(kd, 0.6)) or 0.5
    db = DBSCAN(eps=eps, min_samples=ms).fit(Xs)
    labels = db.labels_
    core = set(db.core_sample_indices_.tolist())

    idxs = list(range(0, n, max(1, n // MECH_POINTS)))
    role = {}
    for i in range(n):
        if labels[i] == -1:
            role[i] = "noise"
        elif i in core:
            role[i] = "core"
        else:
            role[i] = "border"
    # visit order: BFS from each core point in index order (the growth animation)
    order, seen = [], set()
    for c in db.core_sample_indices_:
        if c in seen:
            continue
        queue = [int(c)]
        while queue:
            p = queue.pop(0)
            if p in seen:
                continue
            seen.add(p)
            order.append(p)
    order_rank = {p: r for r, p in enumerate(order)}
    points = [{
        "x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
        "cluster": int(labels[i]), "role": role[i],
        "step": order_rank.get(i, len(order)),
    } for i in idxs]
    n_clusters = len({c for c in labels if c != -1})
    return {
        "kind": "dbscan", "eps": round(float(eps), 3), "min_samples": ms,
        "points": points, "n_clusters": n_clusters,
        "n_noise": int((labels == -1).sum()), "total_steps": len(order),
    }, labels


def _gmm_mechanism(Xs, Xtr, fx, fy, ix, iy, scaler, k):
    """Real GMM: per-point top responsibilities + per-component ellipse in the map axes."""
    import numpy as np
    from sklearn.mixture import GaussianMixture

    gm = GaussianMixture(n_components=k, covariance_type="full", random_state=0).fit(Xs)
    resp = gm.predict_proba(Xs)
    labels = resp.argmax(axis=1)
    idxs = list(range(0, len(Xs), max(1, len(Xs) // MECH_POINTS)))

    ellipses = []
    for c in range(k):
        mean_raw = scaler.inverse_transform(gm.means_[c].reshape(1, -1))[0]
        cov = gm.covariances_[c][np.ix_([ix, iy], [ix, iy])]
        # scale std back to raw units on each axis
        sx, sy = scaler.scale_[ix], scaler.scale_[iy]
        cov_raw = cov * np.array([[sx * sx, sx * sy], [sx * sy, sy * sy]])
        vals, vecs = np.linalg.eigh(cov_raw)
        vals = np.clip(vals, 1e-9, None)
        angle = float(np.degrees(np.arctan2(vecs[1, np.argmax(vals)], vecs[0, np.argmax(vals)])))
        ellipses.append({
            "cx": round(float(mean_raw[ix]), 3), "cy": round(float(mean_raw[iy]), 3),
            "rx": round(float(2 * np.sqrt(vals.max())), 3),
            "ry": round(float(2 * np.sqrt(vals.min())), 3),
            "angle": round(angle, 1),
        })
    points = [{
        "x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
        "cluster": int(labels[i]),
        "resp": [round(float(r), 2) for r in resp[i]],
    } for i in idxs]
    return {"kind": "gmm", "points": points, "ellipses": ellipses, "k": k}, labels


def _hierarchical_mechanism(Xs, Xtr, fx, fy, k, linkage):
    """Real agglomerative merges → a dendrogram on a legible sample of the rows."""
    from scipy.cluster.hierarchy import linkage as sp_linkage
    from sklearn.cluster import AgglomerativeClustering

    n = len(Xs)
    sample = list(range(0, n, max(1, n // DENDRO_LEAVES)))[:DENDRO_LEAVES]
    Xd = Xs[sample]
    method = linkage if linkage in ("single", "complete", "average", "ward") else "ward"
    Z = sp_linkage(Xd, method=method)
    m = len(sample)
    merges = [{
        "a": int(Z[i, 0]), "b": int(Z[i, 1]),
        "height": round(float(Z[i, 2]), 3), "size": int(Z[i, 3]),
        "node": m + i,
    } for i in range(len(Z))]

    full = AgglomerativeClustering(n_clusters=min(k, n), linkage=method).fit(Xs)
    idxs = list(range(0, n, max(1, n // MECH_POINTS)))
    points = [{
        "x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
        "cluster": int(full.labels_[i]),
    } for i in idxs]
    return {"kind": "hierarchical", "linkage": method, "n_leaves": m,
            "merges": merges, "points": points}, full.labels_


def _spectral_mechanism(Xs, Xtr, fx, fy, k):
    """Real spectral clustering: each point's original position AND its embedding position."""
    import numpy as np
    from sklearn.cluster import SpectralClustering
    from sklearn.manifold import SpectralEmbedding

    n = len(Xs)
    kk = min(k, n - 1)
    sc = SpectralClustering(n_clusters=kk, affinity="nearest_neighbors", random_state=0)
    labels = sc.fit_predict(Xs)
    emb = SpectralEmbedding(n_components=2, affinity="nearest_neighbors",
                            random_state=0).fit_transform(Xs)
    # normalise the embedding to a friendly range for the SVG
    emb = (emb - emb.min(0)) / (np.ptp(emb, axis=0) + 1e-9)
    idxs = list(range(0, n, max(1, n // MECH_POINTS)))
    points = [{
        "x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
        "ex": round(float(emb[i, 0]), 3), "ey": round(float(emb[i, 1]), 3),
        "cluster": int(labels[i]),
    } for i in idxs]
    return {"kind": "spectral", "points": points, "k": kk}, labels


@register_tracer("clustering")
def trace_clustering(X, y, feats, target, task, labels_ignored, params=None) -> ModelTrace:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    params = dict(params or {})
    model = str(params.pop("_model", "kmeans") or "kmeans")
    linkage = str(params.pop("linkage", "ward"))
    p, param_spec = resolve_params(SPEC, params)
    Xtr, Xte, _ytr, _yte = split_holdout(X, y)
    scaler = StandardScaler().fit(Xtr)
    Xs = scaler.transform(Xtr)
    k = min(p["k"], len(Xtr))
    fx, fy, show, ix, iy = _axes(X, feats)

    # the canonical loop (k-means) — always computed, the contrast chapter
    iterations = _lloyd(Xs, k, scaler, ix, iy)

    # the CHOSEN algorithm's real fit + mechanism → also colours the map
    mechanism = None
    map_labels = None
    try:
        if model == "dbscan":
            mechanism, map_labels = _dbscan_mechanism(Xs, Xtr, fx, fy, p["eps"], p["min_samples"])
        elif model == "gmm":
            mechanism, map_labels = _gmm_mechanism(Xs, Xtr, fx, fy, ix, iy, scaler, k)
        elif model == "hierarchical":
            mechanism, map_labels = _hierarchical_mechanism(Xs, Xtr, fx, fy, k, linkage)
        elif model == "spectral":
            mechanism, map_labels = _spectral_mechanism(Xs, Xtr, fx, fy, k)
    except Exception:  # any algo hiccup falls back to the k-means map, lesson still plays
        mechanism, map_labels = None, None

    km = KMeans(n_clusters=k, n_init=5, random_state=0).fit(Xs)
    if map_labels is None:
        map_labels = km.labels_

    step = max(1, len(Xtr) // MAX_POINTS)
    idxs = list(range(0, len(Xtr), step))
    points = [
        {"x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
         "label": f"cluster {int(map_labels[i]) + 1}" if map_labels[i] >= 0 else "noise"}
        for i in idxs
    ]

    test_rows = []
    for j in range(len(Xte)):
        srow = scaler.transform(Xte.iloc[[j]])
        dists = np.linalg.norm(km.cluster_centers_ - srow, axis=1)
        order = np.argsort(dists)
        test_rows.append({
            "values": {f: round(float(Xte.iloc[j][f]), 3) for f in show},
            "x": round(float(Xte.iloc[j][fx]), 3), "y": round(float(Xte.iloc[j][fy]), 3),
            "distances": [
                {"cluster": f"cluster {int(c) + 1}", "distance": round(float(dists[c]), 3)}
                for c in order
            ],
            "predicted": f"cluster {int(order[0]) + 1}", "actual": None,
            "correct": None, "error": None,
        })

    sizes = [int((km.labels_ == c).sum()) for c in range(km.n_clusters)]
    series = {"x": fx, "y": fy, "k": km.n_clusters, "sizes": sizes, "iterations": iterations}
    if mechanism:
        series["mechanism"] = mechanism
    return ModelTrace(
        family="clustering", target=target, task="clustering", features=show, labels=None,
        table=table_rows(X, y, show, target, task, None),
        points=points, series=series,
        test_rows=test_rows, params=p, param_spec=param_spec,
        note="Clustering has NO answer column — it looks for natural groups. The map shows the "
        "rows on their two most variable features; the mechanism chapter animates how THIS "
        "algorithm formed the groups on your real points.",
    )
