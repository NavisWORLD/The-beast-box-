"""Deterministic, function-preserving checkpoint growth for Zeref (TRACK 1).

Pure standard library. No torch on this box, so this module operates on a
generic tensor-like mapping: a state dict of ``{name: nested lists}`` where a
scalar tensor is a plain float and every other tensor is a rectangular nested
list of floats, using the exact key names and shapes of
``models/rawrphos/architecture/model.py`` (RawrphosLM).

What it does
------------
* ``grow_depth``: append ``add`` new blocks. Each new block copies the last
  parent block, then zeroes its output projections (``attn.proj`` weight and
  bias, ``ffn.2`` weight and bias), so each new block is an identity residual
  and the grown model returns the parent's outputs at initialization. The old
  final block gains a state transition copied from block 0 when it lacks one,
  matching ``grow_depth`` in ``model.py``. One deliberate difference from the
  torch path: the torch path fresh-random-inits new blocks, while this module
  copies the last block, because this module must be deterministic with no
  RNG. Both are identity at init for the same reason: the output projections
  are exactly zero.
* ``grow_width``: widen the residual stream from ``d_model`` to a larger
  width. New rows and columns are exactly zero, RMSNorm weights on the old
  dims are rescaled by ``sqrt(d_old / d_new)``, and the head dimension is
  preserved (heads scale with width), so the widened model also preserves the
  parent's outputs at initialization, up to the 1e-6 RMSNorm epsilon term in
  the production model (this module's probes use eps 0, where the match is
  exact; see ``parity_check``).
* ``verify_function_preserving`` / ``parity_check``: structural plus numeric
  checks that a grown state really is function-preserving at init. The
  numeric depth proof evaluates both residual branches of every new block on
  a probe vector using the real tensors. The numeric width proof checks the
  embedding to final-norm to tied-logit path and every block's FFN branch.
  Attention under width growth is covered by a structural lemma, not by a
  numeric attention evaluation: zero-padded qkv/proj plus a preserved head
  dimension implies identical attention outputs on the old dims for any
  input. This module has no attention evaluator, so that lemma is reported
  as STRUCTURAL, and full numeric attention parity is NULL here: it is the
  job of the torch-side check and of the gate below.

Production torch path
---------------------
Convert a real state dict with ``{k: v.tolist() for k, v in sd.items()}``,
run ``grow_depth`` / ``grow_width`` here, then rebuild with
``{k: torch.tensor(v) for k, v in grown.items()}`` and
``model.load_state_dict(...)``. For depth growth the torch path already has
``model.grow_depth`` in ``models/rawrphos/architecture/model.py``; prefer
that in production and use this module as the torch-free mirror and as the
only width-growth implementation. Width growth has no torch counterpart yet.

Gate note (binding)
-------------------
Every grown candidate is only a candidate. It still runs through the full
8+1 paired-control gate (delta_NLL_12D and JSD_12D included) and the 5,827
heldout hash screen before any R_pin promotion PR is opened. This module
does not promote, does not touch the 006 workflow, does not touch the Talk
thread, S_lived/S_taught, R_pin, checkpoints, ledgers, or any SHA-256 chain
entry. Growth here is propose-gate-promote only.

Evidence taxonomy used in the check reports: MEASURED means a number was
computed here; STRUCTURAL means a property was proved from the shapes and
the zero padding; NULL means not established by this module.

Related code: ``scripts/zeref_growth_trigger.py`` decides WHEN to grow (it
is never a gate input); this module decides HOW the tensors grow.
"""

import argparse
import copy
import hashlib
import json
import math
import sys

PHI = (1.0 + 5.0 ** 0.5) / 2.0
STATE_WIDTH = 12
STATE42_WIDTH = 42
COND_WIDTH = 54


def hidden_width(d_model):
    """MLP hidden width used by model.py: int(d_model * phi)."""
    return int(d_model * PHI)


