from __future__ import annotations

import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_LINEAGE_PATH = PROJECT_ROOT / "fibo" / "sql" / "sql.sql"


def _split_statements(sql: str) -> list[tuple[str, int]]:
    statements: list[tuple[str, int]] = []
    start = 0
    quote: str | None = None
    depth = 0
    i = 0
    while i < len(sql):
        char = sql[i]
        if quote:
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            statement = sql[start:i].strip()
            if statement:
                leading = len(sql[start:i]) - len(sql[start:i].lstrip())
                statements.append((statement, sql.count("\n", 0, start + leading) + 1))
            start = i + 1
        i += 1
    tail = sql[start:].strip()
    if tail:
        leading = len(sql[start:]) - len(sql[start:].lstrip())
        statements.append((tail, sql.count("\n", 0, start + leading) + 1))
    return statements


def _top_level_keyword(sql: str, keyword: str) -> int:
    quote: str | None = None
    depth = 0
    i = 0
    upper = sql.upper()
    while i < len(sql):
        char = sql[i]
        if quote:
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and upper.startswith(keyword, i):
            before = sql[i - 1] if i else " "
            after = sql[i + len(keyword)] if i + len(keyword) < len(sql) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                return i
        i += 1
    return -1


def _split_top_level_csv(sql: str) -> list[str]:
    parts: list[str] = []
    quote: str | None = None
    depth = 0
    start = 0
    i = 0
    while i < len(sql):
        char = sql[i]
        if quote:
            if char == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 1
                else:
                    quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(sql[start:i].strip())
            start = i + 1
        i += 1
    if sql[start:].strip():
        parts.append(sql[start:].strip())
    return parts


def _query_aliases(statement: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    reserved = {"JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "WHERE", "GROUP", "ORDER", "ON"}
    pattern = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_]\w*)(?:\s+(?:AS\s+)?([A-Za-z_]\w*))?", re.IGNORECASE)
    for match in pattern.finditer(statement):
        table = match.group(1).upper()
        alias = match.group(2)
        if not alias or alias.upper() in reserved:
            alias = table
        aliases[alias.upper()] = table
        aliases[table] = table
    return aliases


def _expression_sources(expression: str, aliases: dict[str, str]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for alias, field in re.findall(r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\b", expression):
        table = aliases.get(alias.upper())
        if not table:
            continue
        key = (table, field.upper())
        if key in seen:
            continue
        seen.add(key)
        sources.append({"table": table, "field": field.upper(), "sourceRef": f"field|{table}|{field.upper()}"})
    return sources


def _output_name(expression: str) -> tuple[str | None, str]:
    alias_match = re.search(r"\s+AS\s+([A-Za-z_]\w*)\s*$", expression, re.IGNORECASE)
    if alias_match:
        return alias_match.group(1).upper(), expression[:alias_match.start()].strip()
    direct = re.fullmatch(r"(?:[A-Za-z_]\w*\s*\.\s*)?([A-Za-z_]\w*)", expression.strip())
    if direct:
        return direct.group(1).upper(), expression.strip()
    return None, expression.strip()


def _query_clauses(statement: str, query_id: str, aliases: dict[str, str]) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    clause_patterns = (
        ("join", r"\bON\s+(.*?)(?=\b(?:JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING)\b|$)"),
        ("filter", r"\bWHERE\s+(.*?)(?=\b(?:GROUP\s+BY|ORDER\s+BY|HAVING)\b|$)"),
        ("grouping", r"\bGROUP\s+BY\s+(.*?)(?=\b(?:ORDER\s+BY|HAVING)\b|$)"),
    )
    for kind, pattern in clause_patterns:
        for position, match in enumerate(re.finditer(pattern, statement, re.IGNORECASE | re.DOTALL), start=1):
            expression = match.group(1).strip()
            clauses.append({
                "clauseKind": kind,
                "expression": expression,
                "sourceRef": f"clause|{query_id}|{kind}|{position}",
                "sourceColumns": _expression_sources(expression, aliases),
            })
    return clauses


def parse_sql_lineage(sql: str) -> list[dict[str, Any]]:
    parsed_queries: list[dict[str, Any]] = []
    for query_number, (statement, line_start) in enumerate(_split_statements(sql), start=1):
        if not statement.lstrip().upper().startswith("SELECT"):
            continue
        from_position = _top_level_keyword(statement, "FROM")
        if from_position < 0:
            continue
        select_list = statement[statement.upper().find("SELECT") + len("SELECT"):from_position]
        aliases = _query_aliases(statement)
        outputs: list[dict[str, Any]] = []
        for position, expression in enumerate(_split_top_level_csv(select_list), start=1):
            name, sql_expression = _output_name(expression)
            name = name or f"OUTPUT_{position}"
            sources = _expression_sources(sql_expression, aliases)
            upper_expression = sql_expression.upper()
            if re.search(r"\b(SUM|COUNT|AVG|MIN|MAX)\s*\(", upper_expression):
                expression_kind = "aggregate"
            elif any(operator in sql_expression for operator in ("+", "-", "*", "/")) or "NULLIF" in upper_expression:
                expression_kind = "derived"
            else:
                expression_kind = "direct"
            output_ref = f"field|SQL_Q{query_number}|{name}"
            outputs.append({
                "name": name,
                "position": position,
                "sqlExpression": sql_expression,
                "expressionKind": expression_kind,
                "sourceRef": output_ref,
                "sourceColumns": sources,
            })

        all_sources = _expression_sources(statement, aliases)
        table_names = sorted(set(aliases.values()))
        query_id = f"SQL_Q{query_number}"
        parsed_queries.append({
            "queryNumber": query_number,
            "queryId": query_id,
            "name": f"Query {query_number}",
            "lineStart": line_start,
            "statement": statement,
            "tables": table_names,
            "aliases": aliases,
            "outputs": outputs,
            "referencedColumns": all_sources,
            "clauses": _query_clauses(statement, query_id, aliases),
            "sourceRef": f"entity|SQL_Q{query_number}",
        })
    return parsed_queries


def load_sql_lineage() -> tuple[str, str, list[dict[str, Any]]]:
    sql = SQL_LINEAGE_PATH.read_text(encoding="utf-8")
    return SQL_LINEAGE_PATH.name, sql, parse_sql_lineage(sql)
