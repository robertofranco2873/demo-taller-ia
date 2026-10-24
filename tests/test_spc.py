import pytest

from src.spc import control_chart, control_limits, run_rule


def test_control_limits():
    lim = control_limits([2, 4, 4, 4, 5, 5, 7, 9])
    assert lim["lc"] == pytest.approx(5.0)
    assert lim["sigma"] == pytest.approx(2.13809, rel=1e-4)
    assert lim["lsc"] == pytest.approx(5 + 3 * 2.13809, rel=1e-4)
    assert lim["lic"] == 0.0  # se trunca en cero: no hay tiempos negativos


def test_requires_two_points():
    with pytest.raises(ValueError):
        control_limits([1.0])


def test_out_of_limits_detected():
    values = [1.0, 1.1, 0.9, 1.0, 1.05, 0.95, 1.0, 1.1, 0.9, 1.0] * 2 + [3.0]
    df, lim = control_chart(values)
    assert df["fuera_de_limites"].tolist()[-1] is True or bool(df["fuera_de_limites"].iloc[-1])
    assert df["fuera_de_limites"].sum() == 1


def test_run_rule():
    flags = run_rule([1, 2, 6, 6, 6, 6, 6, 6, 6, 1], center=5, length=7)
    assert flags == [False, False] + [True] * 7 + [False]
