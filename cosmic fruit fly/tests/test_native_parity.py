"""Native parity gate; C++ and Rust are optional when compilers are unavailable."""
from __future__ import annotations
import json,shutil,subprocess,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parents[1]
FIXTURE=HERE/'native'/'fixtures'/'step4.txt'
sys.path.insert(0,str(HERE/'native'))
from reference import compute

def assert_parity(result):
    expected=compute(FIXTURE)
    for field,n in (("state",42),("dyn12",12)):
        assert len(result[field])==n
        assert max(abs(a-b) for a,b in zip(expected[field],result[field]))<1e-12

def test_reference_determinism():
    assert compute(FIXTURE)==compute(FIXTURE)

def test_cpp_parity(tmp_path):
    if not shutil.which('g++'):pytest.skip('g++ not installed')
    executable=tmp_path/'fly_neural_step'
    subprocess.run(['g++','-O2','-std=c++17',str(HERE/'native'/'cpp'/'neural_step.cpp'),'-o',str(executable)],check=True)
    result=json.loads(subprocess.check_output([str(executable),str(FIXTURE)],text=True))
    assert_parity(result)

def test_rust_parity(tmp_path):
    if not shutil.which('cargo'):pytest.skip('cargo not installed')
    manifest=HERE/'native'/'rust'/'Cargo.toml'
    subprocess.run(['cargo','build','--offline','--release','--manifest-path',str(manifest),'--target-dir',str(tmp_path/'target')],check=True)
    exe=tmp_path/'target'/'release'/('cosmic_fruit_fly_neural_step.exe' if sys.platform=='win32' else 'cosmic_fruit_fly_neural_step')
    assert_parity(json.loads(subprocess.check_output([str(exe),str(FIXTURE)],text=True)))
