# @!testing

"""Tests for AAL parser (compact, guards, refs)."""

from __future__ import annotations

import pytest

from axiompy.aal.parser import (
    parse_aal_file,
    parse_compact,
    parse_guard_then,
    parse_guard_when,
    parse_scope,
    split_guard_segments,
    strip_comment,
)


def test_parse_scope_empty_and_values():
    assert parse_scope(None) == []
    assert parse_scope(' "a", b ') == ["a", "b"]


def test_strip_comment_py_and_block():
    assert strip_comment("# @!testing", ".py") == "@!testing"
    assert strip_comment("/* @!testing */", ".java") == "@!testing"
    assert strip_comment("<!-- @!testing -->", ".html") == "@!testing"
    assert strip_comment("not a comment", ".py") is None


def test_parse_compact_load_modifier():
    ann = parse_compact("testing,load=none", 1)
    assert ann.domains == ["testing"]
    assert ann.load is False


def test_parse_compact_invalid_domain():
    with pytest.raises(ValueError, match="invalid domain"):
        parse_compact("bad_domain", 1)
    with pytest.raises(ValueError, match="reserved"):
        parse_compact("guard", 1)
    with pytest.raises(ValueError, match="at least one domain"):
        parse_compact("load=none", 1)


def test_split_guard_segments_respects_quotes():
    assert split_guard_segments('read:"a,b",read:c') == ['read:"a,b"', "read:c"]


def test_parse_guard_when_and_then():
    when = parse_guard_when("symbol:foo,path:tests/**")
    assert when == [("symbol", "foo"), ("path", "tests/**")]
    then = parse_guard_then('read:"testing/extra.md",read:testing')
    assert then == [("read", "testing/extra.md"), ("read", "testing")]


def test_parse_guard_errors():
    with pytest.raises(ValueError, match="unknown trigger"):
        parse_guard_when("bogus:foo")
    with pytest.raises(ValueError, match="invalid guard action"):
        parse_guard_then("noop:foo")


def test_parse_aal_file_guard_and_ref():
    content = (
        "# @!guard when=symbol:save then=read:testing\n"
        '# @!ref uri=".cursor/skills/testing/SKILL.md" hash="DRAFT"\n'
        "# @!testing\n"
    )
    aal = parse_aal_file(content, ".py")
    assert len(aal.guards) == 1
    assert aal.guards[0].when[0] == ("symbol", "save")
    assert aal.refs[0].uri.endswith("SKILL.md")
    assert aal.compact[0].domains == ["testing"]


def test_parse_aal_file_skips_ref_markers():
    content = "# @!ref-begin\n# @!ref-end\n"
    aal = parse_aal_file(content, ".py")
    assert not aal.compact and not aal.guards and not aal.refs
