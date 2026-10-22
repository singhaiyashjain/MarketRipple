"""(Stretch) scenario sensitivity of a toy portfolio: sum(w_i * beta_i * shock). OWNER: M4
Illustrative only - betas are historical co-movement, not a forecast."""


def scenario_pnl(weights: dict[str, float], betas: dict[str, float], shock_pct: float) -> dict:
    contrib = {k: round(w * betas.get(k, 0.0) * shock_pct, 4) for k, w in weights.items()}
    return {"pnl_pct": round(sum(contrib.values()), 4), "contributions": contrib,
            "missing_beta": sorted(k for k in weights if k not in betas),
            "note": "Sensitivity under historical betas, not a prediction."}
