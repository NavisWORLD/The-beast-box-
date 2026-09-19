import json
import logging

from beastbox.logging_config import configure_logging, redact_mapping


def test_redact_mapping_masks_secrets_recursively():
    assert redact_mapping({
        "IBM_QUANTUM_TOKEN": "secret",
        "event": "boot",
        "nested": {"api_key": "also-secret", "safe": 1},
    }) == {
        "IBM_QUANTUM_TOKEN": "***REDACTED***",
        "event": "boot",
        "nested": {"api_key": "***REDACTED***", "safe": 1},
    }


def test_json_logging_emits_stable_event(capsys):
    logger = configure_logging(json_output=True, level=logging.INFO)
    logger.info("starter_ready", extra={"event_data": {"backend": "ollama", "token": "secret"}})
    record = json.loads(capsys.readouterr().err.strip())
    assert record["message"] == "starter_ready"
    assert record["event_data"]["backend"] == "ollama"
    assert record["event_data"]["token"] == "***REDACTED***"
    assert record["level"] == "INFO"
    assert record["logger"] == "beastbox"


def test_human_logging_remains_readable(capsys):
    logger = configure_logging(json_output=False, level=logging.INFO)
    logger.info("ready")
    assert capsys.readouterr().err.strip() == "INFO beastbox ready"
