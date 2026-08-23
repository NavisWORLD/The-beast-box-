from scripts.import_zeref_r12_fez import load_verified_fez_block
from scripts.run_zeref_r12_reality_loop import run_once


def test_r12_script_modules_are_installable():
    assert callable(load_verified_fez_block)
    assert callable(run_once)
