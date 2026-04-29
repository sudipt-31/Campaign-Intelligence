"""
data_loader.py
──────────────
Single source of truth for all DB access.
Points to: au_topline.db  (SQLite, bundled in the backend folder)

Tables
──────
campaigns            campaign_id | campaign_code | campaign_name
target_groups        tg_id | campaign_id | tg_name
marketing_kpis       id | tg_id | metric | seen | not_seen | uplift | desired_uplift
campaign_diagnostics id | tg_id | metric | norm | dec_25 | fn1_jan_26 | jan_26 | to_date
ad_recall            id | tg_id | ad_creative | norm | dec_25 | fn1_jan_26 | jan_26 | to_date

Views (query-ready)
───────────────────
v_marketing_kpis_full  → kpis + campaign + tg names
v_full_data            → diagnostics + ad_recall + campaign + tg names
"""
import sqlite3
import pathlib
from functools import lru_cache
from typing import Any

_DB_PATH = pathlib.Path(__file__).parent / "au_topline.db"


# ── low-level helpers ────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    if not _DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {_DB_PATH}. "
            "Make sure au_topline.db is in the backend/ folder."
        )
    c = sqlite3.connect(str(_DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _q(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def _scalar(sql: str, params: tuple = ()):
    with _conn() as c:
        row = c.execute(sql, params).fetchone()
        return row[0] if row else None


# ── metadata (cached once on startup) ───────────────────────────────────────

@lru_cache(maxsize=1)
def get_data_summary() -> dict:
    """Full snapshot of what lives in the DB — used by agents to understand scope."""
    campaigns = _q("SELECT campaign_id, campaign_code, campaign_name FROM campaigns ORDER BY campaign_id")
    tgs       = _q("""
        SELECT t.tg_id, t.tg_name, c.campaign_name
        FROM   target_groups t
        JOIN   campaigns c USING (campaign_id)
        ORDER  BY t.campaign_id, t.tg_id
    """)
    kpi_metrics  = [r["metric"] for r in _q("SELECT DISTINCT metric FROM marketing_kpis  ORDER BY metric")]
    diag_metrics = [r["metric"] for r in _q("SELECT DISTINCT metric FROM campaign_diagnostics ORDER BY metric")]
    ad_creatives = [r["ad_creative"] for r in _q("SELECT DISTINCT ad_creative FROM ad_recall ORDER BY ad_creative")]

    # row counts
    counts = {
        tbl: _scalar(f"SELECT COUNT(*) FROM {tbl}")
        for tbl in ("campaigns", "target_groups", "marketing_kpis",
                    "campaign_diagnostics", "ad_recall")
    }

    return {
        "total_campaigns":   len(campaigns),
        "campaigns":         [c["campaign_name"]  for c in campaigns],
        "campaign_codes":    [c["campaign_code"]  for c in campaigns],
        "segments":          list({t["tg_name"]   for t in tgs}),           # unique segment names
        "campaign_segments": [f"{t['campaign_name']} → {t['tg_name']}" for t in tgs],
        "kpi_metrics":       kpi_metrics,
        "diagnostic_metrics": diag_metrics,
        "ad_creatives":      ad_creatives,
        "time_periods":      ["norm", "dec_25", "fn1_jan_26", "jan_26", "to_date"],
        "row_counts":        counts,
        "table_descriptions": {
            "marketing_kpis":
                "Brand-lift KPIs per campaign × segment. "
                "Columns: seen (exposed audience score), not_seen (control), "
                "uplift (seen − not_seen delta), desired_uplift (target). "
                "Metrics include: Preference, Relevance, Brand Trust, Purchase Intent, etc.",
            "campaign_diagnostics":
                "Diagnostic scores over time (norm / dec_25 / fn1_jan_26 / jan_26 / to_date). "
                "Metrics: Campaign Recall, Ad Exposure, Branding, Ease of Understanding, "
                "Key Message recall, Relevancy, Enjoyable/Appealing.",
            "ad_recall":
                "Per-creative recall rates over time periods. "
                "One row per ad creative × target group.",
        },
    }


# ── marketing_kpis queries ───────────────────────────────────────────────────

def get_kpis_for_campaign(campaign_name: str) -> list[dict]:
    return _q("""
        SELECT c.campaign_name, t.tg_name, m.metric,
               ROUND(m.seen,          4) AS seen,
               ROUND(m.not_seen,      4) AS not_seen,
               ROUND(m.uplift,        4) AS uplift,
               m.desired_uplift
        FROM   marketing_kpis m
        JOIN   target_groups  t ON t.tg_id      = m.tg_id
        JOIN   campaigns      c ON c.campaign_id = t.campaign_id
        WHERE  LOWER(c.campaign_name) LIKE LOWER(?)
        ORDER  BY t.tg_name, m.metric
    """, (f"%{campaign_name}%",))


def get_kpis_for_segment(tg_name: str) -> list[dict]:
    return _q("""
        SELECT c.campaign_name, t.tg_name, m.metric,
               ROUND(m.seen,     4) AS seen,
               ROUND(m.not_seen, 4) AS not_seen,
               ROUND(m.uplift,   4) AS uplift,
               m.desired_uplift
        FROM   marketing_kpis m
        JOIN   target_groups  t ON t.tg_id      = m.tg_id
        JOIN   campaigns      c ON c.campaign_id = t.campaign_id
        WHERE  LOWER(t.tg_name) LIKE LOWER(?)
        ORDER  BY c.campaign_name, m.metric
    """, (f"%{tg_name}%",))


def get_uplift_per_campaign() -> list[dict]:
    """Average uplift per campaign (all metrics + segments aggregated)."""
    return _q("""
        SELECT c.campaign_name,
               ROUND(AVG(m.uplift),   4) AS avg_uplift,
               ROUND(AVG(m.seen),     4) AS avg_seen,
               ROUND(AVG(m.not_seen), 4) AS avg_not_seen,
               COUNT(DISTINCT t.tg_id)   AS segment_count,
               COUNT(*)                  AS metric_rows
        FROM   marketing_kpis m
        JOIN   target_groups  t ON t.tg_id      = m.tg_id
        JOIN   campaigns      c ON c.campaign_id = t.campaign_id
        WHERE  m.uplift IS NOT NULL
        GROUP  BY c.campaign_name
        ORDER  BY avg_uplift DESC
    """)


def get_uplift_by_metric_campaign() -> list[dict]:
    """Uplift for every campaign × metric (heatmap view)."""
    return _q("""
        SELECT c.campaign_name, m.metric,
               ROUND(AVG(m.uplift), 4) AS avg_uplift,
               COUNT(*)                AS n
        FROM   marketing_kpis m
        JOIN   target_groups  t ON t.tg_id      = m.tg_id
        JOIN   campaigns      c ON c.campaign_id = t.campaign_id
        WHERE  m.uplift IS NOT NULL
        GROUP  BY c.campaign_name, m.metric
        ORDER  BY c.campaign_name, avg_uplift DESC
    """)


def get_preference_comparison() -> list[dict]:
    return _q("""
        SELECT c.campaign_name, t.tg_name,
               ROUND(m.seen,   4) AS preference_seen,
               ROUND(m.uplift, 4) AS preference_uplift
        FROM   marketing_kpis m
        JOIN   target_groups  t ON t.tg_id      = m.tg_id
        JOIN   campaigns      c ON c.campaign_id = t.campaign_id
        WHERE  LOWER(m.metric) = 'preference'
        ORDER  BY m.uplift DESC
    """)


def get_top_uplift_rows(top_n: int = 10) -> list[dict]:
    return _q("""
        SELECT c.campaign_name, t.tg_name, m.metric,
               ROUND(m.uplift, 4) AS uplift
        FROM   marketing_kpis m
        JOIN   target_groups  t ON t.tg_id      = m.tg_id
        JOIN   campaigns      c ON c.campaign_id = t.campaign_id
        WHERE  m.uplift IS NOT NULL
        ORDER  BY m.uplift DESC
        LIMIT  ?
    """, (top_n,))


def get_negative_uplift_rows() -> list[dict]:
    return _q("""
        SELECT c.campaign_name, t.tg_name, m.metric,
               ROUND(m.uplift, 4) AS uplift
        FROM   marketing_kpis m
        JOIN   target_groups  t ON t.tg_id      = m.tg_id
        JOIN   campaigns      c ON c.campaign_id = t.campaign_id
        WHERE  m.uplift < 0
        ORDER  BY m.uplift ASC
    """)


# ── campaign_diagnostics queries ─────────────────────────────────────────────

def get_diagnostics_for_campaign(campaign_name: str) -> list[dict]:
    return _q("""
        SELECT c.campaign_name, t.tg_name, d.metric,
               ROUND(d.norm,       4) AS norm,
               ROUND(d.dec_25,     4) AS dec_25,
               ROUND(d.fn1_jan_26, 4) AS fn1_jan_26,
               ROUND(d.jan_26,     4) AS jan_26,
               ROUND(d.to_date,    4) AS to_date
        FROM   campaign_diagnostics d
        JOIN   target_groups t ON t.tg_id      = d.tg_id
        JOIN   campaigns     c ON c.campaign_id = t.campaign_id
        WHERE  LOWER(c.campaign_name) LIKE LOWER(?)
          AND  d.metric NOT IN ('Base', 'Campaign recallers Base')
        ORDER  BY t.tg_name, d.metric
    """, (f"%{campaign_name}%",))


def get_recall_trend() -> list[dict]:
    """Campaign Recall across all time periods for every campaign × segment."""
    return _q("""
        SELECT c.campaign_name, t.tg_name,
               ROUND(d.norm,       4) AS norm,
               ROUND(d.dec_25,     4) AS dec_25,
               ROUND(d.fn1_jan_26, 4) AS fn1_jan_26,
               ROUND(d.jan_26,     4) AS jan_26,
               ROUND(d.to_date,    4) AS to_date
        FROM   campaign_diagnostics d
        JOIN   target_groups t ON t.tg_id      = d.tg_id
        JOIN   campaigns     c ON c.campaign_id = t.campaign_id
        WHERE  d.metric = 'Campaign Recall'
        ORDER  BY c.campaign_name, t.tg_name
    """)


def get_diagnostics_vs_norm() -> list[dict]:
    """to_date − norm for every non-base diagnostic metric, sorted best→worst."""
    return _q("""
        SELECT c.campaign_name, t.tg_name, d.metric,
               ROUND(d.norm,             4) AS norm,
               ROUND(d.to_date,          4) AS to_date,
               ROUND(d.to_date - d.norm, 4) AS vs_norm
        FROM   campaign_diagnostics d
        JOIN   target_groups t ON t.tg_id      = d.tg_id
        JOIN   campaigns     c ON c.campaign_id = t.campaign_id
        WHERE  d.norm    IS NOT NULL
          AND  d.to_date IS NOT NULL
          AND  d.metric  NOT IN ('Base', 'Campaign recallers Base')
        ORDER  BY vs_norm DESC
    """)


# ── ad_recall queries ────────────────────────────────────────────────────────

def get_ad_recall_for_campaign(campaign_name: str) -> list[dict]:
    return _q("""
        SELECT c.campaign_name, t.tg_name, a.ad_creative,
               ROUND(a.norm,       4) AS norm,
               ROUND(a.dec_25,     4) AS dec_25,
               ROUND(a.fn1_jan_26, 4) AS fn1_jan_26,
               ROUND(a.jan_26,     4) AS jan_26,
               ROUND(a.to_date,    4) AS to_date
        FROM   ad_recall     a
        JOIN   target_groups t ON t.tg_id      = a.tg_id
        JOIN   campaigns     c ON c.campaign_id = t.campaign_id
        WHERE  LOWER(c.campaign_name) LIKE LOWER(?)
        ORDER  BY t.tg_name, a.ad_creative
    """, (f"%{campaign_name}%",))


def get_ad_recall_vs_norm() -> list[dict]:
    """to_date − norm for every ad creative across all campaigns, ranked."""
    return _q("""
        SELECT c.campaign_name, t.tg_name, a.ad_creative,
               ROUND(a.norm,             4) AS norm,
               ROUND(a.to_date,          4) AS to_date,
               ROUND(a.to_date - a.norm, 4) AS vs_norm
        FROM   ad_recall     a
        JOIN   target_groups t ON t.tg_id      = a.tg_id
        JOIN   campaigns     c ON c.campaign_id = t.campaign_id
        WHERE  a.norm    IS NOT NULL
          AND  a.to_date IS NOT NULL
        ORDER  BY vs_norm DESC
    """)