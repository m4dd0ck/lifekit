"""Tests for Lifekit CLI."""

import os
import tempfile
import warnings

import pytest
from click.testing import Result
from typer.testing import CliRunner

from lifekit.cli.main import app

runner = CliRunner()


@pytest.fixture
def temp_db() -> str:
    """Create a temporary database path (file doesn't exist yet)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)  # Remove the file so DuckDB can create it fresh
    return path


class TestHabitCommands:
    def test_habit_add(self, temp_db: str) -> None:
        result = runner.invoke(
            app,
            ["habit", "add", "Test habit", "--why", "Testing", "-d", temp_db],
        )
        assert result.exit_code == 0
        assert "Created habit" in result.stdout

    def test_habit_list_empty(self, temp_db: str) -> None:
        result = runner.invoke(app, ["habit", "list", "-d", temp_db])
        assert result.exit_code == 0
        assert "No habits yet" in result.stdout

    def test_habit_list_with_data(self, temp_db: str) -> None:
        runner.invoke(app, ["habit", "add", "List test", "-d", temp_db])
        result = runner.invoke(app, ["habit", "list", "-d", temp_db])

        assert result.exit_code == 0
        assert "List test" in result.stdout

    def test_habit_log(self, temp_db: str) -> None:
        runner.invoke(app, ["habit", "add", "Log test", "-d", temp_db])
        result = runner.invoke(
            app,
            ["habit", "log", "Log test", "--mood", "4", "-d", temp_db],
        )

        assert result.exit_code == 0
        assert "Logged" in result.stdout

    def test_habit_log_not_found(self, temp_db: str) -> None:
        result = runner.invoke(
            app,
            ["habit", "log", "Nonexistent", "-d", temp_db],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_habit_stats(self, temp_db: str) -> None:
        runner.invoke(app, ["habit", "add", "Stats test", "-d", temp_db])
        runner.invoke(app, ["habit", "log", "Stats test", "-d", temp_db])

        result = runner.invoke(app, ["habit", "stats", "Stats test", "-d", temp_db])

        assert result.exit_code == 0
        assert "Current streak" in result.stdout

    def test_habit_archive(self, temp_db: str) -> None:
        runner.invoke(app, ["habit", "add", "Archive test", "-d", temp_db])
        result = runner.invoke(app, ["habit", "archive", "Archive test", "-d", temp_db])

        assert result.exit_code == 0
        assert "Archived" in result.stdout


class TestJournalCommands:
    def test_journal_write(self, temp_db: str) -> None:
        result = runner.invoke(
            app,
            ["journal", "write", "Test entry", "--mood", "7", "-d", temp_db],
        )
        assert result.exit_code == 0
        assert "saved" in result.stdout

    def test_journal_list_empty(self, temp_db: str) -> None:
        result = runner.invoke(app, ["journal", "list", "-d", temp_db])
        assert result.exit_code == 0
        assert "No journal entries" in result.stdout

    def test_journal_list_with_data(self, temp_db: str) -> None:
        runner.invoke(app, ["journal", "write", "List test entry", "-d", temp_db])
        result = runner.invoke(app, ["journal", "list", "-d", temp_db])

        assert result.exit_code == 0
        assert "List test entry" in result.stdout

    def test_journal_prompt(self, temp_db: str) -> None:
        result = runner.invoke(app, ["journal", "prompt", "-d", temp_db])
        assert result.exit_code == 0
        # Should show a prompt

    def test_journal_search(self, temp_db: str) -> None:
        runner.invoke(app, ["journal", "write", "Unique search term xyz", "-d", temp_db])
        result = runner.invoke(app, ["journal", "search", "xyz", "-d", temp_db])

        assert result.exit_code == 0
        assert "xyz" in result.stdout

    def test_journal_search_no_results(self, temp_db: str) -> None:
        result = runner.invoke(app, ["journal", "search", "nonexistent123", "-d", temp_db])
        assert result.exit_code == 0
        assert "No entries matching" in result.stdout


class TestGoalCommands:
    def test_goal_add(self, temp_db: str) -> None:
        result = runner.invoke(
            app,
            ["goal", "add", "Run a 5k", "--deadline", "2026-04-01", "-d", temp_db],
        )
        assert result.exit_code == 0
        assert "Created goal" in result.stdout

    def test_goal_list_empty(self, temp_db: str) -> None:
        result = runner.invoke(app, ["goal", "list", "-d", temp_db])
        assert result.exit_code == 0
        assert "No goals yet" in result.stdout

    def test_goal_list_with_data(self, temp_db: str) -> None:
        runner.invoke(app, ["goal", "add", "List goal test", "-d", temp_db])
        result = runner.invoke(app, ["goal", "list", "-d", temp_db])

        assert result.exit_code == 0
        assert "List goal test" in result.stdout

    def test_goal_milestone(self, temp_db: str) -> None:
        runner.invoke(app, ["goal", "add", "Milestone test", "-d", temp_db])
        result = runner.invoke(
            app,
            ["goal", "milestone", "Milestone test", "First step", "-d", temp_db],
        )

        assert result.exit_code == 0
        assert "Added milestone" in result.stdout

    def test_goal_progress(self, temp_db: str) -> None:
        runner.invoke(app, ["goal", "add", "Progress test", "-d", temp_db])
        result = runner.invoke(
            app,
            ["goal", "progress", "Progress test", "50", "-d", temp_db],
        )

        assert result.exit_code == 0
        assert "Updated progress" in result.stdout


class TestStatsCommands:
    def test_stats_overview(self, temp_db: str) -> None:
        result = runner.invoke(app, ["stats", "-d", temp_db])
        assert result.exit_code == 0
        assert "Overview" in result.stdout

    def test_stats_mood(self, temp_db: str) -> None:
        result = runner.invoke(app, ["stats", "mood", "-d", temp_db])
        assert result.exit_code == 0
        assert "Mood Trend" in result.stdout

    def test_stats_habits(self, temp_db: str) -> None:
        runner.invoke(app, ["habit", "add", "Stats habit", "-d", temp_db])
        result = runner.invoke(app, ["stats", "habits", "-d", temp_db])

        assert result.exit_code == 0

    def test_stats_correlations(self, temp_db: str) -> None:
        result = runner.invoke(app, ["stats", "correlations", "-d", temp_db])
        assert result.exit_code == 0


class TestLetterCommand:
    def test_letter_with_why(self, temp_db: str) -> None:
        runner.invoke(
            app,
            ["habit", "add", "Letter test", "--why", "For my health", "-d", temp_db],
        )
        result = runner.invoke(app, ["letter", "Letter test", "-d", temp_db])

        assert result.exit_code == 0
        assert "For my health" in result.stdout

    def test_letter_without_why(self, temp_db: str) -> None:
        runner.invoke(app, ["habit", "add", "No letter", "-d", temp_db])
        result = runner.invoke(app, ["letter", "No letter", "-d", temp_db])

        assert result.exit_code == 0
        assert "No letter was written" in result.stdout

    def test_letter_not_found(self, temp_db: str) -> None:
        result = runner.invoke(app, ["letter", "Nonexistent", "-d", temp_db])
        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestShortOptionCollision:
    """The global -d (db path) must not clash with sub-command short flags."""

    @staticmethod
    def _invoke_without_click_warnings(args: list[str]) -> Result:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = runner.invoke(app, args)
        duplicates = [w for w in caught if "used more than once" in str(w.message)]
        assert duplicates == [], [str(w.message) for w in duplicates]
        return result

    def test_goal_add_deadline_and_db_path_both_apply(self, temp_db: str) -> None:
        result = self._invoke_without_click_warnings(
            ["goal", "add", "Collision goal", "--deadline", "2026-04-01", "-d", temp_db]
        )
        assert result.exit_code == 0, result.output

        listing = runner.invoke(app, ["goal", "list", "-d", temp_db])
        assert "Collision goal" in listing.stdout
        assert "2026-04-01" in listing.stdout

    def test_stats_mood_days_and_db_path_both_apply(self, temp_db: str) -> None:
        result = self._invoke_without_click_warnings(
            ["stats", "mood", "--days", "3", "-d", temp_db]
        )
        assert result.exit_code == 0, result.output
        assert "Mood Trend (3 days)" in result.stdout

    def test_narrative_help_has_no_duplicate_short_flag(self) -> None:
        result = self._invoke_without_click_warnings(["narrative", "--help"])
        assert result.exit_code == 0
        assert result.stdout.count(" -d ") == 1
