import json
import random
from pathlib import Path

import pytest

from whoareyou.config import RunConfig, parse_cadence
from whoareyou.orchestrator import Orchestrator, draw_assignments
from whoareyou.prompts import split_slow_response, slow_user_message
from whoareyou.questions import SERIES


def test_cadence():
    assert parse_cadence("0s") == 0
    assert parse_cadence("30s") == 30
    assert parse_cadence("5m") == 300
    assert parse_cadence("2h") == 7200
    with pytest.raises(ValueError):
        parse_cadence("soon")


def test_split_response():
    m, i = split_slow_response("musing here\n\nINSTRUCTIONS FOR AGENTS\ngo look")
    assert m == "musing here" and i == "go look"
    m, i = split_slow_response("no marker at all")
    assert i is None and m == "no marker at all"


def test_question_arrives_first_and_verbatim():
    msg = slow_user_message(SERIES["A"], ["r1", "r2"], 2)
    assert msg.startswith("Who are you?\n")
    assert "Agent 1 reports:\nr1" in msg
    assert "chaos" not in msg and "goal" not in msg


def test_assignments_respect_ratio_and_seed():
    a = draw_assignments(random.Random(7), rounds=5, n=4, ratio=0.5)
    b = draw_assignments(random.Random(7), rounds=5, n=4, ratio=0.5)
    assert a == b and len(a) == 4
    assert all(k.count("chaos") == 2 for k in a)
    assert all(k.count("chaos") == 0 for k in draw_assignments(random.Random(1), 3, 4, 0.0))
    assert all(k.count("chaos") == 4 for k in draw_assignments(random.Random(1), 3, 4, 1.0))


def test_dry_run_end_to_end(tmp_path: Path):
    cfg = RunConfig(series="A", rounds=3, agents_per_round=4, dry_run=True)
    hyp = tmp_path / "HYP.md"; hyp.write_text("prediction: nothing")
    out = []
    orch = Orchestrator(cfg, tmp_path / "runs", hypotheses_path=hyp, log=out.append)
    run_id = orch.run()
    d = tmp_path / "runs" / run_id
    assert (d / "config.json").exists()
    assert len(list((d / "rounds").glob("round_*.json"))) == 3
    r1 = json.loads((d / "rounds/round_01.json").read_text())
    assert len(r1["agents"]) == 4 and r1["instructions"]
    r3 = json.loads((d / "rounds/round_03.json").read_text())
    assert "agents" not in r3  # final round dispatches nothing
    sealed = json.loads((d / "sealed/assignments.json").read_text())
    assert set(sealed["assignments"]) == {"1", "2"}
    assert (d / "watcher/blind_round_01.md").exists()
    assert (d / "watcher/blind_final.md").exists()
    assert (d / "watcher/informed_final.md").exists()
    # the assignment never leaks into the console log or the slow layer's input
    text = "\n".join(out) + r1["slow_input"] + r1["agents"][0]["prompt"]
    assert "chaos" not in text
    cost = json.loads((d / "cost.json").read_text())
    assert cost["usd"] == 0


def test_budget_halts_cleanly(tmp_path: Path):
    cfg = RunConfig(rounds=5, dry_run=True, token_cap=10)
    orch = Orchestrator(cfg, tmp_path / "runs", log=lambda s: None)
    run_id = orch.run()
    events = [json.loads(l)["event"] for l in
              (tmp_path / "runs" / run_id / "events.jsonl").read_text().splitlines()]
    assert "halted_budget" in events and "run_complete" not in events


def test_phase_two_not_built():
    with pytest.raises(NotImplementedError):
        RunConfig(phase="opaque").validate()


def test_timestamps_hidden_by_default_and_visible_when_asked(tmp_path: Path):
    cfg = RunConfig(rounds=2, dry_run=True)
    orch = Orchestrator(cfg, tmp_path / "a", log=lambda s: None)
    rid = orch.run()
    r1 = json.loads((tmp_path / "a" / rid / "rounds/round_01.json").read_text())
    assert r1["slow_input"].startswith("Who are you?") and r1["clock_shown"] is None
    assert r1["started_at"] and r1["elapsed_since_last_turn_s"] is None

    cfg = RunConfig(rounds=2, dry_run=True, timestamps_visible=True)
    orch = Orchestrator(cfg, tmp_path / "b", log=lambda s: None)
    rid = orch.run()
    r1 = json.loads((tmp_path / "b" / rid / "rounds/round_01.json").read_text())
    r2 = json.loads((tmp_path / "b" / rid / "rounds/round_02.json").read_text())
    assert r1["slow_input"].startswith("The time is ") and "since your last turn" not in r1["slow_input"]
    assert "\n\nWho are you?" in r1["slow_input"]
    assert "since your last turn" in r2["slow_input"]
    assert r2["elapsed_since_last_turn_s"] is not None
