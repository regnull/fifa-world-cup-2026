#!/usr/bin/env python3
"""FIFA World Cup 2026 predictor — Monte Carlo simulation."""
import argparse
from rich.console import Console
from scrape.standings import fetch_standings
from scrape.schedule import fetch_fixtures
from scrape.odds import fetch_odds
from scrape.elo import fetch_elo
from tournament.simulator import run_simulation
from report.terminal import render_report

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="FIFA World Cup 2026 predictor")
    parser.add_argument("--sims", type=int, default=100_000,
                        help="Number of Monte Carlo simulations (default: 100000)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass cached responses and re-scrape all sources")
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

    with console.status(f"[bold green]Simulating {args.sims:,} tournaments..."):
        result = run_simulation(
            standings=standings,
            fixtures=fixtures,
            odds_map=odds_map,
            elo_map=elo_raw,
            n_simulations=args.sims,
        )

    render_report(standings, elo_raw, result, n_sims=args.sims)


if __name__ == "__main__":
    main()