def shape_of(value):
    """Shape tuple of a scalar float or a rectangular nested list."""
    if isinstance(value, bool):
        raise ValueError("tensor values must be numbers, not booleans")
    if isinstance(value, (int, float)):
        return ()
    if isinstance(value, list):
        if not value:
            raise ValueError("empty tensors are not supported")
        inner = shape_of(value[0])
        for item in value[1:]:
            if shape_of(item) != inner:
                raise ValueError("ragged tensor: rows have different shapes")
        return (len(value),) + inner
    raise ValueError("tensor values must be numbers or nested lists, got %s" % type(value).__name__)


def numel(shape):
    out = 1
    for dim in shape:
        out *= dim
    return out


def zeros(shape):
    if not shape:
        return 0.0
    return [zeros(shape[1:]) for _ in range(shape[0])]


def zeros_like(value):
    return zeros(shape_of(value))


def count_parameters(state):
    """Total parameter count of a generic state dict."""
    if not isinstance(state, dict) or not state:
        raise ValueError("state must be a nonempty dict")
    total = 0
    for key, value in state.items():
        total += numel(shape_of(value))
    return total


def parameter_count_for_config(vocab_size, d_model, n_layers, n_heads,
                               state_mode="tri", cond54=True,
                               cond54_direct=True, hebbian=False,
                               hebbian_dim=32):
    """Analytic parameter count for a RawrphosLM config, from model.py shapes.

    Reference point: vocab 4096, d_model 256, 44 layers, 4 heads, tri,
    cond54, cond54_direct, no Hebbian gives 22,620,887 parameters, which is
    within 0.1 percent of the 22.64M figure quoted for the live pin. The
    exact live-pin config is not stated in any file on main, so that figure
    itself is not re-derived here beyond this shape count.
    """
    cfg = validate_config({
        "vocab_size": vocab_size, "d_model": d_model, "n_layers": n_layers,
        "n_heads": n_heads, "state_mode": state_mode, "cond54": cond54,
        "cond54_direct": cond54_direct, "hebbian": hebbian,
        "hebbian_dim": hebbian_dim,
    })
    d = cfg["d_model"]
    hidden = hidden_width(d)
    attn = (3 * d * d + 3 * d) + (d * d + d) + 2
    ffn = (d * hidden + hidden) + (hidden * d + d)
    norms = 2 * d
    if cfg["state_mode"] == "tri":
        transition = 12 + 12 + 42 + (42 * d + 42) + 42 * 42 + 12 * 42 + 42 * 12 + 1
    else:
        transition = 12 + 12
    per_nonfinal = norms + attn + ffn + transition
    per_final = norms + attn + ffn
    total = (cfg["n_layers"] - 1) * per_nonfinal + per_final
    total += cfg["vocab_size"] * d
    total += 12 * d + 12
    total += d
    if cfg["state_mode"] == "tri":
        total += 42 * d + 42
    if cfg["cond54"]:
        total += COND_WIDTH
    if cfg["cond54_direct"]:
        total += COND_WIDTH * d
    if cfg["hebbian"]:
        total += d + 3 * (cfg["hebbian_dim"] * d) + cfg["hebbian_dim"] * d + 1
    return total


