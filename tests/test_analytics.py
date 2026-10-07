"""Tests for Lifekit analytics."""

from datetime import date

from lifekit.analytics import (
    calculate_streak,
    chronotype_analysis,
    habit_completion_trend,
    mood_habit_correlation,
    mood_trend,
)
from lifekit.analytics.correlations import get_overview_stats
from lifekit.storage.database import Database
from lifekit.storage.events import EventStore


class TestStreaks:
    def test_calculate_streak_empty(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Empty habit")

        streak = calculate_streak(db, habit_id)

        assert streak["current_streak"] == 0
        assert streak["longest_streak"] == 0
        assert streak["total_logs"] == 0

    def test_calculate_streak_single_log(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Single log")
        store.log_habit(habit_id)

        streak = calculate_streak(db, habit_id)

        assert streak["current_streak"] >= 0
        assert streak["longest_streak"] >= 1
        assert streak["total_logs"] == 1

    def test_calculate_streak_multiple_logs(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Multiple logs")

        for _ in range(5):
            store.log_habit(habit_id)

        streak = calculate_streak(db, habit_id)

        assert streak["total_logs"] == 5
        assert streak["longest_streak"] >= 1


class TestTrends:
    def test_mood_trend_empty(self, db: Database) -> None:
        trend = mood_trend(db, days=7)

        assert len(trend) == 7
        for day, mood_val in trend:
            assert mood_val is None

    def test_mood_trend_with_data(self, populated_db: Database) -> None:
        trend = mood_trend(populated_db, days=7)

        assert len(trend) == 7
        # Should have at least some data
        has_data = any(m is not None for _, m in trend)
        assert has_data

    def test_habit_completion_trend_empty(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Empty trend")

        trend = habit_completion_trend(db, habit_id, days=7)

        assert len(trend) == 7
        for day, completed in trend:
            assert completed is False

    def test_habit_completion_trend_with_data(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Trend test")
        store.log_habit(habit_id)

        trend = habit_completion_trend(db, habit_id, days=7)

        assert len(trend) == 7
        # Today should be completed
        today = date.today()
        today_entry = next((c for d, c in trend if d == today), None)
        assert today_entry is True


class TestCorrelations:
    def test_mood_habit_correlation_empty(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Correlation test")

        corr = mood_habit_correlation(db, habit_id)

        assert corr["sample_size"] == 0

    def test_mood_habit_correlation_with_data(self, populated_db: Database) -> None:
        habits = populated_db.get_habits()
        if habits:
            corr = mood_habit_correlation(populated_db, habits[0]["habit_id"])
            # Should have some data
            assert "avg_mood_with_habit" in corr
            assert "avg_mood_without_habit" in corr

    def test_chronotype_analysis_empty(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Chrono test")

        chrono = chronotype_analysis(db, habit_id)

        assert chrono["best_hour"] is None
        assert chrono["hour_distribution"] == {}

    def test_chronotype_analysis_with_data(self, db: Database, store: EventStore) -> None:
        habit_id = store.create_habit(name="Chrono data")
        store.log_habit(habit_id)
        store.log_habit(habit_id)

        chrono = chronotype_analysis(db, habit_id)

        assert chrono["best_hour"] is not None
        assert len(chrono["hour_distribution"]) > 0


class TestOverviewStats:
    def test_overview_stats_empty(self, db: Database) -> None:
        stats = get_overview_stats(db)

        assert stats["total_habits"] == 0
        assert stats["habits_completed_today"] == 0
        assert stats["total_journal_entries"] == 0
        assert stats["active_goals"] == 0

    def test_overview_stats_with_data(self, populated_db: Database) -> None:
        stats = get_overview_stats(populated_db)

        assert stats["total_habits"] > 0
        assert stats["total_journal_entries"] > 0
        assert stats["active_goals"] > 0
