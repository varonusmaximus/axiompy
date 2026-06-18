# @!tooling

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompactAnnotation:
    """v1.3 shorthand: @!code-review or @!code-review,testing,load=none"""

    domains: list[str]
    load: bool = True
    line_no: int = 0
    raw_line: str = ""


@dataclass
class RefDirective:
    kind: str
    uri: str
    hash: str
    scope: list[str] = field(default_factory=list)
    line_no: int = 0
    raw_line: str = ""


@dataclass
class GuardDirective:
    when: list[tuple[str, str]]
    then: list[tuple[str, str]]
    line_no: int = 0
    raw_line: str = ""


@dataclass
class AALFile:
    compact: list[CompactAnnotation] = field(default_factory=list)
    refs: list[RefDirective] = field(default_factory=list)
    loads: list[RefDirective] = field(default_factory=list)
    guards: list[GuardDirective] = field(default_factory=list)


AALHeader = AALFile