def validate_config(config):
    """Validate a config dict with the same rules as RawrphosConfig."""
    if not isinstance(config, dict):
        raise ValueError("config must be a dict")
    cfg = {
        "vocab_size": config.get("vocab_size", 4096),
        "d_model": config.get("d_model", 256),
        "n_layers": config.get("n_layers", 44),
        "n_heads": config.get("n_heads", 4),
        "state_mode": config.get("state_mode", "tri"),
        "cond54": config.get("cond54", True),
        "cond54_direct": config.get("cond54_direct", True),
        "hebbian": config.get("hebbian", False),
        "hebbian_dim": config.get("hebbian_dim", 32),
    }
    for name in ("vocab_size", "d_model", "n_heads", "n_layers", "hebbian_dim"):
        if type(cfg[name]) is not int or cfg[name] < 1:
            raise ValueError("invalid %s" % name)
    if cfg["d_model"] % cfg["n_heads"] or (cfg["d_model"] // cfg["n_heads"]) % 2:
        raise ValueError("heads must divide width and have an even rotary dimension")
    if cfg["state_mode"] not in ("dyn12", "tri"):
        raise ValueError("state_mode must be dyn12 or tri")
    if type(cfg["cond54"]) is not bool or (cfg["cond54"] and cfg["state_mode"] != "tri"):
        raise ValueError("cond54 needs state_mode tri")
    if type(cfg["cond54_direct"]) is not bool or (cfg["cond54_direct"] and not cfg["cond54"]):
        raise ValueError("cond54_direct needs a cond54 model")
    if type(cfg["hebbian"]) is not bool:
        raise ValueError("hebbian must be a bool")
    return cfg


def block_indices(state):
    """Sorted block indices present in a state dict."""
    found = set()
    for key in state:
        if key.startswith("blocks."):
            rest = key.split(".")
            if len(rest) < 3 or not rest[1].isdigit():
                raise ValueError("malformed block key %r" % key)
            found.add(int(rest[1]))
    if not found:
        raise ValueError("state has no blocks.* keys")
    ordered = sorted(found)
    if ordered != list(range(ordered[-1] + 1)):
        raise ValueError("block indices are not contiguous from 0")
    return ordered


def canonical_hash(state):
    """Deterministic sha256 of a state dict (sorted keys, compact JSON)."""
    blob = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _is_all_zero(value):
    if isinstance(value, (int, float)):
        return value == 0.0
    return all(_is_all_zero(item) for item in value)


def _pad_cols(matrix, new_cols):
    rows = len(matrix)
    cols = len(matrix[0])
    if new_cols < cols:
        raise ValueError("pad target smaller than current width")
    return [list(row) + [0.0] * (new_cols - cols) for row in matrix]


def _pad_rows(matrix, new_rows):
    cols = len(matrix[0])
    if new_rows < len(matrix):
        raise ValueError("pad target smaller than current height")
    return [list(row) for row in matrix] + [[0.0] * cols for _ in range(new_rows - len(matrix))]


def _pad_matrix(matrix, new_rows, new_cols):
    widened = _pad_cols(matrix, new_cols)
    return _pad_rows(widened, new_rows)


def _extend_vector(vector, new_len):
    if new_len < len(vector):
        raise ValueError("pad target smaller than current length")
    return list(vector) + [0.0] * (new_len - len(vector))


def _scale_and_extend_norm(vector, new_len, factor):
    if new_len < len(vector):
        raise ValueError("pad target smaller than current length")
    return [v * factor for v in vector] + [0.0] * (new_len - len(vector))


def grow_depth(state, add):
    """Append ``add`` function-preserving blocks to a state dict.

    Returns (grown_state, report). Every parent tensor is copied exactly.
    """
    if type(add) is not int or add < 1:
        raise ValueError("grow_depth adds >=1 blocks")
    if not isinstance(state, dict) or not state:
        raise ValueError("state must be a nonempty dict")
    for value in state.values():
        shape_of(value)
    indices = block_indices(state)
    n = len(indices)
    parent_params = count_parameters(state)
    grown = copy.deepcopy(state)
    new_keys = []
    for i in range(n, n + add):
        prefix = "blocks.%d." % (n - 1)
        for key in sorted(state):
            if key.startswith(prefix):
                new_key = "blocks.%d.%s" % (i, key[len(prefix):])
                grown[new_key] = copy.deepcopy(state[key])
                new_keys.append(new_key)
        for key in list(grown):
            if key.startswith("blocks.%d." % i) and (".attn.proj." in key or ".ffn.2." in key):
                grown[key] = zeros_like(grown[key])
    fresh_keys = []
    old_final = "blocks.%d." % (n - 1)
    has_transition = any(k.startswith(old_final + "transition.") for k in state)
    if not has_transition:
        for key in sorted(state):
            if key.startswith("blocks.0.transition."):
                new_key = old_final + key[len("blocks.0."):]
                grown[new_key] = copy.deepcopy(state[key])
                fresh_keys.append(new_key)
    fresh_keys.extend(new_keys)
    report = {
        "kind": "depth",
        "parent_layers": n,
        "grown_layers": n + add,
        "added_layers": add,
        "parent_params": parent_params,
        "grown_params": count_parameters(grown),
        "parent_sha256": canonical_hash(state),
        "grown_sha256": canonical_hash(grown),
        "new_keys": sorted(new_keys),
        "fresh_keys": sorted(fresh_keys),
    }
    report["added_params"] = report["grown_params"] - report["parent_params"]
    return grown, report


def grow_width(state, config, new_d_model, new_n_heads=None):
    """Widen the residual stream, preserving the parent outputs at init.

    Heads scale with width so the head dimension is preserved; that is what
    keeps attention scores unchanged. RMSNorm weights on the old dims are
    rescaled by sqrt(d_old / d_new). Returns (grown_state, new_config, report).
    """
    cfg = validate_config(config)
    d_old = cfg["d_model"]
    if type(new_d_model) is not int or new_d_model <= d_old:
        raise ValueError("grow_width needs a new d_model larger than the current one")
    if new_n_heads is None:
        if (new_d_model * cfg["n_heads"]) % d_old:
            raise ValueError("new d_model must keep the head dimension: scale heads with width")
        new_n_heads = new_d_model * cfg["n_heads"] // d_old
    if type(new_n_heads) is not int or new_n_heads < 1:
        raise ValueError("invalid new_n_heads")
    if new_d_model % new_n_heads or (new_d_model // new_n_heads) % 2:
        raise ValueError("new heads must divide new width and have an even rotary dimension")
    if new_d_model // new_n_heads != d_old // cfg["n_heads"]:
        raise ValueError("width growth must preserve the head dimension")
    if not isinstance(state, dict) or not state:
        raise ValueError("state must be a nonempty dict")
    for value in state.values():
        shape_of(value)
    indices = block_indices(state)
    hidden_old = hidden_width(d_old)
    hidden_new = hidden_width(new_d_model)
    factor = math.sqrt(d_old / new_d_model)
    parent_params = count_parameters(state)
    grown = {}
    for key in sorted(state):
        value = state[key]
        if key == "token.weight":
            if shape_of(value) != (cfg["vocab_size"], d_old):
                raise ValueError("unexpected shape for %s: %s" % (key, shape_of(value)))
            grown[key] = _pad_cols(value, new_d_model)
        elif key in ("state_init.weight", "state_init42.weight"):
            grown[key] = _pad_cols(value, new_d_model)
        elif key in ("state_init.bias", "state_init42.bias", "cond_gain"):
            grown[key] = copy.deepcopy(value)
        elif key == "cond_in.weight":
            if shape_of(value) != (d_old, COND_WIDTH):
                raise ValueError("unexpected shape for %s: %s" % (key, shape_of(value)))
            grown[key] = _pad_rows(value, new_d_model)
        elif key == "norm.weight" or key.endswith(".n1.weight") or key.endswith(".n2.weight") \
                or key == "hebbian.norm.weight":
            if shape_of(value) != (d_old,):
                raise ValueError("unexpected shape for %s: %s" % (key, shape_of(value)))
            grown[key] = _scale_and_extend_norm(value, new_d_model, factor)
        elif ".attn.qkv.weight" in key:
            if shape_of(value) != (3 * d_old, d_old):
                raise ValueError("unexpected shape for %s: %s" % (key, shape_of(value)))
            out = zeros((3 * new_d_model, new_d_model))
            for seg in range(3):
                for r in range(d_old):
                    for c in range(d_old):
                        out[seg * new_d_model + r][c] = value[seg * d_old + r][c]
            grown[key] = out
        elif ".attn.qkv.bias" in key:
            if shape_of(value) != (3 * d_old,):
                raise ValueError("unexpected shape for %s: %s" % (key, shape_of(value)))
            out = []
            for seg in range(3):
                out.extend(value[seg * d_old:(seg + 1) * d_old])
                out.extend([0.0] * (new_d_model - d_old))
            grown[key] = out
        elif ".attn.proj.weight" in key:
            grown[key] = _pad_matrix(value, new_d_model, new_d_model)
        elif ".attn.proj.bias" in key:
            grown[key] = _extend_vector(value, new_d_model)
        elif ".attn.gate_logit" in key or ".attn.log_sigma" in key:
            grown[key] = value
        elif ".ffn.0.weight" in key:
            if shape_of(value) != (hidden_old, d_old):
                raise ValueError("unexpected shape for %s: %s" % (key, shape_of(value)))
            grown[key] = _pad_matrix(value, hidden_new, new_d_model)
        elif ".ffn.0.bias" in key:
            grown[key] = _extend_vector(value, hidden_new)
        elif ".ffn.2.weight" in key:
            if shape_of(value) != (d_old, hidden_old):
                raise ValueError("unexpected shape for %s: %s" % (key, shape_of(value)))
            grown[key] = _pad_matrix(value, new_d_model, hidden_new)
        elif ".ffn.2.bias" in key:
            grown[key] = _extend_vector(value, new_d_model)
        elif ".transition.drive.weight" in key:
            grown[key] = _pad_cols(value, new_d_model)
        elif key == "hebbian.out.weight":
            grown[key] = _pad_rows(value, new_d_model)
        elif key.startswith("hebbian.") and key.endswith(".weight"):
            grown[key] = _pad_cols(value, new_d_model)
        elif ".transition." in key or key.startswith("hebbian."):
            grown[key] = copy.deepcopy(value)
        else:
            raise ValueError("grow_width has no rule for key %r" % key)
    new_config = dict(cfg)
    new_config["d_model"] = new_d_model
    new_config["n_heads"] = new_n_heads
    report = {
        "kind": "width",
        "parent_d_model": d_old,
        "grown_d_model": new_d_model,
        "parent_n_heads": cfg["n_heads"],
        "grown_n_heads": new_n_heads,
        "head_dim": d_old // cfg["n_heads"],
        "parent_hidden": hidden_old,
        "grown_hidden": hidden_new,
        "norm_rescale": factor,
        "parent_params": parent_params,
        "grown_params": count_parameters(grown),
        "parent_sha256": canonical_hash(state),
        "grown_sha256": canonical_hash(grown),
    }
    report["added_params"] = report["grown_params"] - report["parent_params"]
    return grown, new_config, report


def _matvec(matrix, vec):
    return [sum(row[j] * vec[j] for j in range(len(vec))) for row in matrix]


def _gelu_tanh(x):
    return 0.5 * x * (1.0 + math.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x ** 3)))


