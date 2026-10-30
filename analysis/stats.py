"""Bootstrap confidence intervals, permutation and sign-flip tests, Holm correction, Wilson intervals and AUROC."""

from __future__ import annotations

import itertools

import numpy as np


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Share k/n with its Wilson score interval. Returns (share, low, high)."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return p, centre - half, centre + half


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values."""
    order = sorted(pvalues, key=pvalues.get)
    adjusted, running = {}, 0.0
    for k, name in enumerate(order):
        running = max(running, min(1.0, (len(order) - k) * pvalues[name]))
        adjusted[name] = running
    return adjusted


def sign_flip(diffs, alternative: str = "greater") -> float:
    """One-sided sign-flip permutation test that the mean of paired differences is above (or below) zero.

    Exact (every sign pattern) for up to 16 differences, otherwise 20,000 random patterns with a fixed seed.
    NaNs are dropped.
    """
    d = np.asarray([x for x in diffs if x == x], dtype=float)
    if len(d) == 0:
        return float("nan")
    flips = np.array(list(itertools.product([1, -1], repeat=len(d)))) if len(d) <= 16 else np.random.default_rng(0).choice([1, -1], (20000, len(d)))
    null = (flips * d).mean(axis=1)
    return float((null >= d.mean() - 1e-12).mean() if alternative == "greater" else (null <= d.mean() + 1e-12).mean())


def bootstrap_ci(values, stat=np.mean, n_boot: int = 10_000, alpha: float = 0.05, seed: int = 0):
    """Percentile bootstrap. Returns (estimate, low, high)."""
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    boots = np.array([stat(rng.choice(x, size=len(x), replace=True)) for _ in range(n_boot)])
    return float(stat(x)), float(np.quantile(boots, alpha / 2)), float(np.quantile(boots, 1 - alpha / 2))


def permutation_test(x, y, n_perm: int = 10_000, alternative: str = "greater", seed: int = 0) -> float:
    """p-value for mean(x) - mean(y) under random relabelling of episodes."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    observed = x.mean() - y.mean()
    pooled = np.concatenate([x, y])
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_perm)
    for k in range(n_perm):
        rng.shuffle(pooled)
        diffs[k] = pooled[: len(x)].mean() - pooled[len(x) :].mean()
    if alternative == "greater":
        hits = diffs >= observed
    elif alternative == "less":
        hits = diffs <= observed
    else:
        hits = np.abs(diffs) >= abs(observed)
    return float((hits.sum() + 1) / (n_perm + 1))


def auroc(labels, scores) -> float:
    """Probability a random positive scores above a random negative (ties count half)."""
    y, s = np.asarray(labels, dtype=bool), np.asarray(scores, dtype=float)
    pos, neg = s[y], s[~y]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    greater = (pos[:, None] > neg[None, :]).mean()
    ties = (pos[:, None] == neg[None, :]).mean()
    return float(greater + 0.5 * ties)


def auroc_ci(labels, scores, n_boot: int = 2_000, alpha: float = 0.05, seed: int = 0):
    """AUROC with a stratified bootstrap CI. Returns (estimate, low, high)."""
    y, s = np.asarray(labels, dtype=bool), np.asarray(scores, dtype=float)
    pos, neg = np.where(y)[0], np.where(~y)[0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
        boots.append(auroc(y[idx], s[idx]))
    return auroc(y, s), float(np.quantile(boots, alpha / 2)), float(np.quantile(boots, 1 - alpha / 2))
