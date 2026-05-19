"""Tests for axiompy.sql_engine.SQLValidator."""

import sqlite3

import pytest

from axiompy.sql_engine import SQLValidationResult, SQLValidator


class TestSQLValidationResult:
    """Tests for SQLValidationResult."""

    def test_bool_true_when_valid(self) -> None:
        """Valid results are truthy."""
        assert bool(SQLValidationResult(valid=True, errors=[], warnings=[]))

    def test_bool_false_when_invalid(self) -> None:
        """Invalid results are falsy."""
        assert not bool(SQLValidationResult(valid=False, errors=["err"], warnings=[]))


class TestSQLValidatorColumns:
    """Tests for column validation and extraction."""

    def test_validate_columns_all_present(self) -> None:
        """Known columns pass validation."""
        result = SQLValidator.validate_columns(
            "SELECT id, name FROM users WHERE id = 1",
            {"id", "name", "users"},
        )
        assert result.valid
        assert not result.errors

    def test_validate_columns_strict_missing(self) -> None:
        """Strict mode fails on unknown columns."""
        result = SQLValidator.validate_columns(
            "SELECT missing_col FROM users",
            {"id", "name"},
            strict=True,
        )
        assert not result.valid
        assert result.missing_columns == {"missing_col"}
        assert any("missing_col" in err for err in result.errors)

    def test_validate_columns_non_strict_warns(self) -> None:
        """Non-strict mode warns on unknown columns."""
        result = SQLValidator.validate_columns(
            "SELECT ghost FROM users",
            {"id"},
            strict=False,
        )
        assert result.valid
        assert result.warnings

    def test_extract_columns_from_select_and_where(self) -> None:
        """Column extraction finds SELECT and WHERE references."""
        cols = SQLValidator.extract_columns(
            "SELECT u.id, count(*) AS cnt FROM users u WHERE status = 'active' ORDER BY id"
        )
        assert "id" in cols
        assert "status" in cols


class TestSQLValidatorTables:
    """Tests for table validation."""

    def test_validate_tables_known(self) -> None:
        """Known tables pass validation."""
        result = SQLValidator.validate_tables(
            "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id",
            {"orders", "customers"},
        )
        assert result.valid

    def test_validate_tables_unknown(self) -> None:
        """Unknown tables fail validation."""
        result = SQLValidator.validate_tables(
            "SELECT * FROM phantom",
            {"orders"},
        )
        assert not result.valid
        assert any("phantom" in err for err in result.errors)


class TestSQLValidatorSyntax:
    """Tests for syntax validation."""

    def test_validate_syntax_empty(self) -> None:
        """Empty SQL fails syntax validation."""
        result = SQLValidator.validate_syntax("")
        assert not result.valid
        assert "empty" in result.errors[0].lower()

    def test_validate_syntax_unmatched_parens(self) -> None:
        """Unmatched parentheses are reported."""
        result = SQLValidator.validate_syntax("SELECT ( id FROM t", use_parser=False)
        assert not result.valid
        assert any("parentheses" in err.lower() for err in result.errors)

    def test_validate_syntax_valid_select(self) -> None:
        """Well-formed SELECT passes basic checks."""
        result = SQLValidator.validate_syntax(
            "SELECT id FROM users WHERE id = 1",
            use_parser=False,
        )
        assert result.valid


class TestSQLValidatorDryRun:
    """Tests for database dry-run validation."""

    def test_validate_with_db_dryrun_sqlite(self) -> None:
        """SQLite EXPLAIN accepts valid SQL against an in-memory DB."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE items (id INTEGER, label TEXT)")
        result = SQLValidator.validate_with_db_dryrun(
            "SELECT id FROM items WHERE id = 1",
            conn,
            dialect="sqlite",
        )
        conn.close()
        assert result.valid

    def test_validate_with_db_dryrun_invalid_sql(self) -> None:
        """Invalid SQL fails dry-run validation."""
        conn = sqlite3.connect(":memory:")
        result = SQLValidator.validate_with_db_dryrun(
            "SELECT nope FROM missing_table",
            conn,
            dialect="sqlite",
        )
        conn.close()
        assert not result.valid
        assert result.errors
