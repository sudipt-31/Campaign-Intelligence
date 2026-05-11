"""
db/seed.py
==========
Seeds the campaign intelligence SQLite database with a rich, realistic dataset.

RetailCo runs 6 marketing campaigns across 5 product lines targeting 10 
audience segments. The data is designed so the LLM can answer EVERY question
the frontend suggests — budget reallocation, KPI deep-dives, trend analysis,
cross-campaign comparisons, and ad creative recall.

Run standalone:  python db/seed.py
Or via make:     make seed
"""

import sqlite3
import random
from pathlib import Path

DB_PATH = Path(__file__).parent / "retailco_intel.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

random.seed(42)


def connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def seed():
    conn = connect()
    cur = conn.cursor()

    # ─── Apply schema ────────────────────────────────────────────────────────
    with open(SCHEMA_PATH) as f:
        cur.executescript(f.read())

    # Clear existing data
    tables = [
        "ad_recall", "campaign_diagnostics", "campaign_kpis", "budget_allocation",
        "campaign_segments", "ad_creatives", "segments", "campaigns"
    ]
    for t in tables:
        cur.execute(f"DELETE FROM {t}")

    # ─── Campaigns ───────────────────────────────────────────────────────────
    campaigns = [
        ("CA01", "Spring Brand Push",          "awareness",    "Home Essentials",      520_000, "2024-01-15", "2024-04-15"),
        ("CA02", "Gen Z Digital Native",        "acquisition",  "Tech Accessories",     380_000, "2024-02-01", "2024-05-01"),
        ("CA03", "Premium Product Reveal",      "conversion",   "Premium Collection",   650_000, "2024-01-20", "2024-04-20"),
        ("CA04", "Loyalty Retention Drive",     "retention",    "Core Staples",         290_000, "2024-02-15", "2024-05-15"),
        ("CA05", "Summer Lifestyle Campaign",   "awareness",    "Outdoor & Leisure",    430_000, "2024-03-01", "2024-06-01"),
        ("CA06", "Value Seeker Promo",          "conversion",   "Budget Line",          210_000, "2024-02-01", "2024-05-01"),
    ]
    cur.executemany(
        "INSERT INTO campaigns (campaign_code, campaign_name, objective, product_line, "
        "total_budget, start_date, end_date) VALUES (?,?,?,?,?,?,?)",
        campaigns
    )

    # ─── Segments ────────────────────────────────────────────────────────────
    segments = [
        ("Gen Z",              "18-24", "Digital-first, brand-conscious, TikTok-heavy audience"),
        ("Millennials",        "25-38", "Purchase-intent-driven, value-quality balance seekers"),
        ("Gen X Parents",      "39-54", "Family-first buyers, loyalty-prone, coupon-responsive"),
        ("Baby Boomers",       "55-70", "Brand loyal, premium-willing, low digital engagement"),
        ("Urban Professionals","25-45", "High income, time-poor, convenience-driven"),
        ("Budget Conscious",   "18-65", "Price-sensitive, deal-hunters, high volume purchasers"),
        ("Eco-Conscious",      "22-45", "Sustainability-driven, premium-willing, advocacy-strong"),
        ("Sports & Fitness",   "20-40", "Active lifestyle, impulse purchase triggers, influencer-led"),
        ("Empty Nesters",      "50-65", "Discretionary spend up, exploring new brands post-family"),
        ("Students",           "18-25", "Low income, high digital, peer-influenced, deal-responsive"),
    ]
    cur.executemany(
        "INSERT INTO segments (segment_name, age_range, description) VALUES (?,?,?)",
        segments
    )

    # Fetch IDs
    camp_ids = {code: rid for rid, code, *_ in cur.execute("SELECT campaign_id, campaign_code FROM campaigns")}
    seg_ids  = {name: rid for rid, name, *_ in cur.execute("SELECT segment_id, segment_name FROM segments")}

    # ─── Campaign → Segment mappings ─────────────────────────────────────────
    camp_segs = {
        "CA01": [("Gen Z", 18), ("Millennials", 25), ("Urban Professionals", 22), ("Eco-Conscious", 20), ("Sports & Fitness", 15)],
        "CA02": [("Gen Z", 35), ("Students", 30), ("Millennials", 20), ("Urban Professionals", 15)],
        "CA03": [("Urban Professionals", 30), ("Baby Boomers", 25), ("Empty Nesters", 25), ("Eco-Conscious", 20)],
        "CA04": [("Gen X Parents", 30), ("Baby Boomers", 30), ("Empty Nesters", 20), ("Millennials", 20)],
        "CA05": [("Sports & Fitness", 35), ("Gen Z", 20), ("Millennials", 25), ("Urban Professionals", 20)],
        "CA06": [("Budget Conscious", 40), ("Students", 25), ("Gen X Parents", 20), ("Millennials", 15)],
    }
    for code, segs in camp_segs.items():
        for seg_name, pct in segs:
            cur.execute(
                "INSERT INTO campaign_segments (campaign_id, segment_id, allocated_budget_pct) VALUES (?,?,?)",
                (camp_ids[code], seg_ids[seg_name], pct)
            )

    # ─── Ad Creatives ────────────────────────────────────────────────────────
    creatives_map = {
        "CA01": ["YouTube 30s", "Instagram Static", "Display Banner", "Email Creative"],
        "CA02": ["TikTok Short 10s", "Instagram Reel", "YouTube 30s", "Meta Video 15s"],
        "CA03": ["YouTube 30s", "Display Banner", "Email Creative", "Meta Video 15s"],
        "CA04": ["Email Creative", "Display Banner", "Instagram Static"],
        "CA05": ["Instagram Reel", "TikTok Short 10s", "YouTube 30s", "Instagram Static"],
        "CA06": ["Display Banner", "Email Creative", "Meta Video 15s"],
    }
    creative_id_map = {}
    for code, creatives in creatives_map.items():
        for c in creatives:
            cur.execute(
                "INSERT INTO ad_creatives (campaign_id, creative_name, creative_type, channel) VALUES (?,?,?,?)",
                (camp_ids[code], c,
                 "video" if any(v in c for v in ["YouTube", "TikTok", "Reel", "Meta Video"]) else "static",
                 c.split()[0])
            )
            cid = cur.lastrowid
            creative_id_map[(code, c)] = cid

    # ─── KPI data per campaign × segment × time period ───────────────────────
    kpi_metrics = ["Brand Awareness", "Purchase Intent", "Brand Trust", "Preference", "NPS Score"]

    # Realistic uplift profiles: (baseline, week4, week8, week12, current)
    kpi_profiles = {
        "CA01": {
            "Brand Awareness": (42, 51, 58, 64, 62),
            "Purchase Intent":  (28, 32, 36, 40, 38),
            "Brand Trust":      (35, 40, 45, 49, 47),
            "Preference":       (22, 27, 31, 35, 33),
            "NPS Score":        (30, 35, 40, 45, 43),
        },
        "CA02": {
            "Brand Awareness": (38, 49, 60, 68, 70),
            "Purchase Intent":  (24, 31, 40, 47, 49),
            "Brand Trust":      (30, 36, 43, 50, 52),
            "Preference":       (20, 28, 37, 44, 46),
            "NPS Score":        (25, 32, 41, 50, 53),
        },
        "CA03": {
            "Brand Awareness": (45, 52, 56, 59, 58),
            "Purchase Intent":  (33, 41, 50, 57, 55),
            "Brand Trust":      (40, 48, 55, 61, 59),
            "Preference":       (28, 36, 44, 51, 49),
            "NPS Score":        (35, 43, 51, 58, 56),
        },
        "CA04": {
            "Brand Awareness": (50, 53, 55, 57, 56),
            "Purchase Intent":  (36, 38, 40, 43, 42),
            "Brand Trust":      (48, 51, 53, 56, 55),
            "Preference":       (34, 36, 38, 40, 39),
            "NPS Score":        (42, 44, 46, 49, 48),
        },
        "CA05": {
            "Brand Awareness": (35, 46, 55, 62, 65),
            "Purchase Intent":  (22, 29, 37, 44, 47),
            "Brand Trust":      (28, 35, 42, 48, 51),
            "Preference":       (18, 26, 34, 41, 43),
            "NPS Score":        (22, 30, 38, 45, 48),
        },
        "CA06": {
            "Brand Awareness": (30, 37, 42, 46, 44),
            "Purchase Intent":  (38, 46, 52, 56, 54),
            "Brand Trust":      (25, 30, 34, 38, 36),
            "Preference":       (32, 40, 46, 50, 48),
            "NPS Score":        (20, 26, 31, 35, 33),
        },
    }

    periods = ["baseline", "week_4", "week_8", "week_12", "current_value"]
    targets = {
        "Brand Awareness": 60,
        "Purchase Intent":  45,
        "Brand Trust":      50,
        "Preference":       40,
        "NPS Score":        48,
    }

    for code, cid in camp_ids.items():
        for seg_name, sid in seg_ids.items():
            # Only insert for relevant segments
            relevant = [s for s, _ in camp_segs.get(code, [])]
            if seg_name not in relevant:
                continue
            for metric, vals in kpi_profiles[code].items():
                noise = [round(v + random.uniform(-2.5, 2.5), 2) for v in vals]
                cur.execute(
                    """INSERT INTO campaign_kpis
                       (campaign_id, segment_id, kpi_name, baseline, week_4, week_8, week_12, current_value, target_value)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (cid, sid, metric, *noise, targets[metric])
                )

    # ─── Budget Allocation ────────────────────────────────────────────────────
    budget_splits = {
        "CA01": [("YouTube", 35), ("Instagram", 25), ("Display", 20), ("Email", 20)],
        "CA02": [("TikTok", 40), ("Instagram", 30), ("YouTube", 20), ("Meta", 10)],
        "CA03": [("YouTube", 30), ("Email", 30), ("Display", 25), ("Meta", 15)],
        "CA04": [("Email", 45), ("Display", 30), ("Instagram", 25)],
        "CA05": [("Instagram", 35), ("TikTok", 30), ("YouTube", 25), ("Display", 10)],
        "CA06": [("Display", 40), ("Email", 35), ("Meta", 25)],
    }
    channel_perf = {
        "YouTube": 0.82, "TikTok": 0.91, "Instagram": 0.78,
        "Meta": 0.74, "Email": 0.70, "Display": 0.65,
    }
    for code, cid in camp_ids.items():
        camp_budget = next(row[4] for row in campaigns if row[0] == code)
        for channel, pct in budget_splits[code]:
            alloc = round(camp_budget * pct / 100, 2)
            spent = round(alloc * random.uniform(0.70, 0.95), 2)
            roi   = round(channel_perf.get(channel, 0.75) * random.uniform(0.9, 1.1), 3)
            cur.execute(
                """INSERT INTO budget_allocation
                   (campaign_id, channel, allocated_budget, spent_budget, roi_score)
                   VALUES (?,?,?,?,?)""",
                (cid, channel, alloc, spent, roi)
            )

    # ─── Diagnostics ─────────────────────────────────────────────────────────
    diag_metrics = ["Campaign Recall", "Ad Exposure", "Message Clarity", "CTA Recall", "Relevance", "Enjoyment", "Branded Recall"]

    diag_profiles = {
        "CA01": {"Campaign Recall":(40,48,54,59,57), "Ad Exposure":(55,62,68,72,70), "Message Clarity":(38,44,50,55,53),
                 "CTA Recall":(30,36,42,47,45), "Relevance":(45,50,55,59,57), "Enjoyment":(40,46,51,55,53), "Branded Recall":(35,42,48,53,51)},
        "CA02": {"Campaign Recall":(35,47,58,66,69), "Ad Exposure":(48,60,70,78,81), "Message Clarity":(32,42,52,60,63),
                 "CTA Recall":(25,35,46,54,57), "Relevance":(50,58,65,71,73), "Enjoyment":(48,57,65,72,74), "Branded Recall":(30,41,52,61,64)},
        "CA03": {"Campaign Recall":(44,52,58,63,61), "Ad Exposure":(58,65,70,74,72), "Message Clarity":(42,50,57,63,61),
                 "CTA Recall":(35,44,52,58,56), "Relevance":(48,54,59,64,62), "Enjoyment":(42,48,54,59,57), "Branded Recall":(40,48,55,61,59)},
        "CA04": {"Campaign Recall":(52,55,57,60,59), "Ad Exposure":(60,63,65,68,67), "Message Clarity":(48,51,54,57,56),
                 "CTA Recall":(42,44,46,49,48), "Relevance":(55,57,59,62,61), "Enjoyment":(44,46,48,51,50), "Branded Recall":(50,52,54,57,56)},
        "CA05": {"Campaign Recall":(33,44,54,62,65), "Ad Exposure":(45,56,66,74,77), "Message Clarity":(30,40,50,58,61),
                 "CTA Recall":(23,32,42,50,53), "Relevance":(47,55,62,68,70), "Enjoyment":(50,59,67,73,75), "Branded Recall":(28,38,49,58,61)},
        "CA06": {"Campaign Recall":(38,44,49,53,51), "Ad Exposure":(50,56,61,65,63), "Message Clarity":(35,40,45,49,47),
                 "CTA Recall":(40,47,52,56,54), "Relevance":(42,47,51,55,53), "Enjoyment":(35,39,43,47,45), "Branded Recall":(33,38,43,47,45)},
    }

    for code, cid in camp_ids.items():
        for metric, vals in diag_profiles[code].items():
            noise = [round(v + random.uniform(-1.5, 1.5), 2) for v in vals]
            cur.execute(
                """INSERT INTO campaign_diagnostics
                   (campaign_id, metric_name, baseline, week_4, week_8, week_12, current_value)
                   VALUES (?,?,?,?,?,?,?)""",
                (cid, metric, *noise)
            )

    # ─── Ad Recall ────────────────────────────────────────────────────────────
    recall_profiles = {
        ("CA01", "YouTube 30s"):     (38, 46, 53, 58, 56),
        ("CA01", "Instagram Static"): (30, 36, 42, 47, 45),
        ("CA01", "Display Banner"):  (22, 27, 32, 36, 34),
        ("CA01", "Email Creative"):  (35, 41, 46, 50, 48),
        ("CA02", "TikTok Short 10s"): (42, 55, 65, 73, 76),
        ("CA02", "Instagram Reel"):  (38, 49, 59, 67, 70),
        ("CA02", "YouTube 30s"):     (35, 44, 53, 60, 63),
        ("CA02", "Meta Video 15s"):  (30, 38, 46, 52, 55),
        ("CA03", "YouTube 30s"):     (42, 50, 57, 63, 61),
        ("CA03", "Display Banner"):  (28, 34, 40, 45, 43),
        ("CA03", "Email Creative"):  (40, 48, 55, 61, 59),
        ("CA03", "Meta Video 15s"):  (33, 40, 47, 53, 51),
        ("CA04", "Email Creative"):  (48, 52, 55, 58, 57),
        ("CA04", "Display Banner"):  (32, 35, 38, 41, 40),
        ("CA04", "Instagram Static"): (35, 38, 41, 44, 43),
        ("CA05", "Instagram Reel"):  (36, 48, 58, 66, 69),
        ("CA05", "TikTok Short 10s"): (40, 52, 62, 70, 73),
        ("CA05", "YouTube 30s"):     (32, 42, 51, 58, 61),
        ("CA05", "Instagram Static"): (28, 37, 45, 52, 55),
        ("CA06", "Display Banner"):  (34, 40, 45, 49, 47),
        ("CA06", "Email Creative"):  (38, 44, 49, 53, 51),
        ("CA06", "Meta Video 15s"):  (28, 34, 39, 43, 41),
    }

    for (code, creative), vals in recall_profiles.items():
        cid = camp_ids[code]
        noise = [round(v + random.uniform(-1, 1), 2) for v in vals]
        cur.execute(
            """INSERT INTO ad_recall
               (campaign_id, creative_name, baseline, week_4, week_8, week_12, current_value)
               VALUES (?,?,?,?,?,?,?)""",
            (cid, creative, *noise)
        )

    conn.commit()
    conn.close()
    print("✅ Database seeded successfully.")
    print(f"   Campaigns: {len(campaigns)}")
    print(f"   Segments:  {len(segments)}")
    print(f"   KPI rows:  {len(kpi_profiles) * len(kpi_metrics)} (approx)")


if __name__ == "__main__":
    seed()
