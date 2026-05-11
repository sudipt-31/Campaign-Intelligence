"""
db/loader.py
============
All SQL query functions.  No SQL lives anywhere else.
Every function returns list[dict] or dict — no raw sqlite3.Row objects escape.
Parameters always use ? placeholders — never f-string SQL.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional


DB_PATH = Path(__file__).parent / "retailco_intel.db"

VALID_CAMPAIGN_CODES = ["CA01", "CA02", "CA03", "CA04", "CA05", "CA06"]
TIME_PERIODS         = ["baseline", "week_4", "week_8", "week_12", "current_value"]
TIME_LABELS          = ["Baseline", "Week 4", "Week 8", "Week 12", "Current"]


# ─── Connection ──────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _rows(cur: sqlite3.Cursor) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


# ─── A. Catalogue ────────────────────────────────────────────────────────────

def get_all_campaigns() -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute("SELECT * FROM campaigns ORDER BY campaign_code"))


def get_all_segments() -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute("SELECT * FROM segments ORDER BY segment_name"))


def get_campaign_by_code(code: str) -> Optional[dict]:
    with _connect() as conn:
        rows = _rows(conn.execute(
            "SELECT * FROM campaigns WHERE campaign_code = ?", (code,)
        ))
        return rows[0] if rows else None


def get_segments_for_campaign(code: str) -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT s.segment_name, s.age_range, s.description, cs.allocated_budget_pct
               FROM campaign_segments cs
               JOIN campaigns c ON c.campaign_id = cs.campaign_id
               JOIN segments  s ON s.segment_id  = cs.segment_id
               WHERE c.campaign_code = ?
               ORDER BY cs.allocated_budget_pct DESC""",
            (code,)
        ))


# ─── B. KPI functions ────────────────────────────────────────────────────────

def get_kpis_for_campaign(code: str) -> list[dict]:
    """All KPI rows for a campaign, averaged across segments."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT kpi_name,
                      ROUND(AVG(baseline),2)      AS baseline,
                      ROUND(AVG(week_4),2)         AS week_4,
                      ROUND(AVG(week_8),2)         AS week_8,
                      ROUND(AVG(week_12),2)        AS week_12,
                      ROUND(AVG(current_value),2)  AS current_value,
                      ROUND(AVG(target_value),2)   AS target_value
               FROM campaign_kpis ck
               JOIN campaigns c ON c.campaign_id = ck.campaign_id
               WHERE c.campaign_code = ?
               GROUP BY kpi_name
               ORDER BY kpi_name""",
            (code,)
        ))


