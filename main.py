#!/usr/bin/env python3
"""FIFA World Cup 2026 predictor — Monte Carlo simulation."""
import argparse
from rich.console import Console
from rich.progress import Progress, BarColumn, TaskProgressColumn, TimeRemainingColumn
from scrape.standings import fetch_standings
from scrape.schedule import fetch_fixtures
from scrape.odds import fetch_odds
from scrape.elo import fetch_elo
from tournament.simulator import run_simulation, simulate_trace
from report.terminal import render_report, render_trace, render_predict

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="FIFA World Cup 2026 predictor")
    parser.add_argument("--sims", type=int, default=100_000,
                        help="Number of Monte Carlo simulations (default: 100000)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass cached responses and re-scrape all sources")
    parser.add_argument("--trace", action="store_true",
                        help="Run one simulation and print every game result")
    parser.add_argument("--predict", metavar="MATCHUP",
                        help='Predict a single game, e.g. --predict "Spain vs France"')
    args = parser.parse_args()

    use_cache = not args.no_cache

    console.print("[bold cyan]FIFA World Cup 2026 Predictor[/bold cyan]")
    console.print(f"Running {args.sims:,} simulations...\n")

    try:
        with console.status("[bold green]Scraping standings..."):
            standings = fetch_standings(use_cache=use_cache)
    except Exception as exc:
        console.print(f"[yellow]Warning: standings unavailable ({exc})[/yellow]")
        standings = []

    try:
        with console.status("[bold green]Scraping fixtures..."):
            fixtures = fetch_fixtures(use_cache=use_cache)
    except Exception as exc:
        console.print(f"[yellow]Warning: fixtures unavailable ({exc})[/yellow]")
        fixtures = []

    try:
        with console.status("[bold green]Scraping Elo ratings..."):
            elo_raw = fetch_elo(use_cache=use_cache)
    except Exception as exc:
        console.print(f"[yellow]Warning: Elo ratings unavailable ({exc})[/yellow]")
        elo_raw = {}

    try:
        with console.status("[bold green]Scraping match odds..."):
            odds_map = fetch_odds(use_cache=use_cache)
    except Exception as exc:
        console.print(f"[yellow]Warning: match odds unavailable ({exc})[/yellow]")
        odds_map = {}

    if not standings:
        console.print("[yellow]Warning: standings unavailable — simulation may be low-quality.[/yellow]")

    n_odds = len(odds_map)
    n_elo = len(elo_raw)
    console.print(f"[dim]Loaded {len(standings)} team standings, "
                  f"{len(fixtures)} upcoming fixtures, "
                  f"{n_odds} match odds entries, "
                  f"{n_elo} Elo ratings.[/dim]\n")

    if args.predict:
        sep = " vs " if " vs " in args.predict else " v "
        parts = args.predict.split(sep, 1)
        if len(parts) != 2:
            console.print("[red]Use format: --predict \"Team A vs Team B\"[/red]")
            return
        home, away = parts[0].strip(), parts[1].strip()
        odds = odds_map.get((home, away)) or odds_map.get((away, home))
        render_predict(home, away, odds, elo_raw)
        return

    if args.trace:
        console.print("[bold cyan]── Single tournament trace ──[/bold cyan]\n")
        trace = simulate_trace(standings, fixtures, odds_map, elo_raw)
        render_trace(trace)
        return

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[bold green]Simulating {args.sims:,} tournaments...", total=args.sims
        )
        result = run_simulation(
            standings=standings,
            fixtures=fixtures,
            odds_map=odds_map,
            elo_map=elo_raw,
            n_simulations=args.sims,
            progress=progress,
            task_id=task,
        )

    render_report(standings, elo_raw, result, n_sims=args.sims)


if __name__ == "__main__":
    main()
