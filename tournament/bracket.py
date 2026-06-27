from scrape.models import TeamStanding


def rank_group(standings: list[TeamStanding]) -> list[TeamStanding]:
    """Sort group standings: Pts → GD → GF → team name (alphabetical tiebreak)."""
    return sorted(
        standings,
        key=lambda s: (-s.points, -s.gd, -s.gf, s.team),
    )


def select_best_third(
    groups: dict[str, list[TeamStanding]]
) -> list[TeamStanding]:
    """Return the 8 best third-place teams from all 12 groups."""
    third_place = [rank_group(s)[2] for s in groups.values() if len(s) >= 3]
    return sorted(
        third_place,
        key=lambda s: (-s.points, -s.gd, -s.gf, s.team),
    )[:8]


def build_r32_bracket(
    groups: dict[str, list[TeamStanding]]
) -> list[tuple[str, str]]:
    """
    Return 16 R32 matchups as (home, away) team name pairs.

    Group winners and runners-up fill the first 12 matchups:
      Match i: winner of group[i] vs runner-up of group[(i+1) % 12]
    Best 8 third-place teams fill the final 4 matchups (paired sequentially).
    """
    group_letters = list("ABCDEFGHIJKL")
    ranked = {letter: rank_group(groups[letter]) for letter in group_letters}
    best_thirds = select_best_third(groups)

    matchups: list[tuple[str, str]] = []

    # 12 group-position matchups: winner[i] vs runner-up[(i+1) % 12]
    for i, letter in enumerate(group_letters):
        winner = ranked[letter][0].team
        next_letter = group_letters[(i + 1) % 12]
        runner_up = ranked[next_letter][1].team
        matchups.append((winner, runner_up))

    # 4 matchups from best 8 third-place teams (paired sequentially)
    thirds = best_thirds[:8]
    for i in range(0, 8, 2):
        matchups.append((thirds[i].team, thirds[i + 1].team))

    return matchups
