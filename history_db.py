from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "appverity_history.db"


class HistoryDatabaseError(RuntimeError):
    """Raised when AppVerity cannot read or update its local history database."""


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    connection: sqlite3.Connection | None = None

    try:
        connection = sqlite3.connect(DATABASE_PATH, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        yield connection
        connection.commit()
    except sqlite3.Error as exc:
        if connection is not None:
            connection.rollback()
        raise HistoryDatabaseError(
            f"Unable to access the local analysis history: {exc}"
        ) from exc
    finally:
        if connection is not None:
            connection.close()


def initialize_database() -> None:
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analyzed_at TEXT NOT NULL,
                app_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                developer TEXT,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                transparency_score INTEGER NOT NULL,
                positive_percentage REAL NOT NULL,
                neutral_percentage REAL NOT NULL,
                negative_percentage REAL NOT NULL,
                reviews_analyzed INTEGER NOT NULL,
                rating REAL,
                summary TEXT NOT NULL,
                result_json TEXT NOT NULL,
                report_text TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_app_id
                ON analyses(app_id);

            CREATE INDEX IF NOT EXISTS idx_analyses_analyzed_at
                ON analyses(analyzed_at DESC);

            CREATE INDEX IF NOT EXISTS idx_analyses_risk_level
                ON analyses(risk_level);
            """
        )


def save_analysis(result: dict[str, Any], report_text: str) -> int:
    analyzed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    serialized_result = json.dumps(result, ensure_ascii=False, default=str)

    with _connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO analyses (
                analyzed_at,
                app_id,
                app_name,
                developer,
                risk_score,
                risk_level,
                transparency_score,
                positive_percentage,
                neutral_percentage,
                negative_percentage,
                reviews_analyzed,
                rating,
                summary,
                result_json,
                report_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analyzed_at,
                str(result["app_id"]),
                str(result["app_name"]),
                (
                    str(result["developer"])
                    if result.get("developer") is not None
                    else None
                ),
                int(result["risk_score"]),
                str(result["risk_level"]),
                int(result.get("transparency_score") or 0),
                float(result["positive_percentage"]),
                float(result["neutral_percentage"]),
                float(result["negative_percentage"]),
                int(result["reviews_analyzed"]),
                (
                    float(result["rating"])
                    if result.get("rating") is not None
                    else None
                ),
                str(result["summary"]),
                serialized_result,
                report_text,
            ),
        )
        return int(cursor.lastrowid)


def _row_to_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "analyzed_at": str(row["analyzed_at"]),
        "app_id": str(row["app_id"]),
        "app_name": str(row["app_name"]),
        "developer": row["developer"],
        "risk_score": int(row["risk_score"]),
        "risk_level": str(row["risk_level"]),
        "transparency_score": int(row["transparency_score"]),
        "positive_percentage": float(row["positive_percentage"]),
        "neutral_percentage": float(row["neutral_percentage"]),
        "negative_percentage": float(row["negative_percentage"]),
        "reviews_analyzed": int(row["reviews_analyzed"]),
        "rating": (
            float(row["rating"])
            if row["rating"] is not None
            else None
        ),
        "summary": str(row["summary"]),
    }


def list_analyses(
    search: str = "",
    risk_level: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    where_parts: list[str] = []
    parameters: list[Any] = []

    cleaned_search = search.strip()
    if cleaned_search:
        where_parts.append(
            "(app_name LIKE ? OR app_id LIKE ? OR developer LIKE ?)"
        )
        pattern = f"%{cleaned_search}%"
        parameters.extend([pattern, pattern, pattern])

    if risk_level and risk_level != "All":
        where_parts.append("risk_level = ?")
        parameters.append(risk_level)

    where_clause = (
        "WHERE " + " AND ".join(where_parts)
        if where_parts
        else ""
    )

    parameters.append(max(1, min(int(limit), 1000)))

    with _connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                id,
                analyzed_at,
                app_id,
                app_name,
                developer,
                risk_score,
                risk_level,
                transparency_score,
                positive_percentage,
                neutral_percentage,
                negative_percentage,
                reviews_analyzed,
                rating,
                summary
            FROM analyses
            {where_clause}
            ORDER BY analyzed_at DESC, id DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()

    return [_row_to_summary(row) for row in rows]


def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM analyses WHERE id = ?",
            (int(analysis_id),),
        ).fetchone()

    if row is None:
        return None

    try:
        result = json.loads(str(row["result_json"]))
    except json.JSONDecodeError:
        result = {}

    return {
        **_row_to_summary(row),
        "result": result,
        "report_text": str(row["report_text"]),
    }


def delete_analysis(analysis_id: int) -> bool:
    with _connection() as connection:
        cursor = connection.execute(
            "DELETE FROM analyses WHERE id = ?",
            (int(analysis_id),),
        )
        return cursor.rowcount > 0


def clear_history() -> int:
    with _connection() as connection:
        cursor = connection.execute("DELETE FROM analyses")
        return int(cursor.rowcount)


def get_history_stats() -> dict[str, int]:
    with _connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT app_id) AS unique_apps,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) AS high_risk,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) AS medium_risk,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) AS low_risk
            FROM analyses
            """
        ).fetchone()

    return {
        "total": int(row["total"] or 0),
        "unique_apps": int(row["unique_apps"] or 0),
        "high_risk": int(row["high_risk"] or 0),
        "medium_risk": int(row["medium_risk"] or 0),
        "low_risk": int(row["low_risk"] or 0),
    }


def list_tracked_apps() -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT
                app_id,
                MAX(app_name) AS app_name,
                COUNT(*) AS analysis_count,
                MAX(analyzed_at) AS latest_analysis
            FROM analyses
            GROUP BY app_id
            ORDER BY latest_analysis DESC
            """
        ).fetchall()

    return [
        {
            "app_id": str(row["app_id"]),
            "app_name": str(row["app_name"]),
            "analysis_count": int(row["analysis_count"]),
            "latest_analysis": str(row["latest_analysis"]),
        }
        for row in rows
    ]


def get_app_trend(app_id: str) -> list[dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT
                analyzed_at,
                risk_score,
                transparency_score,
                negative_percentage
            FROM analyses
            WHERE app_id = ?
            ORDER BY analyzed_at ASC, id ASC
            """,
            (app_id,),
        ).fetchall()

    return [
        {
            "analyzed_at": str(row["analyzed_at"]),
            "risk_score": int(row["risk_score"]),
            "transparency_score": int(row["transparency_score"]),
            "negative_percentage": float(row["negative_percentage"]),
        }
        for row in rows
    ]
