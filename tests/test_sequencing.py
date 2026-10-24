import pytest

from src.sequencing import Job, compare_rules, metrics, schedule, sequence

# Ejemplo clásico de libro: 5 trabajos en una sola máquina.
JOBS = [
    Job("A", processing=6, due=8, arrival=1),
    Job("B", processing=2, due=6, arrival=2),
    Job("C", processing=8, due=18, arrival=3),
    Job("D", processing=3, due=15, arrival=4),
    Job("E", processing=9, due=23, arrival=5),
]


def ids(jobs):
    return [j.id for j in jobs]


def test_sequence_rules():
    assert ids(sequence(JOBS, "FIFO")) == ["A", "B", "C", "D", "E"]
    assert ids(sequence(JOBS, "SPT")) == ["B", "D", "A", "C", "E"]
    assert ids(sequence(JOBS, "EDD")) == ["B", "A", "D", "C", "E"]


def test_fifo_metrics():
    # C: 6, 8, 16, 19, 28 → flujo 77/5 = 15.4; retrasos 0,2,0,4,5 → 11/5 = 2.2; 3 tarde
    m = metrics(schedule(JOBS, "FIFO"))
    assert m["flujo_promedio_h"] == pytest.approx(15.4)
    assert m["retraso_promedio_h"] == pytest.approx(2.2)
    assert m["ordenes_tarde"] == 3
    assert m["makespan_h"] == 28


def test_spt_minimizes_flow_time():
    table = compare_rules(JOBS).set_index("regla")
    assert table.loc["SPT", "flujo_promedio_h"] == pytest.approx(13.0)
    assert table["flujo_promedio_h"].idxmin() == "SPT"


def test_edd_metrics():
    # B2, A8, D11, C19, E28 → retrasos 0,0,0,1,5
    m = metrics(schedule(JOBS, "EDD"))
    assert m["retraso_promedio_h"] == pytest.approx(1.2)
    assert m["ordenes_tarde"] == 2


def test_parallel_machines():
    df = schedule(JOBS, "SPT", machines=2, machine_names=["T1", "T2"])
    # B→T1(0-2), D→T2(0-3), A→T1(2-8), C→T2(3-11), E→T1(8-17)
    assert df["recurso"].tolist() == ["T1", "T2", "T1", "T2", "T1"]
    assert df["fin_h"].tolist() == [2, 3, 8, 11, 17]


def test_invalid_rule_and_machines():
    with pytest.raises(ValueError):
        sequence(JOBS, "LPT")
    with pytest.raises(ValueError):
        schedule(JOBS, "SPT", machines=0)


def test_empty_metrics():
    assert metrics(schedule([], "FIFO"))["ordenes_tarde"] == 0