def rmsnorm(x, weight, eps=0.0):
    mean_sq = sum(v * v for v in x) / len(x)
    scale = 1.0 / math.sqrt(mean_sq + eps)
    return [v * scale * w for v, w in zip(x, weight)]


def extract_block(state, index):
    """Block tensors as a plain dict, keyed by short name."""
    prefix = "blocks.%d." % index
    block = {}
    for key, value in state.items():
        if key.startswith(prefix):
            block[key[len(prefix):]] = value
    if not block:
        raise ValueError("no such block: %d" % index)
    return block


def block_residual_branches(block, x):
    """Both residual branches of one block for a probe vector x.

    Attention is evaluated as proj @ ones + proj_bias on purpose: the
    projection is what reaches the residual stream, so a zero projection
    makes the branch zero for ANY attention pattern. The FFN branch is
    evaluated in full (norm, linear, GELU, linear).
    """
    d = len(x)
    probe = [1.0] * d
    attn_out = _matvec(block["attn.proj.weight"], probe)
    attn_branch = [a + b for a, b in zip(attn_out, block["attn.proj.bias"])]
    h = rmsnorm(x, block["n2.weight"], eps=0.0)
    hidden = _matvec(block["ffn.0.weight"], h)
    hidden = [_gelu_tanh(v + b) for v, b in zip(hidden, block["ffn.0.bias"])]
    ffn_out = _matvec(block["ffn.2.weight"], hidden)
    ffn_branch = [a + b for a, b in zip(ffn_out, block["ffn.2.bias"])]
    return attn_branch, ffn_branch