def get_kpis_for_campaign_segment(code: str, segment: str) -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT kpi_name, baseline, week_4, week_8, week_12, current_value, target_value
               FROM campaign_kpis ck
               JOIN campaigns c ON c.campaign_id = ck.campaign_id
               JOIN segments  s ON s.segment_id  = ck.segment_id
               WHERE c.campaign_code = ? AND s.segment_name = ?
               ORDER BY kpi_name""",
            (code, segment)
        ))


def get_brand_uplift_all_campaigns() -> list[dict]:
    """Uplift (current - baseline) for every campaign, every KPI."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name, kpi_name,
                      ROUND(AVG(baseline),2)     AS baseline,
                      ROUND(AVG(current_value),2) AS current_value,
                      ROUND(AVG(current_value - baseline),2) AS uplift,
                      ROUND(AVG(target_value),2) AS target_value
               FROM campaign_kpis ck
               JOIN campaigns c ON c.campaign_id = ck.campaign_id
               GROUP BY c.campaign_code, kpi_name
               ORDER BY uplift DESC"""
        ))


def get_target_vs_actual(code: Optional[str] = None) -> list[dict]:
    """Whether KPI targets were hit (current_value >= target_value)."""
    sql = """
        SELECT c.campaign_code, c.campaign_name, kpi_name,
               ROUND(AVG(current_value),2) AS actual,
               ROUND(AVG(target_value),2)  AS target,
               CASE WHEN AVG(current_value) >= AVG(target_value) THEN 1 ELSE 0 END AS achieved
        FROM campaign_kpis ck
        JOIN campaigns c ON c.campaign_id = ck.campaign_id
        {where}
        GROUP BY c.campaign_code, kpi_name
        ORDER BY c.campaign_code, kpi_name
    """
    if code:
        with _connect() as conn:
            return _rows(conn.execute(sql.format(where="WHERE c.campaign_code = ?"), (code,)))
    else:
        with _connect() as conn:
            return _rows(conn.execute(sql.format(where="")))


def get_kpi_comparison_all() -> list[dict]:
    """Single row per campaign with current value for each KPI — great for tables."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name, c.objective,
                      ROUND(MAX(CASE WHEN kpi_name='Brand Awareness'  THEN current_value END),2) AS brand_awareness,
                      ROUND(MAX(CASE WHEN kpi_name='Purchase Intent'  THEN current_value END),2) AS purchase_intent,
                      ROUND(MAX(CASE WHEN kpi_name='Brand Trust'      THEN current_value END),2) AS brand_trust,
                      ROUND(MAX(CASE WHEN kpi_name='Preference'       THEN current_value END),2) AS preference,
                      ROUND(MAX(CASE WHEN kpi_name='NPS Score'        THEN current_value END),2) AS nps_score
               FROM campaign_kpis ck
               JOIN campaigns c ON c.campaign_id = ck.campaign_id
               GROUP BY c.campaign_code
               ORDER BY brand_awareness DESC"""
        ))


# ─── C. Budget functions ─────────────────────────────────────────────────────

def get_budget_for_campaign(code: str) -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT ba.channel, ba.allocated_budget, ba.spent_budget, ba.roi_score,
                      ROUND(ba.spent_budget / ba.allocated_budget * 100, 1) AS burn_pct
               FROM budget_allocation ba
               JOIN campaigns c ON c.campaign_id = ba.campaign_id
               WHERE c.campaign_code = ?
               ORDER BY ba.allocated_budget DESC""",
            (code,)
        ))


def get_budget_summary_all() -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name, c.objective,
                      c.total_budget,
                      ROUND(SUM(ba.allocated_budget),2) AS total_allocated,
                      ROUND(SUM(ba.spent_budget),2)     AS total_spent,
                      ROUND(SUM(ba.spent_budget)/SUM(ba.allocated_budget)*100,1) AS burn_pct,
                      ROUND(AVG(ba.roi_score),3)        AS avg_roi
               FROM budget_allocation ba
               JOIN campaigns c ON c.campaign_id = ba.campaign_id
               GROUP BY c.campaign_code
               ORDER BY avg_roi DESC"""
        ))


def get_top_roi_channels() -> list[dict]:
    """Rank channels across all campaigns by average ROI."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT channel,
                      ROUND(AVG(roi_score),3)         AS avg_roi,
                      ROUND(SUM(spent_budget),0)      AS total_spent,
                      COUNT(*)                         AS appearances
               FROM budget_allocation
               GROUP BY channel
               ORDER BY avg_roi DESC"""
        ))


# ─── D. Diagnostics (Trend) ──────────────────────────────────────────────────

def get_diagnostics_for_campaign(code: str) -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT metric_name, baseline, week_4, week_8, week_12, current_value,
                      ROUND(current_value - baseline, 2) AS total_change
               FROM campaign_diagnostics cd
               JOIN campaigns c ON c.campaign_id = cd.campaign_id
               WHERE c.campaign_code = ?
               ORDER BY total_change DESC""",
            (code,)
        ))


