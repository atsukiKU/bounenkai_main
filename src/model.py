from typing import List


def choose_target(groups: List[List[str]]) -> int:
    """Choose index of a group with smallest size. If multiple, choose one at random."""
    if not groups:
        raise ValueError("no groups provided")
    sizes = [len(g) for g in groups]
    min_size = min(sizes)
    candidates = [i for i, s in enumerate(sizes) if s == min_size]
    import random
    return random.choice(candidates)


def assign(groups: List[List[str]], person: str, target: int) -> None:
    groups[target].append(person)


def is_unassigned(groups: List[List[str]], person: str) -> bool:
    return all(person not in g for g in groups)


def get_unassigned(people: List[str], groups: List[List[str]]) -> List[str]:
    return [p for p in people if is_unassigned(groups, p)]
