from app import rotrisk


def L(t=25, rh=60):
    return {"t": t, "rh": rh}


def test_fresh_heap_is_safe():
    r = rotrisk.compute({"top": L(), "mid": L(), "bot": L(), "amb": L(25, 60)},
                        {"mq135_mv": 400, "mq135_base_mv": 400})
    assert r.level == "SAFE" and r.score < 35


def test_high_gas_and_humidity_is_rot():
    r = rotrisk.compute({"top": L(27, 88), "mid": L(26, 85), "bot": L(25, 84), "amb": L(25, 60)},
                        {"mq135_mv": 720, "mq135_base_mv": 400})
    assert r.level == "ROT"
    assert r.worst_layer == "top"
    assert any("rot gas" in x for x in r.reasons)


def test_humidity_only_is_watch():
    r = rotrisk.compute({"top": L(25, 86), "mid": L(25, 70), "bot": L(25, 70), "amb": L(25, 60)}, {})
    assert r.level in ("WATCH", "ROT")
    assert "gas" not in r.components          # gas missing -> weights renormalise


def test_hotspot_detected_in_bottom_layer():
    r = rotrisk.compute({"top": L(25, 70), "mid": L(25, 70), "bot": L(29.5, 72), "amb": L(25, 60)}, {})
    assert r.components["heat"] == 100.0
    assert r.worst_layer == "bot"


def test_no_data_is_unknown():
    r = rotrisk.compute({"top": {}, "mid": {}, "bot": {}, "amb": {}}, {})
    assert r.level == "UNKNOWN"


def test_bad_baseline_ignored():
    r = rotrisk.compute({"top": L()}, {"mq135_mv": 500, "mq135_base_mv": 0})
    assert "gas" not in r.components


def test_levels():
    assert rotrisk.level_for(10) == "SAFE"
    assert rotrisk.level_for(35) == "WATCH"
    assert rotrisk.level_for(65) == "ROT"


def test_inputs_trace_the_formula_values():
    r = rotrisk.compute({"top": L(27, 88), "mid": L(26, 85), "bot": L(25, 84), "amb": L(25, 60)},
                        {"mq135_mv": 520, "mq135_base_mv": 400, "mq136_mv": 600, "mq136_base_mv": 400})
    assert r.inputs["gas"]["sensor"] == "mq136" and r.inputs["gas"]["rise_pct"] == 50.0
    assert r.inputs["humid"] == {"layer": "top", "rh": 88, "rh_low": 70.0, "rh_high": 90.0}
    assert r.inputs["heat"]["hot_layer"] == "top" and r.inputs["heat"]["hotspot_c"] == 2.0


def test_heat_falls_back_to_coolest_layer_without_ambient():
    r = rotrisk.compute({"top": L(28, 70), "mid": L(25, 70), "bot": L(25, 70)}, {})
    assert r.inputs["heat"]["ref"] == "coolest layer" and r.inputs["heat"]["t_ref"] == 25
