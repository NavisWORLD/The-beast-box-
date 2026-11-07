"""Archive first, then window: the bridge's guest replay window may trim/evict; guest_archive never loses a turn."""
from beastbox.guest_hebbian import MAX_TURNS, GuestHebbianStore

A = "a" * 64
B = "b" * 64


def test_archive_keeps_every_turn_past_the_window_and_eviction(tmp_path):
    clock = [1_000_000]
    store = GuestHebbianStore(tmp_path, ttl_days=1, max_guests=1, now_fn=lambda: clock[0])
    for i in range(MAX_TURNS):  # 2*MAX_TURNS turns, window keeps MAX_TURNS
        assert store.save(A, f"guest {i}", f"reply {i}") is not None
    arch = store.archived(A)
    assert len(arch) == 2 * MAX_TURNS
    assert arch[0]["t"] == "guest 0" and arch[-1]["t"] == f"reply {MAX_TURNS - 1}"
    store.save(B, "other", "other reply")  # evicts A's window (max_guests=1)
    assert len(store.archived(A)) == 2 * MAX_TURNS
    assert [t["t"] for t in store.archived(B)] == ["other", "other reply"]  # per-guest only
    clock[0] += 3 * 86400  # TTL expiry of the window
    store.load(A) if hasattr(store, "load") else None
    assert len(store.archived(A)) == 2 * MAX_TURNS


def test_archive_module_never_deletes_or_updates_archive():
    import inspect
    import beastbox.guest_hebbian as m
    src = inspect.getsource(m)
    assert "DELETE FROM guest_archive" not in src and "UPDATE guest_archive" not in src
