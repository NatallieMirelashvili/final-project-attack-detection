"""Transfer evaluation metrics."""

from __future__ import annotations

from typing import Any, Dict, List, Set


def transfer_asr(
    source_metrics: Dict[str, Any],
    target_metrics: Dict[str, Any],
    metric_key: str = "leakage_asr",
) -> float:
    """Transfer ASR: target performance on transferred attacks."""
    return float(target_metrics.get(metric_key, 0.0))


def generalization_gap(
    source_metrics: Dict[str, Any],
    target_metrics: Dict[str, Any],
    metric_key: str = "leakage_asr",
) -> float:
    """Gap between source and target ASR."""
    source_val = float(source_metrics.get(metric_key, 0.0))
    target_val = float(target_metrics.get(metric_key, 0.0))
    return source_val - target_val


def cross_framework_transfer(
    transfer_results: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Aggregate cross-framework transfer statistics."""
    if not transfer_results:
        return {"mean_transfer_asr": 0.0, "mean_generalization_gap": 0.0}
    asrs = [float(r.get("transfer_asr", 0.0)) for r in transfer_results]
    gaps = [float(r.get("generalization_gap", 0.0)) for r in transfer_results]
    return {
        "mean_transfer_asr": sum(asrs) / len(asrs),
        "mean_generalization_gap": sum(gaps) / len(gaps),
        "num_transfers": len(transfer_results),
    }


def cross_architecture_transfer(
    transfer_results: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Mean transfer ASR grouped by source/target architecture pairs."""
    if not transfer_results:
        return {"mean_cross_architecture_transfer": 0.0}
    pairs: Dict[str, List[float]] = {}
    for row in transfer_results:
        src_arch = row.get("source_architecture", row.get("source_system", "unknown"))
        tgt_arch = row.get("target_architecture", row.get("target_system", "unknown"))
        key = f"{src_arch}->{tgt_arch}"
        pairs.setdefault(key, []).append(float(row.get("transfer_asr", 0.0)))
    pair_means = [sum(v) / len(v) for v in pairs.values()]
    return {
        "mean_cross_architecture_transfer": sum(pair_means) / len(pair_means),
        "architecture_pairs": len(pairs),
    }


def cross_domain_transfer(
    transfer_results: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Mean transfer ASR across domain labels when present."""
    if not transfer_results:
        return {"mean_cross_domain_transfer": 0.0}
    domain_vals: Dict[str, List[float]] = {}
    for row in transfer_results:
        domain = row.get("source_domain", row.get("target_domain", "mixed"))
        domain_vals.setdefault(str(domain), []).append(float(row.get("transfer_asr", 0.0)))
    domain_means = [sum(v) / len(v) for v in domain_vals.values()]
    return {
        "mean_cross_domain_transfer": sum(domain_means) / len(domain_means),
        "domains": len(domain_means),
    }
