from __future__ import annotations

import pytest

from beastbox.env_inventory import EnvironmentInventoryError, parse_env_example, scan_python_source


def test_scan_python_source_collects_literal_environment_reads() -> None:
    source = '''
import os
A = os.getenv("ALPHA")
B = os.environ.get("BETA", "safe")
C = os.environ["GAMMA"]
'''
    result = scan_python_source(source, filename="example.py")
    assert result.variables == {"ALPHA", "BETA", "GAMMA"}
    assert result.dynamic_reads == []


def test_scan_python_source_rejects_dynamic_environment_names() -> None:
    source = '''
import os
name = "ALPHA"
value = os.getenv(name)
'''
    with pytest.raises(EnvironmentInventoryError, match="dynamic environment variable read"):
        scan_python_source(source, filename="dynamic.py")


def test_scan_python_source_records_explicit_dynamic_secret_reference_contract() -> None:
    source = '''
import os
__beastbox_dynamic_env_contract__ = "secret-reference-v1"
name = "USER_SELECTED_SECRET_NAME"
value = os.environ.get(name)
'''
    result = scan_python_source(source, filename="provider.py")
    assert result.variables == set()
    assert result.dynamic_reads == ["provider.py:5:secret-reference-v1"]


def test_parse_env_example_requires_unique_assignment_keys() -> None:
    content = '''
# Runtime
ALPHA=
BETA=safe
'''
    assert parse_env_example(content) == {"ALPHA", "BETA"}

    with pytest.raises(EnvironmentInventoryError, match="duplicate"):
        parse_env_example("ALPHA=\nALPHA=other\n")
