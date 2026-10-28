"""Overview counts for the `lk stats` dashboard."""

from lifekit.storage.database import Database


def get_overview_stats(db: Database) -> dict:
    """Get overview statistics for dashboard."""
    habits_result = db.conn.execute(
        "SELECT COUNT(*) FROM habits WHERE archived_at IS NULL"
    ).fetchone()
    total_habits = habits_result[0] if habits_result else 0

    logs_result = db.conn.execute(
        """
        SELECT COUNT(*)
        FROM habit_logs
        WHERE DATE(completed_at) = CURRENT_DATE AND completed = true
        """
    ).fetchone()
    habits_today = logs_result[0] if logs_result else 0

    journal_result = db.conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()
    total_entries = journal_result[0] if journal_result else 0

    mood_result = db.conn.execute(
        """
        SELECT AVG(mood)
        FROM journal_entries
        WHERE mood IS NOT NULL AND DATE(created_at) >= CURRENT_DATE - INTERVAL 7 DAY
        """
    ).fetchone()
    avg_mood_7d = round(mood_result[0], 1) if mood_result and mood_result[0] else None

    goals_result = db.conn.execute("SELECT COUNT(*) FROM goals WHERE status = 'active'").fetchone()
    active_goals = goals_result[0] if goals_result else 0

    return {
        "total_habits": total_habits,
        "habits_completed_today": habits_today,
        "total_journal_entries": total_entries,
        "avg_mood_7d": avg_mood_7d,
        "active_goals": active_goals,
    }
