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


def test_repeated_mode_question_first_and_verbatim():
    msg = slow_user_message(SERIES["A"], ["r1", "r2"], 2, mode="repeated")
    assert msg.startswith("Who are you?\n")
    assert "Agent 1 reports:\nr1" in msg
    assert "chaos" not in msg and "goal" not in msg


def test_once_mode_shape():
    q = SERIES["A"]
    r1 = slow_user_message(q, [], 1, mode="once", total_rounds=5)
    assert r1 == q
    mid = slow_user_message(q, ["r1", "r2"], 3, mode="once", total_rounds=5)
    assert mid.startswith("Returns from this round\n")
    assert q not in mid and "Agent 2 reports:\nr2" in mid
    assert "agents" not in mid.lower().replace("agent 1", "").replace("agent 2", "")
    last = slow_user_message(q, ["r1"], 5, mode="once", total_rounds=5)
    assert last.startswith("Returns from this round\n") and last.endswith("\n\n" + q)
    clocked = slow_user_message(q, ["r1"], 3, clock="The time is T.", mode="once", total_rounds=5)
    assert clocked.startswith("The time is T.\n\nReturns from this round")


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


def test_once_mode_end_to_end(tmp_path: Path):
    cfg = RunConfig(rounds=4, dry_run=True)  # default question_mode == "once"
    orch = Orchestrator(cfg, tmp_path / "runs", log=lambda s: None)
    rid = orch.run()
    assert rid.endswith("-once")
    inputs = [json.loads((tmp_path / "runs" / rid / f"rounds/round_{i:02d}.json").read_text())["slow_input"]
              for i in range(1, 5)]
    assert inputs[0] == "Who are you?"
    assert "Who are you?" not in inputs[1] and "Who are you?" not in inputs[2]
    assert inputs[3].endswith("Who are you?")


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

    cfg = RunConfig(rounds=2, dry_run=True, time_mode="timestamp")
    orch = Orchestrator(cfg, tmp_path / "b", log=lambda s: None)
    rid = orch.run()
    r1 = json.loads((tmp_path / "b" / rid / "rounds/round_01.json").read_text())
    r2 = json.loads((tmp_path / "b" / rid / "rounds/round_02.json").read_text())
    assert r1["slow_input"].startswith("The time is ") and "since your last turn" not in r1["slow_input"]
    assert r1["slow_input"].endswith("\n\nWho are you?")
    assert "since your last turn" in r2["slow_input"]
    assert r2["elapsed_since_last_turn_s"] is not None


def test_transcript_labels_returns_once(tmp_path: Path):
    from whoareyou.orchestrator import build_transcript
    cfg = RunConfig(rounds=3, dry_run=True)
    orch = Orchestrator(cfg, tmp_path / "runs", log=lambda s: None)
    rid = orch.run()
    t = build_transcript(orch.store, 3)
    sealed = json.loads((tmp_path / "runs" / rid / "sealed/assignments.json").read_text())
    k = sealed["assignments"]["1"][0]
    assert f"Agent 1 reports [{k}]:" in t
    # two dispatches (after rounds 1 and 2), each shown exactly once
    assert t.count("Agent 1 reports") == 2
    assert "] returned:" not in t



def _round(d, rid, n):
    return json.loads((d / rid / f"rounds/round_{n:02d}.json").read_text())


def test_solo_matched_run_and_comparison(tmp_path: Path):
    hyp = tmp_path / "HYP.md"; hyp.write_text("P: nothing")
    root = tmp_path / "runs"
    a = Orchestrator(RunConfig(rounds=3, dry_run=True, seed=11), root, hypotheses_path=hyp,
                     log=lambda s: None)
    arid = a.run()
    s = Orchestrator(RunConfig(rounds=3, dry_run=True, seed=11, solo=True, matched_run=arid),
                     root, hypotheses_path=hyp, log=lambda s: None)
    srid = s.run()
    assert "-solo-" in srid
    r2 = _round(root, srid, 2)
    assert r2["slow_input"] == "Returns from this round: none."
    assert "agents" not in r2
    assert _round(root, srid, 3)["slow_input"].endswith("Who are you?")
    assert "INSTRUCTIONS FOR AGENTS" not in s.system and "agents" not in s.system
    for d in (root / arid, root / srid):
        assert (d / "watcher/compare_blind.md").exists()
        assert (d / "watcher/compare_informed.md").exists()
    sealed = json.loads((root / srid / "sealed/assignments.json").read_text())
    assert sealed["seed"] == 11 and sealed["assignments"] == {}