def new_block_is_identity(state, index, probe):
    """True when block ``index`` contributes exactly zero to the stream."""
    block = extract_block(state, index)
    attn_branch, ffn_branch = block_residual_branches(block, probe)
    return all(v == 0.0 for v in attn_branch + ffn_branch)


def ffn_branch(block, x):
    """FFN residual branch of one block for a probe vector x."""
    _, branch = block_residual_branches(block, x)
    return branch


def logits_path(state, x):
    """Final-norm plus tied-embedding logits for a probe stream vector x."""
    y = rmsnorm(x, state["norm.weight"], eps=0.0)
    token = state["token.weight"]
    return [sum(y[j] * token[v][j] for j in range(len(y))) for v in range(len(token))]


def _old_region(key, grown_value, parent_value, cfg, new_cfg):
    """Slice of a grown tensor holding the parent's old region, plus a scale.

    Returns (region, scale) where region has the parent's shape and equals
    the parent tensor times scale (scale is the RMSNorm rescale for norm
    weights, 1.0 everywhere else). Used to prove width growth kept every
    parent value in place.
    """
    d_old = cfg["d_model"]
    d_new = new_cfg["d_model"]
    hidden_old = hidden_width(d_old)
    hidden_new = hidden_width(d_new)
    shape = shape_of(parent_value)
    if shape == ():
        return grown_value, 1.0
    if key in ("norm.weight",) or key.endswith(".n1.weight") or key.endswith(".n2.weight") \
            or key == "hebbian.norm.weight":
        return grown_value[:d_old], math.sqrt(d_old / d_new)
    if key in ("token.weight", "state_init.weight", "state_init42.weight"):
        return [row[:d_old] for row in grown_value], 1.0
    if key == "cond_in.weight":
        return grown_value[:d_old], 1.0
    if key == "hebbian.out.weight":
        return grown_value[:d_old], 1.0
    if key.startswith("hebbian.") and key.endswith(".weight"):
        return [row[:d_old] for row in grown_value], 1.0
    if ".attn.qkv.weight" in key:
        region = []
        for seg in range(3):
            for r in range(d_old):
                region.append(grown_value[seg * d_new + r][:d_old])
        return region, 1.0
    if ".attn.qkv.bias" in key:
        region = []
        for seg in range(3):
            region.extend(grown_value[seg * d_new:seg * d_new + d_old])
        return region, 1.0
    if ".attn.proj.weight" in key:
        return [row[:d_old] for row in grown_value[:d_old]], 1.0
    if ".attn.proj.bias" in key or ".ffn.2.bias" in key:
        return grown_value[:d_old], 1.0
    if ".ffn.0.weight" in key:
        return [row[:d_old] for row in grown_value[:hidden_old]], 1.0
    if ".ffn.0.bias" in key:
        return grown_value[:hidden_old], 1.0
    if ".ffn.2.weight" in key:
        return [row[:hidden_old] for row in grown_value[:d_old]], 1.0
    if ".transition.drive.weight" in key:
        return [row[:d_old] for row in grown_value], 1.0
    return copy.deepcopy(grown_value), 1.0


