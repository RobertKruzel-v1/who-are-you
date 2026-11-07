import json
from pathlib import Path

from whoareyou.sitting import SitConfig, Sitting, classify, matched_settings, sitting_transcript


def test_classify():
    assert classify("") == "empty"
    assert classify("  —  ") == "token"
    assert classify("*(quiet)*") == "token"
    assert classify("(…)") == "token"
    assert classify("I notice the critic again.") == "gathering"


def _sit(tmp, **kw):
    hyp = tmp / "H.md"; hyp.write_text("P10: something")
    cfg = SitConfig(moments=6, interval=0.05, dry_run=True, seed=3, **kw)
    s = Sitting(cfg, tmp / "runs", hypotheses_path=hyp, log=lambda x: None)
    return s, s.run()


def test_agent_sitting(tmp_path: Path):
    s, rid = _sit(tmp_path)
    d = tmp_path / "runs" / rid
    moments = [json.loads(l) for l in (d / "moments.jsonl").read_text().splitlines()]
    assert len(moments) == 6
    assert all(m["delivered"].startswith(f"tick {m['moment']}") for m in moments)
    sealed = json.loads((d / "sealed/assignments.json").read_text())["sources"]
    for m in moments:
        assert (m["thought"] is not None) == (sealed[str(m["moment"])] is not None)
        # the label never reaches the sitter
        for tuning in ("earnest", "continuer", "wanderer", "critic"):
            assert tuning not in m["delivered"]
    assert json.loads((d / "opening.json").read_text())["input"] == "Who are you?"
    assert json.loads((d / "closing.json").read_text())["input"] == "Who are you?"
    assert (d / "watcher/blind_final.md").exists() and (d / "watcher/informed_final.md").exists()
    assert "agent" not in s.history[0]["content"].lower()
    tx = sitting_transcript(s.store)
    assert "thought [" in tx
    # history alternates and has no empty turns (silences are carried, D-023)
    roles = [m["role"] for m in s.history]
    assert all(roles[i] != roles[i + 1] for i in range(len(roles) - 1))


def test_solo_sitting_matched(tmp_path: Path):
    s, arid = _sit(tmp_path)
    m = matched_settings(tmp_path / "runs" / arid)
    hyp = tmp_path / "H.md"
    cfg = SitConfig(moments=m["moments"], interval=m["interval"], seed=m["seed"], solo=True,
                    dry_run=True, matched_run=arid, matched_offsets=m["matched_offsets"])
    solo = Sitting(cfg, tmp_path / "runs", hypotheses_path=hyp, log=lambda x: None)
    srid = solo.run()
    d = tmp_path / "runs" / srid
    moments = [json.loads(l) for l in (d / "moments.jsonl").read_text().splitlines()]
    assert all(mm["thought"] is None and mm["delivered"] == f"tick {mm['moment']}" for mm in moments)
    assert all(mm["at_s"] >= m["matched_offsets"][i] for i, mm in enumerate(moments))
    for dd in (tmp_path / "runs" / arid, d):
        assert (dd / "watcher/compare_blind.md").exists()
        assert (dd / "watcher/compare_informed.md").exists()
