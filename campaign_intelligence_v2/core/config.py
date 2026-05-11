"""
core/config.py -- v2
Single source of truth for every threshold, model name, and constant.
"""
from __future__ import annotations

# LLM
LLM_MODEL: str         = "gpt-4o-mini"
LLM_TEMPERATURE: float = 0.1
LLM_MAX_TOKENS: int    = 2048

# Graph control-loop limits
MAX_VALIDATION_RETRIES: int  = 2   # kept for compat
MAX_DATA_RETRIES: int        = 1   # DataQualityGate retry cap
MAX_CRITIC_ATTEMPTS: int     = 1   # Critic loop cap
CONFIDENCE_THRESHOLD: int    = 55  # strategist must reach this score

# Database
VALID_CAMPAIGN_CODES: list[str] = ["CA01", "CA02", "CA03", "CA04", "CA05", "CA06"]
TIME_PERIOD_COLUMNS:  list[str] = ["baseline", "week_4", "week_8", "week_12", "current_value"]
TIME_PERIOD_LABELS:   list[str] = ["Baseline", "Week 4", "Week 8", "Week 12", "Current"]
