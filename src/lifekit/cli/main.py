"""CLI for Lifekit - personal management system."""

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lifekit.ai.narrative import generate_weekly_narrative
from lifekit.analytics import (
    calculate_streak,
    chronotype_analysis,
    mood_habit_correlation,
    mood_trend,
)
from lifekit.analytics.correlations import get_overview_stats
from lifekit.storage.database import Database
from lifekit.storage.events import EventStore

app = typer.Typer(
    name="lk",
    help="Lifekit - Personal management CLI",
    no_args_is_help=True,
)
habit_app = typer.Typer(help="Habit tracking commands")
journal_app = typer.Typer(help="Journal commands")
goal_app = typer.Typer(help="Goal tracking commands")
stats_app = typer.Typer(help="Analytics and statistics")

app.add_typer(habit_app, name="habit")
app.add_typer(journal_app, name="journal")
app.add_typer(goal_app, name="goal")
app.add_typer(stats_app, name="stats")

console = Console()

DB_PATH_OPTION = typer.Option(
    "~/.lifekit/data.db",
    "--db-path",
    "-d",
    help="Path to database file",
)


def get_db(db_path: str) -> Database:
    path = Path(db_path).expanduser()
    return Database(path)


def get_store(db_path: str) -> EventStore:
    return EventStore(get_db(db_path))


# Habit commands


