"""Hash-bound reply-only examples, with no padding or prompt loss."""
import json
from pathlib import Path
import torch
from rawrphos.data.corpus import canonical, sha
from rawrphos.inference.chat import format_chat


def encode_example(row, tokenizer, max_seq_len):
    prefix = tokenizer.encode(format_chat(row['messages']), add_bos=True)
    reply = row['reply']
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError('empty reply')
    answer = tokenizer.encode(' ' + reply, add_eos=True)
    ids = prefix + answer
    if len(ids) - 1 > max_seq_len:
        raise ValueError('example exceeds sequence length; never truncate answer or EOS')
    labels = [-100] * len(prefix) + answer
    return torch.tensor(ids[:-1], dtype=torch.long), torch.tensor(labels[1:], dtype=torch.long)


def collate(examples, indices):
    selected = [examples[i] for i in indices]
    size = max(len(x) for x, _ in selected)
    x = torch.zeros((len(selected), size), dtype=torch.long)
    y = torch.full_like(x, -100)
    for i, (inputs, targets) in enumerate(selected):
        x[i, :len(inputs)] = inputs
        y[i, :len(targets)] = targets
    return x, y


def write_dataset(path, train, validation, provenance):
    path = Path(path)
    if path.exists():
        raise FileExistsError('dataset is immutable')
    # Identity ignores provenance so duplicate text from different sources
    # cannot silently cross the boundary.
    def identity(r): return sha(canonical({'messages': r['messages'], 'reply': r['reply']}))
    if {identity(r) for r in train} & {identity(r) for r in validation}:
        raise ValueError('training/validation overlap')
    if not train or not validation: raise ValueError('empty split')
    path.mkdir(parents=True)
    manifest = {'schema': 'rawrphos-conversation-data-v1', 'provenance': provenance, 'counts': {}, 'files': {}}
    for name, rows in [('train', train), ('validation', validation)]:
        raw = b''.join(canonical(r) + b'\n' for r in rows)
        (path / (name + '.jsonl')).write_bytes(raw)
        manifest['files'][name + '.jsonl'] = sha(raw)
        manifest['counts'][name] = len(rows)
    manifest['dataset_sha256'] = sha(canonical(manifest))
    (path / 'manifest.json').write_bytes(canonical(manifest))
    return manifest


def load_dataset(path):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    unsigned = dict(manifest); digest = unsigned.pop('dataset_sha256')
    if sha(canonical(unsigned)) != digest: raise ValueError('dataset manifest hash mismatch')
    result = {'manifest': manifest}
    for split in ('train', 'validation'):
        raw = (path / (split + '.jsonl')).read_bytes()
        if sha(raw) != manifest['files'][split + '.jsonl']: raise ValueError('dataset file hash mismatch')
        result[split] = [json.loads(line) for line in raw.splitlines()]
    return result
