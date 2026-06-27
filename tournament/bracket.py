import re
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


def resolve_r32_bracket(
    slots: list[tuple[str, str]],
    groups: dict[str, list[TeamStanding]],
) -> list[tuple[str, str]]:
    """
    Take the real ESPN bracket slots and resolve any TBD placeholders
    ('Group L Winner', 'Third Place Group E/H/I/J/K') into concrete team names
    using the supplied (possibly simulated) group standings.

    Third-place slots are resolved using the globally best 8 thirds with
    deconfliction: each qualifying team is assigned to at most one slot.
    """
    ranked: dict[str, list[TeamStanding]] = {
        letter: rank_group(teams) for letter, teams in groups.items()
    }

    # Determine global best-8 third-place teams (by points, GD, GF, name)
    all_thirds = [
        ranked[letter][2]
        for letter, teams in ranked.items()
        if len(teams) >= 3
    ]
    best_8 = sorted(all_thirds, key=lambda s: (-s.points, -s.gd, -s.gf, s.team))[:8]
    # Map group letter → 3rd-place team for the 8 qualifiers
    best_8_by_group: dict[str, TeamStanding] = {t.group: t for t in best_8}

    # Collect teams already named concretely in fixed slots — these are
    # 3rd-place qualifiers explicitly placed by the draw (e.g. France vs Sweden)
    # and must not be double-assigned to a TBD slot.
    already_placed: set[str] = {
        name
        for h, a in slots
        for name in (h, a)
        if not _is_placeholder(name)
    }
    # Remove already-placed teams' groups from the available pool
    for group, third in list(best_8_by_group.items()):
        if third.team in already_placed:
            del best_8_by_group[group]

    # Pre-assign "Third Place Group X/Y/Z" slots greedily so each team
    # appears at most once. Slots are sorted by fewest eligible groups first
    # (most constrained first) for a stable assignment.
    third_slot_names: list[str] = []
    for h, a in slots:
        for name in (h, a):
            if re.match(r"Third Place Group", name) and name not in third_slot_names:
                third_slot_names.append(name)

    third_slot_names.sort(key=lambda n: len(re.findall(r"[A-L]", n)))

    third_assignments: dict[str, str] = {}
    assigned_groups: set[str] = set()
    for name in third_slot_names:
        m = re.match(r"Third Place Group ([A-L/]+)", name)
        if not m:
            continue
        letters = m.group(1).split("/")
        # Pick the highest-ranked qualifying team from the eligible groups
        # that hasn't been assigned yet
        candidates = [
            best_8_by_group[l]
            for l in letters
            if l in best_8_by_group and l not in assigned_groups
        ]
        if candidates:
            best = sorted(candidates, key=lambda s: (-s.points, -s.gd, -s.gf, s.team))[0]
            third_assignments[name] = best.team
            assigned_groups.add(best.group)

    # Fallback: any TBD third slot still unfilled (its eligible groups didn't
    # contain an available qualifier after simulation) gets the next best
    # unassigned third. Guarantees no placeholder survives into the bracket.
    leftover = sorted(
        (t for g, t in best_8_by_group.items() if g not in assigned_groups),
        key=lambda s: (-s.points, -s.gd, -s.gf, s.team),
    )
    for name in third_slot_names:
        if name not in third_assignments and leftover:
            third_assignments[name] = leftover.pop(0).team

    def _resolve(name: str) -> str:
        if not _is_placeholder(name):
            return name
        # "Group X Winner" / "Group X 2nd Place" / "Group X Runner-up"
        m = re.match(r"Group ([A-L]) (Winner|2nd Place|Runner.up)", name)
        if m:
            letter, pos = m.group(1), m.group(2)
            idx = 0 if pos == "Winner" else 1
            team_list = ranked.get(letter, [])
            return team_list[idx].team if len(team_list) > idx else name
        if name in third_assignments:
            return third_assignments[name]
        return name

    return [(_resolve(h), _resolve(a)) for h, a in slots]


def _is_placeholder(name: str) -> bool:
    return "Group" in name or "Third Place" in name or "Place" in name


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
    present_letters = [letter for letter in group_letters if letter in groups]
    if not present_letters:
        return []
    ranked = {letter: rank_group(groups[letter]) for letter in present_letters}
    best_thirds = select_best_third(groups)

    matchups: list[tuple[str, str]] = []

    # 12 group-position matchups: winner[i] vs runner-up[(i+1) % len]
    n = len(present_letters)
    for i, letter in enumerate(present_letters):
        winner = ranked[letter][0].team
        next_letter = present_letters[(i + 1) % n]
        runner_up = ranked[next_letter][1].team
        matchups.append((winner, runner_up))

    # 4 matchups from best 8 third-place teams (paired sequentially)
    thirds = best_thirds[:8]
    for i in range(0, len(thirds) - 1, 2):
        matchups.append((thirds[i].team, thirds[i + 1].team))

    return matchups
