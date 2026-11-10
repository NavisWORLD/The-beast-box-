"""The companion JSON keeps every record. search() k is the window. A crash before replace leaves the last file."""
from pathlib import Path

from beastbox.companion_local.memory import MAX_RECORDS, CompanionMemory


def test_search_window_is_not_the_file_and_a_crash_before_replace_keeps_the_file(tmp_path, monkeypatch):
    path = tmp_path / "memory.json"
    memory = CompanionMemory(path)
    for i in range(MAX_RECORDS + 5):
        memory.add(f"grove note number {i}", "note", "keeper")
    assert len(memory.records) == MAX_RECORDS + 5
    assert len(memory.search("grove", k=4)) == 4
    reloaded = CompanionMemory(path)
    assert [row["text"] for row in reloaded.records] == [row["text"] for row in memory.records]
    assert reloaded.records[0]["id"] == memory.records[0]["id"]

    def crash(self, target):
        raise OSError("crash before replace")

    monkeypatch.setattr(Path, "replace", crash)
    try:
        memory.add("this note must not land", "note", "keeper")
    except OSError as error:
        assert "crash before replace" in str(error)
    survived = CompanionMemory(path)
    assert len(survived.records) == MAX_RECORDS + 5
    assert survived.records[-1]["text"] == f"grove note number {MAX_RECORDS + 4}"
    assert not any(row["text"] == "this note must not land" for row in survived.records)
