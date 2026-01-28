"""Streak calculations for habits."""

from datetime import date, timedelta

from lifekit.storage.database import Database


def calculate_streak(db: Database, habit_id: str) -> dict:
    """Calculate streak statistics for a habit.

    Returns:
        dict with current_streak, longest_streak, completion_rate, total_logs
    """
    result = db.conn.execute(
        """
        SELECT DATE(completed_at) as day
        FROM habit_logs
        WHERE habit_id = ? AND completed = true
        ORDER BY day ASC
        """,
        [habit_id],
    ).fetchall()

    if not result:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "completion_rate": 0.0,
            "total_logs": 0,
        }

    days = [row[0] for row in result]
    if isinstance(days[0], str):
        days = [date.fromisoformat(d) for d in days]

    total_logs = len(days)
    unique_days = sorted(set(days))

    if not unique_days:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "completion_rate": 0.0,
            "total_logs": total_logs,
        }

    streaks = []
    current = [unique_days[0]]

    for i in range(1, len(unique_days)):
        if unique_days[i] - unique_days[i - 1] == timedelta(days=1):
            current.append(unique_days[i])
        else:
            streaks.append(current)
            current = [unique_days[i]]
    streaks.append(current)

    longest_streak = max(len(s) for s in streaks)

    today = date.today()
    yesterday = today - timedelta(days=1)

    if streaks[-1][-1] == today or streaks[-1][-1] == yesterday:
        current_streak = len(streaks[-1])
    else:
        current_streak = 0

    habit_created = db.conn.execute(
        "SELECT created_at FROM habits WHERE habit_id = ?", [habit_id]
    ).fetchone()

    if habit_created:
        created_date = habit_created[0]
        if isinstance(created_date, str):
            created_date = date.fromisoformat(created_date[:10])
        elif hasattr(created_date, "date"):
            created_date = created_date.date()

        days_since_created = (today - created_date).days + 1
        if days_since_created > 0:
            completion_rate = (len(unique_days) / days_since_created) * 100
        else:
            completion_rate = 0.0
    else:
        completion_rate = 0.0

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "completion_rate": round(completion_rate, 1),
        "total_logs": total_logs,
    }
