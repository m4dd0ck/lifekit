"""Tests for AI narrative generation."""

from unittest.mock import MagicMock, patch

import pytest

from lifekit.ai import narrative
from lifekit.storage.database import Database


def _generate(db: Database) -> str:
    return narrative.generate_weekly_narrative(
        db=db, habits=[], habit_logs={}, journal_entries=[], mood_trend=[]
    )


def test_default_model_is_current_sonnet() -> None:
    assert narrative.DEFAULT_MODEL == "claude-sonnet-5-5"


def test_without_api_key_returns_setup_message(
    db: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert "ANTHROPIC_API_KEY" in _generate(db)


def test_request_uses_default_model(db: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(type="thinking", thinking=""),
        MagicMock(type="text", text="A quiet week."),
    ]

    with patch.object(narrative, "Anthropic", return_value=client):
        text = _generate(db)

    assert text == "A quiet week."
    assert client.messages.create.call_args.kwargs["model"] == narrative.DEFAULT_MODEL