def _scaled_equal(region, parent_value, scale):
    if isinstance(parent_value, (int, float)):
        return region == parent_value * scale
    return len(region) == len(parent_value) and all(
        _scaled_equal(r, p, scale) for r, p in zip(region, parent_value))


def verify_function_preserving(parent, grown, kind, config=None, new_config=None):
    """Structural checks that ``grown`` preserves ``parent`` at init.

    Returns a report whose checks each carry a status: MEASURED (a number
    was computed here) or STRUCTURAL (proved from shapes and zero padding).
    Width verification needs ``config`` and ``new_config`` so the old region
    of every tensor can be compared against its parent value.
    """
    checks = []

    def check(name, status, passed, detail):
        checks.append({"name": name, "status": status, "passed": bool(passed), "detail": detail})

    if kind == "depth":
        missing = [k for k in parent if k not in grown]
        changed = [k for k in parent if k in grown and grown[k] != parent[k]]
        check("parent_tensors_unchanged", "MEASURED", not missing and not changed,
              "missing=%d changed=%d" % (len(missing), len(changed)))
        parent_idx = block_indices(parent)
        grown_idx = block_indices(grown)
        new_blocks = [i for i in grown_idx if i not in parent_idx]
        bad = []
        for i in new_blocks:
            block = extract_block(grown, i)
            for name in ("attn.proj.weight", "attn.proj.bias", "ffn.2.weight", "ffn.2.bias"):
                if not _is_all_zero(block[name]):
                    bad.append("blocks.%d.%s" % (i, name))
        check("new_block_output_projections_zero", "MEASURED", not bad,
              "nonzero=%s" % (bad or "none"))
        old_final = parent_idx[-1]
        added_transition = [k for k in grown
                            if k.startswith("blocks.%d.transition." % old_final)
                            and k not in parent]
        if added_transition:
            ok = all(grown[k] == parent[k.replace("blocks.%d." % old_final, "blocks.0.", 1)]
                     for k in added_transition)
            check("old_final_transition_matches_block0", "STRUCTURAL", ok,
                  "copied=%d" % len(added_transition))
    elif kind == "width":
        if config is None or new_config is None:
            raise ValueError("width verification needs config and new_config")
        cfg = validate_config(config)
        new_cfg = validate_config(new_config)
        bad = []
        for key in parent:
            if key not in grown:
                bad.append(key)
                continue
            region, scale = _old_region(key, grown[key], parent[key], cfg, new_cfg)
            if not _scaled_equal(region, parent[key], scale):
                bad.append(key)
        check("parent_old_region_unchanged", "MEASURED", not bad,
              "mismatched=%s" % (bad or "none"))
        check("head_dim_preserved", "STRUCTURAL",
              new_cfg["d_model"] // new_cfg["n_heads"] == cfg["d_model"] // cfg["n_heads"],
              "head_dim=%d -> %d" % (cfg["d_model"] // cfg["n_heads"],
                                     new_cfg["d_model"] // new_cfg["n_heads"]))
    else:
        raise ValueError("kind must be depth or width")
    parent_params = count_parameters(parent)
    grown_params = count_parameters(grown)
    check("parameter_count_grew", "MEASURED", grown_params > parent_params,
          "parent=%d grown=%d added=%d" % (parent_params, grown_params, grown_params - parent_params))
    return {"kind": kind, "passed": all(c["passed"] for c in checks), "checks": checks,
            "parent_params": parent_params, "grown_params": grown_params}


def parity_check(parent, grown, kind, probe, config=None, new_config=None):
    """Numeric plus structural parity proof for a grown state.

    ``probe`` is a stream vector of the parent width. For depth, every new
    block must be numerically an identity map. For width, the embedding to
    final-norm to tied-logit path and every block's FFN branch must match
    numerically (tolerance 1e-12), and the attention width lemma is reported
    STRUCTURAL: zero-padded qkv/proj plus a preserved head dimension implies
    identical attention outputs on the old dims for any input, but this
    module has no attention evaluator, so full numeric attention parity is
    NULL here and is the torch-side check's job.
    """
    report = verify_function_preserving(parent, grown, kind, config, new_config)
    checks = report["checks"]

    def check(name, status, passed, detail):
        checks.append({"name": name, "status": status, "passed": bool(passed), "detail": detail})

    if kind == "depth":
        parent_idx = block_indices(parent)
        grown_idx = block_indices(grown)
        new_blocks = [i for i in grown_idx if i not in parent_idx]
        bad = [i for i in new_blocks if not new_block_is_identity(grown, i, probe)]
        check("new_blocks_numeric_identity", "MEASURED", not bad,
              "non-identity blocks=%s" % (bad or "none"))
    elif kind == "width":
        if config is None or new_config is None:
            raise ValueError("width parity needs config and new_config")
        d_old = config["d_model"]
        d_new = new_config["d_model"]
        if len(probe) != d_old:
            raise ValueError("probe must have the parent width")
        padded = list(probe) + [0.0] * (d_new - d_old)
        parent_logits = logits_path(parent, probe)
        grown_logits = logits_path(grown, padded)
        diff = max(abs(a - b) for a, b in zip(parent_logits, grown_logits))
        check("logits_path_numeric_parity", "MEASURED", diff <= 1e-12,
              "max_abs_logit_diff=%.3g" % diff)
        worst = 0.0
        for i in block_indices(parent):
            parent_branch = ffn_branch(extract_block(parent, i), probe)
            grown_branch = ffn_branch(extract_block(grown, i), padded)
            old_part = grown_branch[:d_old]
            worst = max(worst, max(abs(a - b) for a, b in zip(parent_branch, old_part)))
            if any(v != 0.0 for v in grown_branch[d_old:]):
                worst = float("inf")
        check("ffn_branch_numeric_parity", "MEASURED", worst <= 1e-12,
              "max_abs_ffn_diff=%.3g" % worst)
        check("attention_width_parity_by_padding", "STRUCTURAL", True,
              "zero-padded qkv/proj plus preserved head_dim; numeric attention parity is NULL here")
    else:
        raise ValueError("kind must be depth or width")
    report["passed"] = all(c["passed"] for c in checks)
    return report


def _load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _dump_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic function-preserving checkpoint growth.")
    sub = parser.add_subparsers(dest="command", required=True)
    count_p = sub.add_parser("count", help="Count parameters of a state JSON file.")
    count_p.add_argument("state")
    depth_p = sub.add_parser("grow-depth", help="Append identity blocks.")
    depth_p.add_argument("state")
    depth_p.add_argument("out")
    depth_p.add_argument("--add", type=int, required=True)
    width_p = sub.add_parser("grow-width", help="Widen the residual stream.")
    width_p.add_argument("state")
    width_p.add_argument("config")
    width_p.add_argument("out")
    width_p.add_argument("--new-d-model", type=int, required=True)
    width_p.add_argument("--new-n-heads", type=int, default=None)
    width_p.add_argument("--out-config", default=None)
    verify_p = sub.add_parser("verify", help="Parity-check a grown state against its parent.")
    verify_p.add_argument("parent")
    verify_p.add_argument("grown")
    verify_p.add_argument("--kind", choices=("depth", "width"), required=True)
    verify_p.add_argument("--probe", default=None, help="JSON list probe vector; defaults to ones.")
    verify_p.add_argument("--config", default=None)
    verify_p.add_argument("--new-config", default=None)
    args = parser.parse_args(argv)
    if args.command == "count":
        print(json.dumps({"params": count_parameters(_load_json(args.state))}))
        return 0
    if args.command == "grow-depth":
        grown, report = grow_depth(_load_json(args.state), args.add)
        _dump_json(args.out, grown)
        print(json.dumps(report, sort_keys=True))
        return 0
    if args.command == "grow-width":
        state = _load_json(args.state)
        config = validate_config(_load_json(args.config))
        grown, new_config, report = grow_width(state, config, args.new_d_model, args.new_n_heads)
        _dump_json(args.out, grown)
        if args.out_config:
            _dump_json(args.out_config, new_config)
        print(json.dumps(report, sort_keys=True))
        return 0
    if args.command == "verify":
        parent = _load_json(args.parent)
        grown = _load_json(args.grown)
        config = validate_config(_load_json(args.config)) if args.config else None
        new_config = validate_config(_load_json(args.new_config)) if args.new_config else None
        if args.probe is None:
            probe = [1.0] * (config["d_model"] if config else len(parent["norm.weight"]))
        else:
            probe = _load_json(args.probe)
        report = parity_check(parent, grown, args.kind, probe, config, new_config)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["passed"] else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
