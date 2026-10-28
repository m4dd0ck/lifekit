"""Correlation analysis between habits and mood."""

from lifekit.storage.database import Database


def mood_habit_correlation(db: Database, habit_id: str) -> dict:
    """Calculate correlation between habit completion and mood.

    Compares average mood on days when habit was completed vs not completed.

    Returns:
        dict with avg_mood_with_habit, avg_mood_without_habit, difference, sample_size
    """
    result = db.conn.execute(
        """
        WITH habit_days AS (
            SELECT DISTINCT DATE(completed_at) as day
            FROM habit_logs
            WHERE habit_id = ? AND completed = true
        ),
        daily_mood AS (
            SELECT DATE(created_at) as day, AVG(mood) as avg_mood
            FROM journal_entries
            WHERE mood IS NOT NULL
            GROUP BY DATE(created_at)
        )
        SELECT
            dm.day,
            dm.avg_mood,
            CASE WHEN hd.day IS NOT NULL THEN 1 ELSE 0 END as habit_done
        FROM daily_mood dm
        LEFT JOIN habit_days hd ON dm.day = hd.day
        """,
        [habit_id],
    ).fetchall()

    if not result:
        return {
            "avg_mood_with_habit": None,
            "avg_mood_without_habit": None,
            "difference": None,
            "sample_size": 0,
        }

    with_habit = []
    without_habit = []

    for row in result:
        mood = row[1]
        habit_done = row[2]
        if habit_done:
            with_habit.append(mood)
        else:
            without_habit.append(mood)

    avg_with = sum(with_habit) / len(with_habit) if with_habit else None
    avg_without = sum(without_habit) / len(without_habit) if without_habit else None

    if avg_with is not None and avg_without is not None:
        difference = round(avg_with - avg_without, 2)
    else:
        difference = None

    return {
        "avg_mood_with_habit": round(avg_with, 2) if avg_with else None,
        "avg_mood_without_habit": round(avg_without, 2) if avg_without else None,
        "difference": difference,
        "sample_size": len(result),
    }


def chronotype_analysis(db: Database, habit_id: str) -> dict:
    """Analyze what time of day habits are most successfully completed.

    Returns:
        dict with best_hour, hour_distribution (dict of hour -> count)
    """
    result = db.conn.execute(
        """
        SELECT EXTRACT(HOUR FROM completed_at) as hour, COUNT(*) as count
        FROM habit_logs
        WHERE habit_id = ? AND completed = true
        GROUP BY EXTRACT(HOUR FROM completed_at)
        ORDER BY count DESC
        """,
        [habit_id],
    ).fetchall()

    if not result:
        return {
            "best_hour": None,
            "hour_distribution": {},
        }

    distribution = {int(row[0]): row[1] for row in result}
    best_hour = int(result[0][0])

    return {
        "best_hour": best_hour,
        "hour_distribution": distribution,
    }
