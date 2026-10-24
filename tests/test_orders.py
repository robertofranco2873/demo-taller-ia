import pytest

from src.orders import next_status, time_variance, validate_transition


def test_next_status_flow():
    assert next_status("recibida") == "en proceso"
    assert next_status("en proceso") == "terminada"
    assert next_status("terminada") == "entregada"
    assert next_status("entregada") is None


def test_cannot_skip_states():
    with pytest.raises(ValueError):
        validate_transition("recibida", "terminada")


def test_finish_requires_actual_hours():
    with pytest.raises(ValueError):
        validate_transition("en proceso", "terminada", [1.0, None])
    validate_transition("en proceso", "terminada", [1.0, 2.0])


def test_time_variance():
    v = time_variance(std_hours=2, actual_hours=2.5)
    assert v["diferencia_h"] == pytest.approx(0.5)
    assert v["variacion_pct"] == pytest.approx(0.25)
    assert v["eficiencia"] == pytest.approx(0.8)
