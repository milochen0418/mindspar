from mindspar import history
from mindspar.i18n import kind_labels


def _round(kind, ai_ok, ai_secs=10.0, wager=2, answered=True):
    return {"kind": kind, "you_ok": True, "you_points": 100, "you_secs": 5.0, "ai_ok": ai_ok, "ai_points": 0, "ai_secs": ai_secs, "ai_wager": wager, "ai_answered": answered, "ai_well_formed": True}


def test_matches_are_kept_and_summed_per_model(tmp_path, monkeypatch):
    monkeypatch.setenv("MINDSPAR_DATA_DIR", str(tmp_path))
    history.save({"model": "Ollama (qwen3.5:9b)", "you": 300, "ai": 100, "rounds": [_round("arith", True, 20.0, 3), _round("target", False, None, 1, False)]})
    history.save({"model": "Ollama (qwen3.5:9b)", "you": 100, "ai": 400, "rounds": [_round("arith", False, 30.0, 3)]})
    history.save({"model": "Claude (claude-opus-5-5)", "you": 0, "ai": 0, "rounds": [_round("count", True, 4.0)]})
    (tmp_path / "matches.jsonl").open("a").write("not json\n")

    rows = history.board(history.load(), kind_labels("zh"))
    assert [r.model for r in rows] == ["Ollama (qwen3.5:9b)", "Claude (claude-opus-5-5)"]
    qwen = rows[0]
    assert (qwen.matches, qwen.you_won, qwen.ai_won, qwen.draws) == (2, 1, 1, 0)
    assert qwen.ai_right == "33%"
    assert qwen.ai_secs == "25.0"
    assert qwen.sure_right == "1/2"
    cells = {c.kind: c for c in qwen.kinds}
    assert (cells["arith"].label, cells["arith"].right, cells["arith"].tone) == ("心算", "1/2", "fair")
    assert (cells["target"].right, cells["target"].tone) == ("0/1", "poor")
    assert (cells["count"].right, cells["count"].tone) == ("–", "none")
    assert rows[1].draws == 1


def test_no_file_no_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("MINDSPAR_DATA_DIR", str(tmp_path / "none"))
    assert history.board(history.load(), {}) == []