def get_diagnostics_all_campaigns() -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name, metric_name,
                      ROUND(baseline,2) AS baseline,
                      ROUND(current_value,2) AS current_value,
                      ROUND(current_value - baseline,2) AS change
               FROM campaign_diagnostics cd
               JOIN campaigns c ON c.campaign_id = cd.campaign_id
               ORDER BY c.campaign_code, metric_name"""
        ))


def get_trend_direction_all() -> list[dict]:
    """Simple trend: is the campaign going up, down or flat week 8→current?"""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name,
                      ROUND(AVG(week_8),2)        AS avg_week8,
                      ROUND(AVG(current_value),2) AS avg_current,
                      ROUND(AVG(current_value - week_8),2) AS recent_change,
                      CASE
                        WHEN AVG(current_value) > AVG(week_8) + 1 THEN 'up'
                        WHEN AVG(current_value) < AVG(week_8) - 1 THEN 'down'
                        ELSE 'flat'
                      END AS trend_direction
               FROM campaign_diagnostics cd
               JOIN campaigns c ON c.campaign_id = cd.campaign_id
               GROUP BY c.campaign_code
               ORDER BY recent_change DESC"""
        ))


# ─── E. Ad Recall ────────────────────────────────────────────────────────────

def get_ad_recall_for_campaign(code: str) -> list[dict]:
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT ar.creative_name, ar.baseline, ar.week_4, ar.week_8,
                      ar.week_12, ar.current_value,
                      ROUND(ar.current_value - ar.baseline, 2) AS uplift
               FROM ad_recall ar
               JOIN campaigns c ON c.campaign_id = ar.campaign_id
               WHERE c.campaign_code = ?
               ORDER BY ar.current_value DESC""",
            (code,)
        ))


def get_top_ad_recall_all() -> list[dict]:
    """Best-performing ad creatives by current recall, across all campaigns."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name, ar.creative_name,
                      ROUND(ar.baseline,2)       AS baseline,
                      ROUND(ar.current_value,2)  AS current_recall,
                      ROUND(ar.current_value - ar.baseline,2) AS uplift
               FROM ad_recall ar
               JOIN campaigns c ON c.campaign_id = ar.campaign_id
               ORDER BY ar.current_value DESC
               LIMIT 20"""
        ))


# ─── F. Cross-campaign views ─────────────────────────────────────────────────

def get_campaign_summary_view() -> list[dict]:
    """Single rich summary row per campaign for frontend dataset/info."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name, c.objective, c.product_line,
                      c.total_budget,
                      ROUND(AVG(ck.current_value),2)         AS avg_kpi_current,
                      ROUND(AVG(ck.baseline),2)               AS avg_kpi_baseline,
                      ROUND(AVG(ck.current_value - ck.baseline),2) AS avg_uplift
               FROM campaigns c
               LEFT JOIN campaign_kpis ck ON ck.campaign_id = c.campaign_id
               GROUP BY c.campaign_code
               ORDER BY avg_uplift DESC"""
        ))


def get_segment_performance(segment_name: str) -> list[dict]:
    """How each campaign performs for a given segment."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name, ck.kpi_name,
                      ROUND(ck.baseline,2)      AS baseline,
                      ROUND(ck.current_value,2) AS current_value,
                      ROUND(ck.current_value - ck.baseline,2) AS uplift,
                      ck.target_value
               FROM campaign_kpis ck
               JOIN campaigns c ON c.campaign_id = ck.campaign_id
               JOIN segments  s ON s.segment_id  = ck.segment_id
               WHERE s.segment_name = ?
               ORDER BY uplift DESC""",
            (segment_name,)
        ))


def get_anomalies() -> list[dict]:
    """High recall but low purchase intent — classic diagnostic anomaly."""
    with _connect() as conn:
        return _rows(conn.execute(
            """SELECT c.campaign_code, c.campaign_name,
                      ROUND(AVG(CASE WHEN kpi_name='Brand Awareness' THEN current_value END),2) AS awareness,
                      ROUND(AVG(CASE WHEN kpi_name='Purchase Intent'  THEN current_value END),2) AS purchase_intent,
                      ROUND(AVG(CASE WHEN kpi_name='Brand Trust'      THEN current_value END),2) AS brand_trust
               FROM campaign_kpis ck
               JOIN campaigns c ON c.campaign_id = ck.campaign_id
               GROUP BY c.campaign_code
               HAVING awareness > 55 AND purchase_intent < 45
               ORDER BY awareness DESC"""
        ))
