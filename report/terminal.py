from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich import box
from tournament.simulator import SimulationResult, TournamentTrace
from scrape.models import TeamStanding, MatchOdds
from model.probability import elo_to_probs, odds_to_probs

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
    table.add_column("Final", justify="right")
    table.add_column("SF", justify="right")
    table.add_column("QF", justify="right")
    table.add_column("R16", justify="right")

    top_teams = [t for t, _ in result.champion.most_common(16)]

    for team in top_teams:
        p_champ = result.champion[team] / n_sims
        p_final = (result.champion[team] + result.finalist[team]) / n_sims
        p_semi = (result.champion[team] + result.finalist[team] +
                  result.semi_finalist[team]) / n_sims
        p_qf = p_semi + result.quarter_finalist[team] / n_sims
        p_r16 = p_qf + result.r16[team] / n_sims

        colour = "gold1" if p_champ > 0.15 else ("yellow" if p_champ > 0.05 else "white")

        elo_val = elo_map.get(team) if elo_map else None
        elo_str = f"{elo_val:.0f}" if elo_val is not None else "—"

        table.add_row(
            team,
            elo_str,
            f"[{colour}]{p_champ:.1%}[/{colour}]",
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


def render_predict(
    home: str,
    away: str,
    odds: MatchOdds | None,
    elo_map: dict[str, float],
) -> None:
    DEFAULT_ELO = 1800.0
    home_elo = elo_map.get(home, DEFAULT_ELO)
    away_elo = elo_map.get(away, DEFAULT_ELO)

    p_h_elo, p_d_elo, p_a_elo = elo_to_probs(home_elo, away_elo)

    table = Table(box=box.ROUNDED, header_style="bold magenta", show_header=True)
    table.add_column("", style="bold", min_width=18)
    table.add_column(home, justify="center", min_width=10)
    table.add_column("Draw", justify="center", min_width=10)
    table.add_column(away, justify="center", min_width=10)

    table.add_row(
        "Elo",
        f"{home_elo:.0f}{'*' if home not in elo_map else ''}",
        "—",
        f"{away_elo:.0f}{'*' if away not in elo_map else ''}",
    )
    table.add_row(
        "Elo probability",
        f"[green]{p_h_elo:.1%}[/green]",
        f"{p_d_elo:.1%}",
        f"[green]{p_a_elo:.1%}[/green]" if p_a_elo > p_h_elo else f"{p_a_elo:.1%}",
    )
    table.add_row(
        "Elo implied odds",
        f"{1/p_h_elo:.2f}",
        f"{1/p_d_elo:.2f}",
        f"{1/p_a_elo:.2f}",
    )

    if odds:
        p_h_o, p_d_o, p_a_o = odds_to_probs(odds.odds_home, odds.odds_draw, odds.odds_away)
        table.add_row("", "", "", "")
        table.add_row(
            "Market odds (DK)",
            f"{odds.odds_home:.2f}",
            f"{odds.odds_draw:.2f}",
            f"{odds.odds_away:.2f}",
        )
        table.add_row(
            "Market probability",
            f"[green]{p_h_o:.1%}[/green]",
            f"{p_d_o:.1%}",
            f"[green]{p_a_o:.1%}[/green]" if p_a_o > p_h_o else f"{p_a_o:.1%}",
        )

    console.print(table)
    if home not in elo_map or away not in elo_map:
        console.print("[dim]* team not found in Elo data — using default 1800[/dim]")


def render_trace(trace: TournamentTrace) -> None:
    """Print every game from a single simulated tournament."""
    if trace.group_games:
        console.print(Rule("[bold]Simulated Group Stage Games[/bold]"))
        for r in trace.group_games:
            _print_game(r)

    for rnd in trace.rounds:
        console.print(Rule(f"[bold]{rnd.name}[/bold]"))
        for r in rnd.games:
            _print_game(r)

    console.print()
    console.print(Panel(
        Text(f"🏆  Champion: [bold gold1]{trace.champion}[/bold gold1]", justify="center"),
        style="bold",
    ))


def _print_game(r) -> None:
    if r.winner == r.home:
        home_style, away_style = "bold green", "dim"
    elif r.winner == r.away:
        home_style, away_style = "dim", "bold green"
    else:
        home_style = away_style = "yellow"

    score = f"{r.home_goals}–{r.away_goals}"
    suffix = "  [dim](pens)[/dim]" if r.method == "penalties" else ""
    console.print(
        f"  [{home_style}]{r.home}[/{home_style}]"
        f"  [bold]{score}[/bold]"
        f"  [{away_style}]{r.away}[/{away_style}]"
        f"{suffix}"
    )
