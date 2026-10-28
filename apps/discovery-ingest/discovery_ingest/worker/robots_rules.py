"""RFC 9309 robots.txt matching: the longest matching rule wins, ``Allow`` wins a tie, ``*`` and ``$`` work."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

RULE_FIELDS = {"allow": True, "disallow": False}
_PERCENT_ESCAPE = re.compile(r"%[0-9a-fA-F]{2}")


@dataclass(frozen=True, slots=True)
class Rule:
    """One ``Allow`` or ``Disallow`` line, compiled to a prefix matcher."""

    allow: bool
    length: int
    matcher: re.Pattern[str]


def _canonical(text: str) -> str:
    return _PERCENT_ESCAPE.sub(lambda escape: escape.group().upper(), text)


def compile_rule(allow: bool, path: str) -> Rule:
    """Compile a rule path: ``*`` matches any run of characters and a trailing ``$`` anchors the end."""
    anchored = path.endswith("$")
    pieces = _canonical(path.removesuffix("$")).split("*")
    body = ".*".join(re.escape(piece) for piece in pieces)
    return Rule(allow, len(path), re.compile(body + (r"\Z" if anchored else ""), re.DOTALL))


def _fields(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    for line in lines:
        field, colon, value = line.partition("#")[0].partition(":")
        if colon:
            yield field.strip().lstrip("\ufeff").lower(), value.strip()


def _records(fields: Iterable[tuple[str, str]]) -> Iterator[tuple[list[str], Rule]]:
    """Yield each rule with the agent tokens of its group; consecutive ``User-agent`` lines share a group."""
    agents: list[str] = []
    collecting = False
    for field, value in fields:
        if field == "user-agent" and value:
            agents = [*agents, value.lower()] if collecting else [value.lower()]
            collecting = True
        elif field in RULE_FIELDS and value:
            collecting = False
            yield agents, compile_rule(RULE_FIELDS[field], value)


def _groups(fields: Iterable[tuple[str, str]]) -> dict[str, list[Rule]]:
    groups: dict[str, list[Rule]] = {}
    for agents, rule in _records(fields):
        for agent in agents:
            groups.setdefault(agent, []).append(rule)
    return groups


def _rules_for(groups: dict[str, list[Rule]], agent: str) -> list[Rule]:
    """Pick the group whose token is the longest prefix of ``agent``, else the ``*`` group, else no rules."""
    product = agent.lower()
    named = [token for token in groups if token != "*" and product.startswith(token)]
    return groups.get(max(named, key=len, default="*"), [])


def _target(url: str) -> str:
    parts = urlsplit(url)
    return _canonical(f"{parts.path or '/'}{'?' + parts.query if parts.query else ''}")


class RobotsRules:
    """The rules one robots.txt holds for one agent."""

    def __init__(self, rules: Sequence[Rule]) -> None:
        """Keep the rules that apply to the agent."""
        self._rules = tuple(rules)

    @classmethod
    def parse(cls, lines: Sequence[str], agent: str) -> RobotsRules:
        """Build the rules for ``agent`` from robots.txt ``lines``; malformed lines are ignored."""
        return cls(_rules_for(_groups(_fields(lines)), agent))

    def allowed(self, url: str) -> bool:
        """Return whether ``url`` may be fetched: the longest matching rule decides and ``Allow`` wins a tie."""
        if urlsplit(url).path == "/robots.txt":
            return True
        target = _target(url)
        matching = [rule for rule in self._rules if rule.matcher.match(target)]
        best = max(matching, key=lambda rule: (rule.length, rule.allow), default=None)
        return best is None or best.allow