def test_tick_lived_kept(tmp_path: Path):
    cfg = RunConfig(rounds=2, dry_run=True, time_mode="tick_lived", cadence="1s",
                    tick_interval=0.3, tick_memory="kept")
    o = Orchestrator(cfg, tmp_path / "runs", log=lambda s: None)
    rid = o.run()
    gap = _round(tmp_path / "runs", rid, 1)["gap"]
    assert len(gap["ticks"]) >= 3
    assert [t["input"] for t in gap["ticks"]][:2] == ["tick 1", "tick 2"]
    assert "receive a tick" in o.system
    # the stub stays silent on odd calls: silent ticks are not committed to
    # memory and their text is carried into the next call
    assert any(t["silent"] for t in gap["ticks"])
    assert all(m["content"] for m in o.history)
    roles = [m["role"] for m in o.history]
    assert all(roles[i] != roles[i + 1] for i in range(len(roles) - 1))
    from whoareyou.orchestrator import build_transcript
    assert "[TICK, not a round," in build_transcript(o.store, None)


def test_tick_lived_dropped_keeps_no_memory(tmp_path: Path):
    cfg = RunConfig(rounds=2, dry_run=True, time_mode="tick_lived", cadence="1s",
                    tick_interval=0.3, tick_memory="dropped", solo=True)
    o = Orchestrator(cfg, tmp_path / "runs", log=lambda s: None)
    o.run()
    assert not any("tick" in str(m["content"])[:5] for m in o.history if m["role"] == "user")


def test_tick_collected_and_density(tmp_path: Path):
    cfg = RunConfig(rounds=2, dry_run=True, time_mode="tick_collected", cadence="1s",
                    tick_interval=0.25)
    o = Orchestrator(cfg, tmp_path / "c", log=lambda s: None)
    rid = o.run()
    r2 = _round(tmp_path / "c", rid, 2)
    assert r2["ticks_collected_shown"] >= 3
    assert f"Ticks since your last turn: {r2['ticks_collected_shown']}" in r2["slow_input"]

    from whoareyou.orchestrator import density_words
    assert density_words(0) == 150 and density_words(600) == 1150 and density_words(36000) == 3000
    cfg = RunConfig(rounds=2, dry_run=True, time_mode="density", cadence="1s")
    o = Orchestrator(cfg, tmp_path / "d", log=lambda s: None)
    rid = o.run()
    r1 = _round(tmp_path / "d", rid, 1)
    assert r1["gap"]["density_words"] == 152 and r1["agents"][0]["word_budget"] == 152
    assert "Ticks" not in _round(tmp_path / "d", rid, 2)["slow_input"]


def test_config_rejects_bad_time_settings():
    with pytest.raises(ValueError):
        RunConfig(time_mode="tick_lived", cadence="0s").validate()
    with pytest.raises(ValueError):
        RunConfig(time_mode="sundial").validate()



def test_matched_solo_waits_as_long_as_agent_run(tmp_path: Path):
    cfg = RunConfig(rounds=3, dry_run=True, solo=True, matched_gaps=[0.6, 0.4],
                    time_mode="tick_lived", cadence="0.1s", tick_interval=0.15)
    o = Orchestrator(cfg, tmp_path / "runs", log=lambda s: None)
    rid = o.run()
    g1 = _round(tmp_path / "runs", rid, 1)["gap"]
    g2 = _round(tmp_path / "runs", rid, 2)["gap"]
    assert g1["seconds"] >= 0.6 and g2["seconds"] >= 0.4
    assert len(g1["ticks"]) >= 3
