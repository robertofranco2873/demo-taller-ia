from datetime import date, datetime

import pytest

from src.workcalendar import (add_work_hours, add_workdays, available_hours, week_start,
                              work_hours_until, workdays_between)

MONDAY = date(2026, 10, 19)


def test_workdays_between_excludes_sunday():
    assert workdays_between(MONDAY, date(2026, 10, 25)) == 6  # lun-dom
    assert workdays_between(date(2026, 10, 25), date(2026, 10, 25)) == 0
    assert workdays_between(MONDAY, date(2026, 10, 18)) == 0


def test_available_hours():
    assert available_hours(MONDAY, date(2026, 10, 25), resources=3) == 6 * 8 * 3


def test_week_start():
    assert week_start(date(2026, 10, 23)) == MONDAY


def test_add_workdays_skips_sunday():
    assert add_workdays(date(2026, 10, 24), 1) == date(2026, 10, 26)


def test_add_work_hours_same_day():
    assert add_work_hours(datetime(2026, 10, 19, 10), 3) == datetime(2026, 10, 19, 13)


def test_add_work_hours_rolls_over_to_next_day():
    # 15:00 + 4 h → 2 h el lunes y 2 h el martes desde las 9:00
    assert add_work_hours(datetime(2026, 10, 19, 15), 4) == datetime(2026, 10, 20, 11)


def test_add_work_hours_skips_sunday():
    assert add_work_hours(datetime(2026, 10, 24, 16), 2) == datetime(2026, 10, 26, 10)


def test_work_hours_until():
    now = datetime(2026, 10, 19, 13)  # lunes, 4 h trabajadas
    assert work_hours_until(now, date(2026, 10, 19)) == pytest.approx(4)
    assert work_hours_until(now, date(2026, 10, 20)) == pytest.approx(12)
    assert work_hours_until(datetime(2026, 10, 20, 13), date(2026, 10, 19)) == pytest.approx(-4)
