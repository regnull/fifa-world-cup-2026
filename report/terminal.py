from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from tournament.simulator import SimulationResult
from scrape.models import TeamStanding

console = Console()


def render_report(
    standings: list[TeamStanding],
    elo_map: dict[str, float],
    result: SimulationResult,
    n_sims: int,
) -> None:
    _render_standings(standings)
    _render_championship_table(result, n_sims, elo_map)
    _render_top_finals(result, n_sims)
    _render_implied_odds(result, n_sims)
    _render_footer(n_sims)


def _render_standings(standings: list[TeamStanding]) -> None:
    groups: dict[str, list[TeamStanding]] = {}
    for s in standings:
        groups.setdefault(s.group, []).append(s)

    for letter in sorted(groups.keys()):
        group = sorted(groups[letter], key=lambda s: (-s.points, -s.gd, -s.gf))
        table = Table(title=f"Group {letter}", box=box.SIMPLE_HEAVY,
                      show_header=True, header_style="bold cyan")
        for col in ["Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]:
            table.add_column(col, justify="right" if col != "Team" else "left")
        for i, s in enumerate(group):
            style = "green" if i < 2 else ("dim" if i == 3 else "")
            table.add_row(
                s.team, str(s.played), str(s.won), str(s.drawn), str(s.lost),
                str(s.gf), str(s.ga), str(s.gd), str(s.points),
                style=style,
            )
        console.print(table)


def _render_championship_table(
    result: SimulationResult,
    n_sims: int,
    elo_map: dict[str, float] | None = None,
) -> None:
    table = Table(title="Championship Probabilities", box=box.ROUNDED,
                  header_style="bold magenta")
    table.add_column("Team", style="bold", min_width=20)
    table.add_column("Elo", justify="right")
    table.add_column("Champion", justify="right")
    table.add_column("", min_width=22)
    table.add_column("Finalist", justify="right")
    table.add_column("Semi", justify="right")
    table.add_column("Quarter", justify="right")
    table.add_column("R16", justify="right")

    top_teams = [t for t, _ in result.champion.most_common(16)]

    for team in top_teams:
        p_champ = result.champion[team] / n_sims
        p_final = (result.champion[team] + result.finalist[team]) / n_sims
        p_semi = (result.champion[team] + result.finalist[team] +
                  result.semi_finalist[team]) / n_sims
        p_qf = p_semi + result.quarter_finalist[team] / n_sims
        p_r16 = p_qf + result.r16[team] / n_sims

        bar_len = int(p_champ * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        colour = "gold1" if p_champ > 0.15 else ("yellow" if p_champ > 0.05 else "white")

        elo_val = elo_map.get(team) if elo_map else None
        elo_str = f"{elo_val:.0f}" if elo_val is not None else "—"

        table.add_row(
            team,
            elo_str,
            f"[{colour}]{p_champ:.1%}[/{colour}]",
            f"[dim]{bar}[/dim]",
            f"{p_final:.1%}",
            f"{p_semi:.1%}",
            f"{p_qf:.1%}",
            f"{p_r16:.1%}",
        )

    console.print(table)


def _render_top_finals(result: SimulationResult, n_sims: int) -> None:
    # Compute joint finalist probabilities
    finalists = list(result.champion.most_common(8))
    pairs: Counter = Counter()
    top_teams = [t for t, _ in finalists]

    for i, t1 in enumerate(top_teams):
        for t2 in top_teams[i + 1:]:
            p1_final = (result.champion[t1] + result.finalist[t1]) / n_sims
            p2_final = (result.champion[t2] + result.finalist[t2]) / n_sims
            pairs[(t1, t2)] = p1_final * p2_final

    table = Table(title="Most Likely Finals", box=box.SIMPLE)
    table.add_column("Match", style="bold")
    table.add_column("Probability", justify="right")

    for (t1, t2), prob in pairs.most_common(5):
        table.add_row(f"{t1} vs {t2}", f"{prob:.1%}")

    console.print(table)


def _render_implied_odds(result: SimulationResult, n_sims: int) -> None:
    table = Table(title="Implied Decimal Odds (to Win)", box=box.SIMPLE)
    table.add_column("Team", style="bold")
    table.add_column("Model Probability", justify="right")
    table.add_column("Implied Odds", justify="right")

    for team, count in result.champion.most_common(10):
        p = count / n_sims
        odds = round(1.0 / p, 2) if p > 0 else 999.0
        table.add_row(team, f"{p:.1%}", f"{odds:.2f}")

    console.print(table)


def _render_footer(n_sims: int) -> None:
    console.print(Panel(
        Text(f"Based on {n_sims:,} Monte Carlo simulations | "
             "Data: ESPN · eloratings.net · DraftKings (via ESPN)", justify="center"),
        style="dim",
    ))
