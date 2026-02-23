"""Shared LLM invocation with timeout and trace metadata.

Eliminates the duplicated asyncio.wait_for + try/except + trace capture
pattern found across policy_rag, external_threat, decision_arbiter,
explainability, and debate_utils.
"""

import asyncio

from langchain_core.language_models import BaseChatModel

from ..constants import AGENT_TIMEOUTS
from .logger import get_logger

logger = get_logger(__name__)


async def invoke_llm_with_timeout(
    llm: BaseChatModel,
    prompt: str,
    *,
    timeout: float = AGENT_TIMEOUTS.llm_call,
    agent_name: str = "unknown",
) -> tuple[str | None, dict]:
    """Invoke an LLM with timeout, returning response content and trace metadata.

    Args:
        llm: LangChain chat model instance.
        prompt: Formatted prompt string.
        timeout: Seconds before giving up.
        agent_name: For structured logging context.

    Returns:
        (response_content, llm_trace) — content is None on failure.
    """
    llm_trace: dict = {
        "llm_prompt": prompt,
        "llm_model": getattr(llm, "model", None) or getattr(llm, "deployment_name", "unknown"),
        "llm_temperature": getattr(llm, "temperature", 0.0),
    }

    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=timeout)

        llm_trace["llm_response_raw"] = response.content

        if hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("usage", {})
            llm_trace["llm_tokens_used"] = usage.get("total_tokens")

        return response.content, llm_trace

    except asyncio.TimeoutError:
        logger.error("llm_timeout", agent=agent_name, timeout_seconds=timeout)
        llm_trace["llm_response_raw"] = f"TIMEOUT after {timeout}s"
        return None, llm_trace
    except Exception as e:
        logger.error("llm_call_failed", agent=agent_name, error=str(e))
        llm_trace["llm_response_raw"] = f"ERROR: {e}"
        return None, llm_trace
