"""SQL validation engine for LLM-generated queries.

Provides :class:`SQLValidator` used by composable validators in :mod:`axiompy.validators`.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Optional, Set

try:
    import sqlparse

    HAS_SQLPARSE = True
except ImportError:
    HAS_SQLPARSE = False


@dataclass
class SQLValidationResult:
    """Result of SQL validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    missing_columns: Set[str] = field(default_factory=set)
    error_type: Optional[object] = None

    def __bool__(self) -> bool:
        """Allow using validation result as boolean."""
        return self.valid


class SQLValidator:
    """Validate SQL queries against schema metadata."""

    @staticmethod
    def validate_columns(
        sql: str,
        schema_columns: Set[str],
        strict: bool = False,
    ) -> SQLValidationResult:
        """Validate that all columns referenced in SQL exist in schema."""
        errors: list[str] = []
        warnings: list[str] = []
        missing_columns: Set[str] = set()

        try:
            referenced_columns = SQLValidator.extract_columns(sql)
        except (ValueError, TypeError, re.error) as e:
            return SQLValidationResult(
                valid=False, errors=[f"Failed to parse SQL: {e}"], warnings=[]
            )

        schema_lower = {col.lower() for col in schema_columns}

        for col in referenced_columns:
            col_lower = col.lower()
            if SQLValidator._is_sql_keyword(col_lower):
                continue
            if col_lower not in schema_lower:
                missing_columns.add(col)
                if strict:
                    errors.append(
                        f"Column '{col}' not found in schema. "
                        f"Available: {', '.join(sorted(schema_columns))}"
                    )

        if errors:
            return SQLValidationResult(
                valid=False, errors=errors, warnings=warnings, missing_columns=missing_columns
            )

        if missing_columns and not strict:
            warnings.append(
                f"Potentially invalid columns: {', '.join(sorted(missing_columns))}. "
                f"These may be valid if they're from subqueries or derived tables."
            )

        return SQLValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_columns=missing_columns,
        )

    @staticmethod
    def extract_columns(sql: str) -> Set[str]:
        """Extract column names referenced in SQL query."""
        columns: Set[str] = set()
        sql_normalized = sql.replace("\n", " ").replace("\t", " ")

        select_pattern = r"SELECT\s+(?:DISTINCT\s+)?(.+?)(?:FROM|WHERE|GROUP|ORDER|LIMIT|;|$)"
        select_match = re.search(select_pattern, sql_normalized, re.IGNORECASE)
        if select_match:
            select_clause = select_match.group(1)
            for col in select_clause.split(","):
                col = col.strip()
                col = re.sub(r"\s+AS\s+\w+", "", col, flags=re.IGNORECASE)
                if "." in col:
                    col = col.split(".")[-1]
                col = re.sub(r"\w+\s*\((.+?)\)", r"\1", col)
                col = col.strip().replace("`", "").replace('"', "")
                if col and col != "*":
                    columns.add(col.lower())

        condition_pattern = r"(?:WHERE|HAVING)\s+(.+?)(?:GROUP|ORDER|LIMIT|;|$)"
        for match in re.finditer(condition_pattern, sql_normalized, re.IGNORECASE):
            condition = match.group(1)
            condition_no_quotes = re.sub(r"'[^']*'|\"[^\"]*\"", "", condition)
            col_matches = re.findall(
                r"\b([a-zA-Z_]\w*)\s*(?:=|<|>|!=|LIKE|IN|BETWEEN|NOT)",
                condition_no_quotes,
                re.IGNORECASE,
            )
            for col in col_matches:
                if col.lower() not in ("and", "or", "not"):
                    columns.add(col.lower())

        order_group_pattern = r"(?:ORDER\s+BY|GROUP\s+BY)\s+(.+?)(?:ORDER|GROUP|LIMIT|;|$)"
        for match in re.finditer(order_group_pattern, sql_normalized, re.IGNORECASE):
            cols_str = match.group(1)
            for col_expr in cols_str.split(","):
                col_expr = col_expr.strip()
                col_expr = re.sub(r"\s+(?:ASC|DESC)$", "", col_expr, flags=re.IGNORECASE)
                id_match = re.match(r"(?:`|\")?([a-zA-Z_]\w*)(?:`|\")?", col_expr)
                if id_match:
                    columns.add(id_match.group(1).lower())

        on_pattern = r"ON\s+(.+?)(?:WHERE|GROUP|ORDER|LIMIT|INNER|LEFT|RIGHT|FULL|;|$)"
        for match in re.finditer(on_pattern, sql_normalized, re.IGNORECASE):
            condition = match.group(1)
            condition_no_quotes = re.sub(r"'[^']*'|\"[^\"]*\"", "", condition)
            col_matches = re.findall(
                r"\b([a-zA-Z_]\w*)\s*(?:=|<|>|!=)", condition_no_quotes, re.IGNORECASE
            )
            for col in col_matches:
                if col.lower() not in ("and", "or"):
                    columns.add(col.lower())

        return columns

    @staticmethod
    def _is_sql_keyword(word: str) -> bool:
        """Check if a word is a SQL keyword or function."""
        sql_keywords = {
            "select",
            "from",
            "where",
            "and",
            "or",
            "not",
            "in",
            "like",
            "is",
            "null",
            "true",
            "false",
            "case",
            "when",
            "then",
            "else",
            "end",
            "having",
            "group",
            "order",
            "by",
            "asc",
            "desc",
            "limit",
            "offset",
            "distinct",
            "all",
            "any",
            "some",
            "between",
            "exists",
            "union",
            "except",
            "intersect",
            "count",
            "sum",
            "avg",
            "max",
            "min",
            "abs",
            "round",
            "length",
            "substring",
            "upper",
            "lower",
            "trim",
            "coalesce",
            "cast",
            "date",
            "year",
            "month",
            "day",
            "now",
            "current_date",
            "stddev",
            "variance",
            "collect",
            "listagg",
            "row_number",
            "rank",
            "dense_rank",
            "lag",
            "lead",
        }
        return word.lower() in sql_keywords

    @staticmethod
    def validate_tables(sql: str, valid_tables: Set[str]) -> SQLValidationResult:
        """Validate that all tables referenced in SQL exist."""
        errors: list[str] = []
        referenced_tables: Set[str] = set()
        sql_normalized = sql.replace("\n", " ").replace("\t", " ")

        from_pattern = r"FROM\s+([a-zA-Z_]\w*)"
        for match in re.finditer(from_pattern, sql_normalized, re.IGNORECASE):
            referenced_tables.add(match.group(1).lower())

        join_pattern = r"(?:INNER|LEFT|RIGHT|FULL)?\s*JOIN\s+([a-zA-Z_]\w*)"
        for match in re.finditer(join_pattern, sql_normalized, re.IGNORECASE):
            referenced_tables.add(match.group(1).lower())

        valid_tables_lower = {t.lower() for t in valid_tables}
        for table in referenced_tables:
            if table not in valid_tables_lower:
                errors.append(
                    f"Table '{table}' not found. "
                    f"Available tables: {', '.join(sorted(valid_tables))}"
                )

        return SQLValidationResult(valid=len(errors) == 0, errors=errors, warnings=[])

    @staticmethod
    def _basic_syntax_checks(sql: str) -> tuple[list[str], list[str]]:
        """Run lightweight checks that complement sqlparse."""
        errors: list[str] = []
        warnings: list[str] = []

        open_count = sql.count("(") - sql.count("\\(")
        close_count = sql.count(")") - sql.count("\\)")
        if open_count != close_count:
            errors.append(f"Unmatched parentheses: {open_count} open, {close_count} close")

        single_quotes = len(re.findall(r"(?<!\\)'", sql)) % 2
        double_quotes = len(re.findall(r"(?<!\\)\"", sql)) % 2
        if single_quotes != 0:
            errors.append("Unmatched single quotes")
        if double_quotes != 0:
            errors.append("Unmatched double quotes")

        if not re.search(r"\bSELECT\b", sql, re.IGNORECASE):
            warnings.append("Query doesn't contain SELECT keyword")
        if not re.search(r"\bFROM\b", sql, re.IGNORECASE):
            warnings.append("Query doesn't contain FROM keyword")

        return errors, warnings

    @staticmethod
    def validate_syntax(sql: str, use_parser: bool = True) -> SQLValidationResult:
        """Perform SQL syntax validation using sqlparse when available."""
        errors: list[str] = []
        warnings: list[str] = []
        sql = sql.strip()

        if not sql:
            errors.append("SQL query is empty")
            return SQLValidationResult(valid=False, errors=errors, warnings=warnings)

        if use_parser and HAS_SQLPARSE:
            try:
                parsed = sqlparse.parse(sql)
                if not parsed:
                    errors.append("Failed to parse SQL - invalid syntax")
                    return SQLValidationResult(valid=False, errors=errors, warnings=warnings)

                for statement in parsed:
                    tokens = [t for t in statement.tokens if not t.is_whitespace]
                    if not tokens:
                        errors.append("Empty SQL statement")
                        continue

                    first_token = str(tokens[0]).upper()
                    valid_starts = [
                        "SELECT",
                        "INSERT",
                        "UPDATE",
                        "DELETE",
                        "WITH",
                        "CREATE",
                        "DROP",
                        "ALTER",
                        "EXPLAIN",
                    ]
                    if first_token not in valid_starts:
                        warnings.append(
                            f"Statement starts with '{first_token}' - "
                            f"expected one of: {', '.join(valid_starts)}"
                        )

                    sql_upper = sql.upper()
                    if "LIMIT" in sql_upper:
                        limit_pos = sql_upper.find("LIMIT")
                        before_limit = sql_upper[:limit_pos]
                        if "FROM" not in before_limit:
                            errors.append("LIMIT clause found without FROM clause")
                        after_limit = sql_upper[limit_pos:].replace("LIMIT", "", 1).strip()
                        if not after_limit or not after_limit[0].isdigit():
                            errors.append("LIMIT clause requires a numeric value")

                    bad_pairs = [
                        ("FROM", "WHERE"),
                        ("FROM", "LIMIT"),
                        ("FROM", "ORDER"),
                        ("SELECT", "FROM"),
                        ("WHERE", "FROM"),
                        ("WHERE", "ORDER"),
                    ]
                    for i, token in enumerate(tokens[:-1]):
                        if not token.is_keyword:
                            continue
                        token_str = str(token).upper().strip()
                        next_token = tokens[i + 1]
                        if next_token.is_keyword:
                            next_str = str(next_token).upper().strip()
                            if (token_str, next_str) in bad_pairs:
                                errors.append(
                                    f"Invalid syntax: '{token_str}' followed by '{next_str}'"
                                )

            except (ValueError, TypeError, AttributeError) as e:
                errors.append(f"SQL parsing failed: {e}")
        elif not HAS_SQLPARSE and use_parser:
            warnings.append(
                "sqlparse not installed - using basic validation. "
                "Install with: pip install sqlparse"
            )

        basic_errors, basic_warnings = SQLValidator._basic_syntax_checks(sql)
        errors.extend(basic_errors)
        warnings.extend(basic_warnings)

        return SQLValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    @staticmethod
    def validate_with_db_dryrun(
        sql: str, db_connection, dialect: str = "sqlite"
    ) -> SQLValidationResult:
        """Validate SQL by doing a database dry-run using EXPLAIN."""
        errors: list[str] = []
        warnings: list[str] = []

        if not sql or not sql.strip():
            return SQLValidationResult(valid=False, errors=["SQL query is empty"], warnings=[])

        try:
            cursor = db_connection.cursor()
            if dialect == "sqlite":
                cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            elif dialect in ("postgres", "mysql"):
                cursor.execute(f"EXPLAIN {sql}")
            else:
                warnings.append(f"Unknown dialect '{dialect}' - trying EXPLAIN anyway")
                cursor.execute(f"EXPLAIN {sql}")
            cursor.close()

        except sqlite3.OperationalError as e:
            error_msg = str(e)
            errors.append(f"Database validation failed: {error_msg}")
            if "no such table" in error_msg.lower():
                errors.append("Hint: Check that the table name exists in the database")
            elif "no such column" in error_msg.lower():
                errors.append("Hint: Check that column names match the schema exactly")
            elif "syntax error" in error_msg.lower():
                errors.append("Hint: Check SQL syntax - there may be missing/extra keywords")

        except (AttributeError, TypeError, OSError) as e:
            errors.append(f"Database validation error: {e}")

        return SQLValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
