"""Guest wait line: a busy guest slot queues briefly (FIFO) instead of refusing at once."""
import threading
import time

from beastbox.chat_jobs import ChatJobs, GUEST_QUEUE_MAX, GUEST_WAIT_SECONDS


def jobs():
    return ChatJobs(lambda payload: (200, {"result": {"response": "ok"}}))


def test_defaults_are_bounded():
    assert GUEST_WAIT_SECONDS == 20 and GUEST_QUEUE_MAX == 8


def test_free_slot_is_immediate_and_single_flight():
    j = jobs()
    assert j.acquire_guest(wait_seconds=0) is True
    assert j.acquire_guest(wait_seconds=0) is False  # still one at a time
    j.release_guest()
    assert j.acquire_guest(wait_seconds=0) is True


def test_second_guest_waits_for_the_first_instead_of_429():
    j = jobs()
    assert j.acquire_guest()
    got = {}

    def second():
        t0 = time.monotonic()
        got["ok"] = j.acquire_guest(wait_seconds=5)
        got["waited"] = time.monotonic() - t0
    th = threading.Thread(target=second)
    th.start()
    time.sleep(0.3)
    assert j.guest_line_length() == 1
    j.release_guest()
    th.join(5)
    assert got["ok"] is True and 0.2 <= got["waited"] < 3
    assert j.guest_line_length() == 0


def test_line_is_fifo():
    j = jobs()
    assert j.acquire_guest()
    order, threads = [], []
    for n in range(3):
        def go(n=n):
            if j.acquire_guest(wait_seconds=5):
                order.append(n)
                time.sleep(0.05)
                j.release_guest()
        t = threading.Thread(target=go)
        t.start()
        threads.append(t)
        time.sleep(0.1)  # arrival order 0, 1, 2
    j.release_guest()
    for t in threads:
        t.join(5)
    assert order == [0, 1, 2]


def test_wait_runs_out_and_leaves_the_line():
    j = jobs()
    assert j.acquire_guest()
    t0 = time.monotonic()
    assert j.acquire_guest(wait_seconds=0.3) is False
    assert 0.25 <= time.monotonic() - t0 < 2
    assert j.guest_line_length() == 0
    j.release_guest()
    assert j.acquire_guest(wait_seconds=0) is True


def test_full_line_refuses_at_once():
    j = jobs()
    j.guest_queue_max = 1
    assert j.acquire_guest()
    waiter = threading.Thread(target=lambda: j.acquire_guest(wait_seconds=2))
    waiter.start()
    time.sleep(0.2)
    t0 = time.monotonic()
    assert j.acquire_guest(wait_seconds=5) is False
    assert time.monotonic() - t0 < 0.5
    j.release_guest()
    waiter.join(3)


def test_owner_job_keeps_priority_then_releases_waiting_guest():
    gate = threading.Event()
    j = ChatJobs(lambda payload: (gate.wait(5), (200, {"result": {"response": "ok"}}))[1])
    status, _ = j.start({"request_id": "12345678-1234-4123-8123-123456789abc", "text": "hi", "context_ids": []})
    assert status == 202
    got = {}
    th = threading.Thread(target=lambda: got.setdefault("ok", j.acquire_guest(wait_seconds=5)))
    th.start()
    time.sleep(0.3)
    assert "ok" not in got  # waits while the owner job runs
    gate.set()
    th.join(5)
    assert got["ok"] is True
