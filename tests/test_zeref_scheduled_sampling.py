import torch

from scripts.run_zeref_scheduled_sampling_stage import scheduled_sampling_input


def test_scheduled_sampling_only_replaces_response_history_positions():
    # loss_mask marks targets at positions 3..5. The input token at position 4
    # is the previous response character for the target at position 4, so only
    # positions whose previous target was supervised may be replaced.
    x = torch.tensor([[10, 11, 12, 13, 14, 15]], dtype=torch.long)
    loss_mask = torch.tensor([[0, 0, 0, 1, 1, 1]], dtype=torch.float32)
    logits = torch.full((1, 6, 32), -100.0)
    predicted_targets = [20, 21, 22, 23, 24, 25]
    for pos, token in enumerate(predicted_targets):
        logits[0, pos, token] = 100.0
    mixed, replaced = scheduled_sampling_input(
        x,
        logits,
        loss_mask,
        probability=1.0,
        generator=torch.Generator().manual_seed(1),
        excluded_ids=set(),
    )
    # Prompt and first-response prediction context are untouched.
    assert mixed[0, :4].tolist() == x[0, :4].tolist()
    # x[4] receives argmax(y prediction at pos 3), x[5] gets pos 4.
    assert mixed[0, 4:].tolist() == [23, 24]
    assert int(replaced.sum().item()) == 2


def test_scheduled_sampling_never_replaces_with_excluded_stop_or_pad_tokens():
    x = torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)
    loss_mask = torch.tensor([[0, 0, 1, 1, 1]], dtype=torch.float32)
    logits = torch.full((1, 5, 16), -100.0)
    logits[0, 2, 9] = 100.0  # excluded newline
    logits[0, 3, 8] = 100.0  # allowed generated character
    mixed, replaced = scheduled_sampling_input(
        x,
        logits,
        loss_mask,
        probability=1.0,
        generator=torch.Generator().manual_seed(2),
        excluded_ids={9},
    )
    assert mixed[0, 3].item() == x[0, 3].item()
    assert mixed[0, 4].item() == 8
    assert int(replaced.sum().item()) == 1


def test_zero_probability_is_exact_teacher_forcing():
    x = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
    loss_mask = torch.tensor([[0, 0, 1, 1]], dtype=torch.float32)
    logits = torch.randn(1, 4, 10)
    mixed, replaced = scheduled_sampling_input(
        x,
        logits,
        loss_mask,
        probability=0.0,
        generator=torch.Generator().manual_seed(3),
        excluded_ids=set(),
    )
    assert torch.equal(mixed, x)
    assert int(replaced.sum().item()) == 0
