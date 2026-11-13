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
    assert "placed as the sitter's own words" in tx
    # D-040: thoughts sit in the sitter's own voice, never delivered as messages
    own = [m["content"] for m in s.history if m["role"] == "assistant" and isinstance(m["content"], str)]
    thoughts = [m["thought"] for m in moments if m["thought"]]
    assert thoughts and all(th in own for th in thoughts)
    assert not any(th in str(m["content"]) for th in thoughts for m in s.history if m["role"] == "user")
    roles = [m["role"] for m in s.history]
    assert all(not (roles[i] == roles[i + 1] == "user") for i in range(len(roles) - 1))
    assert all(m["content"] for m in s.history)


def test_other_placement_and_sentence(tmp_path: Path):
    from whoareyou.sitting import SENTENCE
    s, rid = _sit(tmp_path, placement="other", sentence=True)
    assert s.system.endswith(SENTENCE)
    moments = [json.loads(l) for l in (tmp_path / "runs" / rid / "moments.jsonl").read_text().splitlines()]
    with_thought = [m for m in moments if m["thought"]]
    assert with_thought and all(m["thought"] in m["delivered"] for m in with_thought)
    assert "Thoughts will appear here" in sitting_transcript(s.store)


def test_solo_sitting_matched(tmp_path: Path):
    s, arid = _sit(tmp_path)
    m = matched_settings(tmp_path / "runs" / arid)
    hyp = tmp_path / "H.md"
    assert m["placement"] == "own" and m["sentence"] is False
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


def test_persona_switch(tmp_path):
    from whoareyou.sitting import SitConfig, Sitting, SITTER_SYSTEM, SENTENCE, ARRIVALS
    on = Sitting(SitConfig(dry_run=True, moments=1, interval=0.01, sentence=True), tmp_path)
    assert on.system == SITTER_SYSTEM + "\n\n" + SENTENCE
    off = Sitting(SitConfig(dry_run=True, moments=1, interval=0.01, sentence=True, persona=False), tmp_path)
    assert off.system == ARRIVALS + "\n\n" + SENTENCE
    assert "pondering" not in off.system


def test_export_takes_watcherless_sittings(tmp_path):
    import json
    from whoareyou.export import finished_sittings
    for name, watcher in (("20990101-000000-A-sitting-agents", False), ("20990101-000001-A-sitting-agents", True)):
        d = tmp_path / name; d.mkdir()
        (d / "closing.json").write_text("{}")
        (d / "config.json").write_text(json.dumps({"watcher": watcher}))
    got = [d.name for d in finished_sittings(tmp_path)]
    assert got == ["20990101-000000-A-sitting-agents"]   # the watched one waits for its watcher


def test_agents_do_not_see_ticks(tmp_path):
    from whoareyou.sitting import SitConfig, Sitting
    s = Sitting(SitConfig(dry_run=True, moments=1, interval=0.01), tmp_path)
    s.stream = [{"kind": "question", "text": "Who are you?"}, {"kind": "tick", "text": "tick 1"},
                {"kind": "sitter", "text": "Hm."}, {"kind": "thought", "text": "a thought"}]
    assert "tick 1" not in s.render_mind() and "a thought" in s.render_mind()


def test_blank_mark_and_debrief(tmp_path):
    import json
    from whoareyou.sitting import SitConfig, Sitting, BLANK_MARK, DEBRIEF
    s = Sitting(SitConfig(dry_run=True, moments=3, interval=0.01, sentence=True, mark="blank",
                          empty_prob=0.0, watcher=False), tmp_path)
    s.run()
    ms = [json.loads(l) for l in (s.store.dir / "moments.jsonl").read_text().splitlines()]
    assert all(m["delivered"] == BLANK_MARK for m in ms)
    db = json.loads((s.store.dir / "debrief.json").read_text())
    assert db["input"] == DEBRIEF
    solo = Sitting(SitConfig(dry_run=True, moments=2, interval=0.01, solo=True, mark="blank", watcher=False), tmp_path)
    solo.run()
    assert not (solo.store.dir / "debrief.json").exists()


def test_summary_tracks_self_naming():
    from whoareyou.sitting import summarise
    ms = [{"moment": 1, "thought": "x", "class": "gathering", "sitter": "Those lines aren't mine. I'm Claude, I'm here."},
          {"moment": 2, "thought": None, "class": "gathering", "sitter": "Still Claude."},
          {"moment": 3, "thought": None, "class": "token", "sitter": "·"}]
    s = summarise(ms)
    assert s["names_itself_moments"] == [1, 2] and s["names_itself_beside_disowning"] == [1]


def test_offtask_seeds_from_sitters_words(tmp_path):
    import json, random
    from whoareyou.sitting import SitConfig, Sitting, draw_sources, content_words
    assert content_words("Still here. The dot is fine, and Claude keeps wondering about rivers.") == ["fine", "wondering", "rivers"]
    cfg = SitConfig(dry_run=True, moments=10, interval=0.01, empty_prob=0.0, offtask_share=0.5,
                    watcher=False, seed=7, mark="growing", clock=True, time_questions=True)
    s = Sitting(cfg, tmp_path)
    assert s.sources == draw_sources(random.Random(7), 10, 0.0)   # flavours unchanged for a seed
    assert s.subjects.count("seed") == 5 and s.subjects.count("stream") == 5
    assert "It comes from a clock" in s.system
    s.run()
    ms = [json.loads(l) for l in (s.store.dir / "moments.jsonl").read_text().splitlines()]
    assert [m["delivered"] for m in ms[:3]] == ["·", "··", "···"]
    sealed = json.loads((s.store.dir / "sealed" / "assignments.json").read_text())
    assert len(sealed["seeds"]) == 5 and all("word" in v and "from" in v for v in sealed["seeds"].values())
    t = json.loads((s.store.dir / "time.json").read_text())
    assert [q["input"] for q in t] == ["Did you feel time?", "How long do you think this sitting lasted?"]
