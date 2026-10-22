from app.impact.scoring import path_strength, terminal_effect


def test_strength_product():
    assert path_strength([0.9, 0.8, 0.7]) == 0.504


def test_terminal_effect():
    assert terminal_effect([1, 1, -1]) == "negative"
    assert terminal_effect([1, -1, -1]) == "positive"
    assert terminal_effect([1, 0]) == "mixed"
