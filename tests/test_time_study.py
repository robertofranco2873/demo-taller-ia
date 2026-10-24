import pytest

from src.time_study import normal_time, observed_average, standard_hours, standard_time


def test_observed_average():
    assert observed_average([10, 12, 14]) == pytest.approx(12)


def test_observed_average_rejects_empty_and_negative():
    with pytest.raises(ValueError):
        observed_average([])
    with pytest.raises(ValueError):
        observed_average([5, -1])


def test_normal_time():
    # TN = 40 min × 1.10 = 44 min
    assert normal_time(40, 1.10) == pytest.approx(44)


def test_standard_time():
    # TS = 44 × (1 + 0.15) = 50.6 min
    assert standard_time(44, 0.15) == pytest.approx(50.6)


def test_standard_hours_chain():
    assert standard_hours(60, 1.0, 0.20) == pytest.approx(1.2)


@pytest.mark.parametrize("obs, rf", [(0, 1), (10, 0), (-5, 1)])
def test_normal_time_invalid(obs, rf):
    with pytest.raises(ValueError):
        normal_time(obs, rf)


def test_standard_time_negative_allowance():
    with pytest.raises(ValueError):
        standard_time(10, -0.1)
