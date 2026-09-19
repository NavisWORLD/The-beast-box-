from pathlib import Path


def test_quantum_geometry_workflow_is_pinned_and_matched():
    path = Path('.github/workflows/d001-quantum-geometry.yml')
    assert path.exists()
    text = path.read_text(encoding='utf-8')
    assert '31911380890' in text
    assert 'd001-trained-lineage-31911380890' in text
    assert 'c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f' in text
    assert 'b414724c627300c41b099dcc6853766d08fd27a4' in text
    assert 'data/quantum_measurements_public.jsonl' in text
    assert '986b4778097affe6fbda6170e3401bb4d5ae0ff2b2eef5764b42a4a8399a3b82' in text
    assert 'materialize_d001_quantum_packets.py' in text
    assert 'run_d001_quantum_geometry.py' in text
    for arm in ('hardware', 'shuffled_hardware', 'prng', 'fixed_seed', 'neutral'):
        assert arm in text
    assert 'alignment_proven=False' in text
    assert 'actions/upload-artifact@v4' in text


def test_quantum_geometry_workflow_has_read_only_permissions():
    text = Path('.github/workflows/d001-quantum-geometry.yml').read_text(encoding='utf-8')
    assert 'contents: read' in text
    assert 'actions: read' in text
    assert 'contents: write' not in text
