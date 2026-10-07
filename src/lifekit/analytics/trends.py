"""Trend calculations for mood and habits."""

from datetime import date, timedelta

from lifekit.storage.database import Database


def mood_trend(db: Database, days: int = 7) -> list[tuple[date, float | None]]:
    """Calculate mood trend over the specified number of days.

    Returns:
        List of (date, average_mood) tuples. Mood is None if no entries that day.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    result = db.conn.execute(
        """
        SELECT DATE(created_at) as day, AVG(mood) as avg_mood
        FROM journal_entries
        WHERE DATE(created_at) >= ? AND mood IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY day ASC
        """,
        [start_date.isoformat()],
    ).fetchall()

    mood_by_day = {}
    for row in result:
        day = row[0]
        if isinstance(day, str):
            day = date.fromisoformat(day)
        mood_by_day[day] = round(row[1], 1) if row[1] is not None else None

    trend = []
    current = start_date
    while current <= end_date:
        trend.append((current, mood_by_day.get(current)))
        current += timedelta(days=1)

    return trend


def habit_completion_trend(db: Database, habit_id: str, days: int = 30) -> list[tuple[date, bool]]:
    """Calculate habit completion trend over the specified number of days.

    Returns:
        List of (date, completed) tuples.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    result = db.conn.execute(
        """
        SELECT DATE(completed_at) as day, MAX(completed) as completed
        FROM habit_logs
        WHERE habit_id = ? AND DATE(completed_at) >= ?
        GROUP BY DATE(completed_at)
        """,
        [habit_id, start_date.isoformat()],
    ).fetchall()

    completed_days = set()
    for row in result:
        day = row[0]
        if isinstance(day, str):
            day = date.fromisoformat(day)
        if row[1]:
            completed_days.add(day)

    trend = []
    current = start_date
    while current <= end_date:
        trend.append((current, current in completed_days))
        current += timedelta(days=1)

    return trend
