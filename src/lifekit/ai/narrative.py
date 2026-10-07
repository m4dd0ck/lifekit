"""AI-powered weekly narrative generation."""

import os
from datetime import date

from anthropic import Anthropic

from lifekit.storage.database import Database


def _format_habits(habits: list[dict], logs: dict[str, list[dict]]) -> str:
    """Format habit data for the prompt."""
    if not habits:
        return "No habits tracked yet."

    lines = []
    for habit in habits:
        habit_logs = logs.get(habit["habit_id"], [])
        completed_count = len([log for log in habit_logs if log.get("completed", True)])
        lines.append(f"- {habit['name']}: completed {completed_count} times this week")

        avg_mood = [log["mood_after"] for log in habit_logs if log.get("mood_after") is not None]
        if avg_mood:
            lines.append(f"  Average mood after: {sum(avg_mood) / len(avg_mood):.1f}/5")

    return "\n".join(lines)


def _format_journal(entries: list[dict]) -> str:
    """Format journal entries for the prompt."""
    if not entries:
        return "No journal entries this week."

    lines = []
    for entry in entries[:5]:
        raw = entry["content"]
        content = raw[:200] + "..." if len(raw) > 200 else raw
        mood_str = f" (mood: {entry['mood']}/10)" if entry.get("mood") else ""
        lines.append(f"- {content}{mood_str}")

    if len(entries) > 5:
        lines.append(f"  ...and {len(entries) - 5} more entries")

    return "\n".join(lines)


def _format_mood_trend(trend: list[tuple[date, float | None]]) -> str:
    """Format mood trend for the prompt."""
    valid_moods = [(d, m) for d, m in trend if m is not None]
    if not valid_moods:
        return "No mood data recorded."

    avg = sum(m for _, m in valid_moods) / len(valid_moods)
    lines = [f"Average mood: {avg:.1f}/10"]

    if len(valid_moods) >= 2:
        first_half = valid_moods[: len(valid_moods) // 2]
        second_half = valid_moods[len(valid_moods) // 2 :]
        first_avg = sum(m for _, m in first_half) / len(first_half)
        second_avg = sum(m for _, m in second_half) / len(second_half)

        if second_avg > first_avg + 0.5:
            lines.append("Trend: improving")
        elif second_avg < first_avg - 0.5:
            lines.append("Trend: declining")
        else:
            lines.append("Trend: stable")

    return "\n".join(lines)


def generate_weekly_narrative(
    db: Database,
    habits: list[dict],
    habit_logs: dict[str, list[dict]],
    journal_entries: list[dict],
    mood_trend: list[tuple[date, float | None]],
) -> str:
    """Generate AI narrative of the week using Claude API.

    Args:
        db: Database instance (not used directly, kept for consistency)
        habits: List of habit dicts
        habit_logs: Dict mapping habit_id to list of log dicts
        journal_entries: List of journal entry dicts
        mood_trend: List of (date, mood) tuples

    Returns:
        Generated narrative string
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "Weekly narrative generation requires an ANTHROPIC_API_KEY environment variable. "
            "Set it to enable AI-powered summaries."
        )

    client = Anthropic()

    prompt = f"""You are a supportive personal coach reviewing someone's week of personal data.

Here's their data:

HABITS TRACKED:
{_format_habits(habits, habit_logs)}

JOURNAL EXCERPTS:
{_format_journal(journal_entries)}

MOOD TREND (1-10 scale):
{_format_mood_trend(mood_trend)}

Write a 2-3 paragraph narrative summary of their week. Be:
- Warm but not saccharine
- Observational, noting patterns you see
- Forward-looking with gentle suggestions
- Never judgmental about missed habits or low moods

Do NOT use phrases like "great job", "amazing work", "you're doing great", or similar.
Just observe patterns and reflect thoughtfully. Focus on what the data shows."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text_block = response.content[0]
    if hasattr(text_block, "text"):
        return text_block.text
    return str(text_block)
