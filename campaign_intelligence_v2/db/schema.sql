-- =============================================================================
-- Campaign Intelligence — RetailCo Database Schema
-- =============================================================================
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys  = ON;

-- ---------------------------------------------------------------------------
-- campaigns
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_code   TEXT    NOT NULL UNIQUE,
    campaign_name   TEXT    NOT NULL,
    objective       TEXT    NOT NULL,   -- awareness / acquisition / retention / conversion
    product_line    TEXT    NOT NULL,
    total_budget    REAL    NOT NULL,
    start_date      TEXT    NOT NULL,
    end_date        TEXT    NOT NULL
);

-- ---------------------------------------------------------------------------
-- segments
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS segments (
    segment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    segment_name    TEXT    NOT NULL UNIQUE,
    age_range       TEXT    NOT NULL,
    description     TEXT    NOT NULL
);

-- ---------------------------------------------------------------------------
-- campaign_segments  (junction)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_segments (
    cs_id               INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id         INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    segment_id          INTEGER NOT NULL REFERENCES segments(segment_id),
    allocated_budget_pct REAL   NOT NULL   -- % of campaign budget for this segment
);

-- ---------------------------------------------------------------------------
-- ad_creatives
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ad_creatives (
    creative_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    creative_name   TEXT    NOT NULL,   -- e.g. "TikTok Short 10s"
    creative_type   TEXT    NOT NULL,   -- video / static
    channel         TEXT    NOT NULL
);

-- ---------------------------------------------------------------------------
-- campaign_kpis
-- Primary KPI brand-health metrics tracked at every time period.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_kpis (
    kpi_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    segment_id      INTEGER NOT NULL REFERENCES segments(segment_id),
    kpi_name        TEXT    NOT NULL,   -- Brand Awareness / Purchase Intent / etc.
    baseline        REAL    NOT NULL,
    week_4          REAL    NOT NULL,
    week_8          REAL    NOT NULL,
    week_12         REAL    NOT NULL,
    current_value   REAL    NOT NULL,
    target_value    REAL    NOT NULL
);

-- ---------------------------------------------------------------------------
-- budget_allocation
-- How the campaign budget was split across channels, and performance.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budget_allocation (
    alloc_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id         INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    channel             TEXT    NOT NULL,
    allocated_budget    REAL    NOT NULL,
    spent_budget        REAL    NOT NULL,
    roi_score           REAL    NOT NULL    -- 0.0–1.0; higher = better return
);

-- ---------------------------------------------------------------------------
-- campaign_diagnostics
-- Diagnostic/recall metrics tracked at every time period.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaign_diagnostics (
    diag_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    metric_name     TEXT    NOT NULL,
    baseline        REAL    NOT NULL,
    week_4          REAL    NOT NULL,
    week_8          REAL    NOT NULL,
    week_12         REAL    NOT NULL,
    current_value   REAL    NOT NULL
);

-- ---------------------------------------------------------------------------
-- ad_recall
-- Creative-level recall scores across time periods.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ad_recall (
    recall_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    creative_name   TEXT    NOT NULL,
    baseline        REAL    NOT NULL,
    week_4          REAL    NOT NULL,
    week_8          REAL    NOT NULL,
    week_12         REAL    NOT NULL,
    current_value   REAL    NOT NULL
);