@habit_app.command("add")
def habit_add(
    name: Annotated[str, typer.Argument(help="Name of the habit")],
    why: Annotated[
        str | None, typer.Option("--why", "-w", help="Why this matters (sealed letter)")
    ] = None,
    tiny: Annotated[
        str | None, typer.Option("--tiny", "-t", help="Tiny version of the habit")
    ] = None,
    description: Annotated[str | None, typer.Option("--desc", help="Description")] = None,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Add a new habit to track."""
    store = get_store(db_path)
    store.create_habit(
        name=name,
        description=description,
        why=why,
        tiny_version=tiny,
    )
    console.print(f"[green]Created habit:[/green] {name}")
    if why:
        console.print("[dim]Sealed your letter to your future self.[/dim]")


@habit_app.command("log")
def habit_log(
    name: Annotated[str, typer.Argument(help="Name of the habit")],
    mood: Annotated[
        int | None, typer.Option("--mood", "-m", help="Mood after (1-5)", min=1, max=5)
    ] = None,
    energy: Annotated[
        int | None, typer.Option("--energy", "-e", help="Energy before (1-5)", min=1, max=5)
    ] = None,
    difficulty: Annotated[
        int | None, typer.Option("--difficulty", help="Difficulty (1-5)", min=1, max=5)
    ] = None,
    quality: Annotated[
        int | None, typer.Option("--quality", "-q", help="Quality (1-5)", min=1, max=5)
    ] = None,
    context: Annotated[str | None, typer.Option("--context", "-c", help="Context/notes")] = None,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Log a habit completion."""
    db = get_db(db_path)
    store = EventStore(db)

    habit = db.get_habit_by_name(name)
    if not habit:
        console.print(f"[red]Habit not found:[/red] {name}")
        raise typer.Exit(1)

    store.log_habit(
        habit_id=habit["habit_id"],
        mood_after=mood,
        energy_before=energy,
        difficulty=difficulty,
        quality=quality,
        context=context,
    )
    console.print(f"[green]Logged:[/green] {name}")


@habit_app.command("list")
def habit_list(
    include_archived: Annotated[
        bool, typer.Option("--archived", "-a", help="Include archived")
    ] = False,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """List all habits."""
    db = get_db(db_path)
    habits = db.get_habits(include_archived=include_archived)

    if not habits:
        console.print('[yellow]No habits yet. Add one with:[/yellow] lk habit add "Your habit"')
        return

    table = Table(title="Habits")
    table.add_column("Name", style="cyan")
    table.add_column("Created", style="dim")
    table.add_column("Streak", style="green")
    table.add_column("Status")

    for habit in habits:
        streak = calculate_streak(db, habit["habit_id"])
        created = habit["created_at"]
        if hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d")
        else:
            created = str(created)[:10]

        status = "[dim]archived[/dim]" if habit["archived_at"] else "[green]active[/green]"
        streak_str = f"{streak['current_streak']}d ({streak['completion_rate']}%)"

        table.add_row(habit["name"], created, streak_str, status)

    console.print(table)


@habit_app.command("stats")
def habit_stats(
    name: Annotated[str, typer.Argument(help="Name of the habit")],
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Show detailed stats for a habit."""
    db = get_db(db_path)
    habit = db.get_habit_by_name(name)

    if not habit:
        console.print(f"[red]Habit not found:[/red] {name}")
        raise typer.Exit(1)

    streak = calculate_streak(db, habit["habit_id"])
    chrono = chronotype_analysis(db, habit["habit_id"])
    correlation = mood_habit_correlation(db, habit["habit_id"])

    console.print(Panel(f"[bold]{habit['name']}[/bold]", subtitle=habit.get("description") or ""))

    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Metric", style="dim")
    stats_table.add_column("Value", style="bold")

    stats_table.add_row("Current streak", f"{streak['current_streak']} days")
    stats_table.add_row("Longest streak", f"{streak['longest_streak']} days")
    stats_table.add_row("Completion rate", f"{streak['completion_rate']}%")
    stats_table.add_row("Total completions", str(streak["total_logs"]))

    if chrono["best_hour"] is not None:
        stats_table.add_row("Best time", f"{chrono['best_hour']:02d}:00")

    if correlation["difference"] is not None:
        diff = correlation["difference"]
        if diff > 0:
            stats_table.add_row("Mood impact", f"+{diff} when completed")
        elif diff < 0:
            stats_table.add_row("Mood impact", f"{diff} when completed")

    console.print(stats_table)


@habit_app.command("archive")
def habit_archive(
    name: Annotated[str, typer.Argument(help="Name of the habit")],
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Archive a habit (stop tracking)."""
    db = get_db(db_path)
    store = EventStore(db)

    habit = db.get_habit_by_name(name)
    if not habit:
        console.print(f"[red]Habit not found:[/red] {name}")
        raise typer.Exit(1)

    store.archive_habit(habit["habit_id"])
    console.print(f"[yellow]Archived:[/yellow] {name}")


# Journal commands


@journal_app.command("write")
def journal_write(
    content: Annotated[str | None, typer.Argument(help="Journal content")] = None,
    mood: Annotated[
        int | None, typer.Option("--mood", "-m", help="Mood (1-10)", min=1, max=10)
    ] = None,
    energy: Annotated[
        int | None, typer.Option("--energy", "-e", help="Energy (1-5)", min=1, max=5)
    ] = None,
    gratitude: Annotated[
        str | None, typer.Option("--gratitude", "-g", help="What are you grateful for?")
    ] = None,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Write a journal entry."""
    if not content:
        content = typer.prompt("What's on your mind?")

    store = get_store(db_path)
    store.create_journal_entry(
        content=content,
        mood=mood,
        energy=energy,
        gratitude=gratitude,
    )
    console.print("[green]Journal entry saved.[/green]")


@journal_app.command("prompt")
def journal_prompt(
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Prompt category")
    ] = None,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Get a journaling prompt."""
    db = get_db(db_path)
    prompt = db.get_random_prompt(category)

    if not prompt:
        console.print("[yellow]No prompts available.[/yellow]")
        return

    console.print(Panel(prompt["text"], title=f"[dim]{prompt['category']}[/dim]"))


@journal_app.command("search")
def journal_search(
    query: Annotated[str, typer.Argument(help="Search query")],
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Search journal entries."""
    db = get_db(db_path)
    entries = db.search_journal(query)

    if not entries:
        console.print(f"[yellow]No entries matching:[/yellow] {query}")
        return

    for entry in entries:
        created = entry["created_at"]
        if hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d %H:%M")
        mood_str = f" (mood: {entry['mood']}/10)" if entry.get("mood") else ""

        console.print(f"\n[dim]{created}[/dim]{mood_str}")
        console.print(entry["content"][:300] + ("..." if len(entry["content"]) > 300 else ""))


@journal_app.command("list")
def journal_list(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of entries")] = 10,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """List recent journal entries."""
    db = get_db(db_path)
    entries = db.get_journal_entries(limit=limit)

    if not entries:
        console.print("[yellow]No journal entries yet.[/yellow]")
        return

    for entry in entries:
        created = entry["created_at"]
        if hasattr(created, "strftime"):
            created = created.strftime("%Y-%m-%d %H:%M")
        mood_str = f" [mood: {entry['mood']}/10]" if entry.get("mood") else ""

        console.print(f"\n[bold]{created}[/bold]{mood_str}")
        preview = entry["content"][:150] + ("..." if len(entry["content"]) > 150 else "")
        console.print(f"[dim]{preview}[/dim]")


# Goal commands


@goal_app.command("add")
def goal_add(
    outcome: Annotated[str, typer.Argument(help="Goal outcome (SMART format)")],
    deadline: Annotated[
        str | None, typer.Option("--deadline", "-d", help="Deadline (YYYY-MM-DD)")
    ] = None,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Add a new goal."""
    store = get_store(db_path)

    deadline_dt = None
    if deadline:
        try:
            deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
            raise typer.Exit(1)

    store.create_goal(outcome=outcome, deadline=deadline_dt)
    console.print(f"[green]Created goal:[/green] {outcome}")


@goal_app.command("milestone")
def goal_milestone(
    goal: Annotated[str, typer.Argument(help="Goal name (partial match)")],
    description: Annotated[str, typer.Argument(help="Milestone description")],
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Add a milestone to a goal."""
    db = get_db(db_path)
    store = EventStore(db)

    goal_data = db.get_goal_by_outcome(goal)
    if not goal_data:
        console.print(f"[red]Goal not found:[/red] {goal}")
        raise typer.Exit(1)

    store.add_milestone(goal_id=goal_data["goal_id"], description=description)
    console.print(f"[green]Added milestone:[/green] {description}")


@goal_app.command("progress")
def goal_progress(
    goal: Annotated[str, typer.Argument(help="Goal name (partial match)")],
    progress: Annotated[int, typer.Argument(help="Progress percentage (0-100)", min=0, max=100)],
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Update goal progress."""
    db = get_db(db_path)
    store = EventStore(db)

    goal_data = db.get_goal_by_outcome(goal)
    if not goal_data:
        console.print(f"[red]Goal not found:[/red] {goal}")
        raise typer.Exit(1)

    store.update_progress(goal_id=goal_data["goal_id"], progress=progress)
    console.print(f"[green]Updated progress:[/green] {progress}%")

    if progress >= 100:
        store.complete_goal(goal_data["goal_id"])
        console.print("[bold green]Goal achieved![/bold green]")


@goal_app.command("list")
def goal_list(
    status: Annotated[str | None, typer.Option("--status", "-s", help="Filter by status")] = None,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """List goals."""
    db = get_db(db_path)
    goals = db.get_goals(status=status)

    if not goals:
        console.print('[yellow]No goals yet. Add one with:[/yellow] lk goal add "Your goal"')
        return

    table = Table(title="Goals")
    table.add_column("Outcome", style="cyan")
    table.add_column("Progress", style="green")
    table.add_column("Deadline", style="dim")
    table.add_column("Status")

    for goal in goals:
        deadline = goal["deadline"]
        if deadline:
            if hasattr(deadline, "strftime"):
                deadline = deadline.strftime("%Y-%m-%d")
            else:
                deadline = str(deadline)[:10]
        else:
            deadline = "-"

        status_color = {
            "active": "yellow",
            "achieved": "green",
            "abandoned": "dim",
        }.get(goal["status"], "white")

        table.add_row(
            goal["outcome"][:50] + ("..." if len(goal["outcome"]) > 50 else ""),
            f"{goal['progress']}%",
            deadline,
            f"[{status_color}]{goal['status']}[/{status_color}]",
        )

    console.print(table)


# Stats commands


@stats_app.callback(invoke_without_command=True)
def stats_overview(
    ctx: typer.Context,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Show overview statistics."""
    if ctx.invoked_subcommand is not None:
        return

    db = get_db(db_path)
    stats = get_overview_stats(db)

    console.print(Panel("[bold]Lifekit Overview[/bold]"))

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Active habits", str(stats["total_habits"]))
    table.add_row("Completed today", str(stats["habits_completed_today"]))
    table.add_row("Journal entries", str(stats["total_journal_entries"]))
    table.add_row("Avg mood (7d)", str(stats["avg_mood_7d"]) if stats["avg_mood_7d"] else "-")
    table.add_row("Active goals", str(stats["active_goals"]))

    console.print(table)


@stats_app.command("mood")
def stats_mood(
    days: Annotated[int, typer.Option("--days", "-d", help="Number of days")] = 7,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Show mood trends."""
    db = get_db(db_path)
    trend = mood_trend(db, days=days)

    console.print(f"[bold]Mood Trend ({days} days)[/bold]\n")

    for day, mood_val in trend:
        day_str = day.strftime("%a %m/%d")
        if mood_val is not None:
            bar = "█" * int(mood_val) + "░" * (10 - int(mood_val))
            console.print(f"{day_str}: {bar} {mood_val:.1f}")
        else:
            console.print(f"{day_str}: [dim]no data[/dim]")


@stats_app.command("habits")
def stats_habits(
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Show habit statistics."""
    db = get_db(db_path)
    habits = db.get_habits()

    if not habits:
        console.print("[yellow]No habits to analyze.[/yellow]")
        return

    table = Table(title="Habit Statistics")
    table.add_column("Habit", style="cyan")
    table.add_column("Current", style="green")
    table.add_column("Longest", style="yellow")
    table.add_column("Rate", style="dim")

    for habit in habits:
        streak = calculate_streak(db, habit["habit_id"])
        table.add_row(
            habit["name"],
            f"{streak['current_streak']}d",
            f"{streak['longest_streak']}d",
            f"{streak['completion_rate']}%",
        )

    console.print(table)


@stats_app.command("correlations")
def stats_correlations(
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Show habit-mood correlations."""
    db = get_db(db_path)
    habits = db.get_habits()

    if not habits:
        console.print("[yellow]No habits to analyze.[/yellow]")
        return

    table = Table(title="Habit-Mood Correlations")
    table.add_column("Habit", style="cyan")
    table.add_column("Mood With", style="green")
    table.add_column("Mood Without", style="red")
    table.add_column("Impact")

    for habit in habits:
        corr = mood_habit_correlation(db, habit["habit_id"])
        if corr["sample_size"] < 3:
            continue

        avg_with = corr["avg_mood_with_habit"]
        avg_without = corr["avg_mood_without_habit"]
        with_str = f"{avg_with:.1f}" if avg_with else "-"
        without_str = f"{avg_without:.1f}" if avg_without else "-"

        if corr["difference"] is not None:
            diff = corr["difference"]
            if diff > 0.3:
                impact = f"[green]+{diff:.1f}[/green]"
            elif diff < -0.3:
                impact = f"[red]{diff:.1f}[/red]"
            else:
                impact = f"[dim]{diff:+.1f}[/dim]"
        else:
            impact = "-"

        table.add_row(habit["name"], with_str, without_str, impact)

    console.print(table)


# AI commands


@app.command("narrative")
def narrative(
    days: Annotated[int, typer.Option("--days", "-d", help="Days to summarize")] = 7,
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Generate AI weekly narrative."""
    db = get_db(db_path)

    habits = db.get_habits()
    habit_logs = {}
    for habit in habits:
        habit_logs[habit["habit_id"]] = db.get_habit_logs(habit["habit_id"], limit=days * 2)

    entries = db.get_journal_entries(limit=days * 3)
    trend = mood_trend(db, days=days)

    console.print("[dim]Generating narrative...[/dim]\n")

    narrative_text = generate_weekly_narrative(
        db=db,
        habits=habits,
        habit_logs=habit_logs,
        journal_entries=entries,
        mood_trend=trend,
    )

    console.print(Panel(narrative_text, title="Weekly Narrative"))


@app.command("letter")
def letter(
    habit_name: Annotated[str, typer.Argument(help="Name of the habit")],
    db_path: str = DB_PATH_OPTION,
) -> None:
    """Read the sealed letter for a habit."""
    db = get_db(db_path)
    habit = db.get_habit_by_name(habit_name)

    if not habit:
        console.print(f"[red]Habit not found:[/red] {habit_name}")
        raise typer.Exit(1)

    if not habit.get("why"):
        console.print("[yellow]No letter was written for this habit.[/yellow]")
        return

    console.print(
        Panel(
            habit["why"],
            title=f"[bold]Why you started: {habit['name']}[/bold]",
            subtitle="[dim]Written when you created this habit[/dim]",
        )
    )


if __name__ == "__main__":
    app()
