"""Path time horizon = slowest edge horizon. OWNER: M3"""
ORDER = ["immediate", "short", "medium", "long"]


def path_horizon(edge_horizons: list[str]) -> str:
    return max(edge_horizons, key=ORDER.index) if edge_horizons else "short"
