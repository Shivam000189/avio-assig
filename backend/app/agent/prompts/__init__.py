"""Prompts package for LangGraph analysis nodes."""

from app.agent.prompts.capa_prompt import CAPA_SCHEMA_HINT, CAPA_SYSTEM_PROMPT
from app.agent.prompts.completeness_prompt import (
    COMPLETENESS_SCHEMA_HINT,
    COMPLETENESS_SYSTEM_PROMPT,
)
from app.agent.prompts.duplicate_prompt import (
    DUPLICATE_SCHEMA_HINT,
    DUPLICATE_SYSTEM_PROMPT,
)
from app.agent.prompts.extract_prompt import (
    EXTRACT_SCHEMA_HINT,
    EXTRACT_SYSTEM_PROMPT,
)
from app.agent.prompts.risk_assess_prompt import (
    RISK_ASSESS_SCHEMA_HINT,
    RISK_ASSESS_SYSTEM_PROMPT,
)
from app.agent.prompts.root_cause_prompt import (
    ROOT_CAUSE_SCHEMA_HINT,
    ROOT_CAUSE_SYSTEM_PROMPT,
)
from app.agent.prompts.summarize_prompt import (
    SUMMARIZE_SCHEMA_HINT,
    SUMMARIZE_SYSTEM_PROMPT,
)

__all__ = [
    "CAPA_SCHEMA_HINT",
    "CAPA_SYSTEM_PROMPT",
    "COMPLETENESS_SCHEMA_HINT",
    "COMPLETENESS_SYSTEM_PROMPT",
    "DUPLICATE_SCHEMA_HINT",
    "DUPLICATE_SYSTEM_PROMPT",
    "EXTRACT_SCHEMA_HINT",
    "EXTRACT_SYSTEM_PROMPT",
    "RISK_ASSESS_SCHEMA_HINT",
    "RISK_ASSESS_SYSTEM_PROMPT",
    "ROOT_CAUSE_SCHEMA_HINT",
    "ROOT_CAUSE_SYSTEM_PROMPT",
    "SUMMARIZE_SCHEMA_HINT",
    "SUMMARIZE_SYSTEM_PROMPT",
]
