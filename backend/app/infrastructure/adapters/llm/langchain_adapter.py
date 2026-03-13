"""LangChain LLM adapter — implements LLMPort with ChatOllama/ChatOpenAI."""

import asyncio

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.domain.constants import AGENT_TIMEOUTS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LangChainLLMAdapter:
    """LLMPort implementation backed by LangChain chat models.

    Encapsulates LLM factory logic, timeout handling, and trace metadata capture.
    """

    def __init__(
        self,
        *,
        use_azure_openai: bool = False,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "qwen3:30b",
        azure_openai_endpoint: str = "",
        azure_openai_api_key: str = "",
        azure_openai_deployment: str = "gpt-5.2-chat",
    ):
        self._use_azure = use_azure_openai
        self._ollama_base_url = ollama_base_url
        self._ollama_model = ollama_model
        self._azure_endpoint = azure_openai_endpoint
        self._azure_api_key = azure_openai_api_key
        self._azure_deployment = azure_openai_deployment
        self._llm: BaseChatModel | None = None

    @property
    def llm(self) -> BaseChatModel:
        """Lazily create and cache the LLM instance."""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> BaseChatModel:
        if self._use_azure:
            if not self._azure_endpoint:
                raise ValueError("USE_AZURE_OPENAI=true but AZURE_OPENAI_ENDPOINT not configured")

            base_url = self._azure_endpoint.rstrip("/") + "/openai/v1/"
            return ChatOpenAI(
                base_url=base_url,
                api_key=self._azure_api_key,
                model=self._azure_deployment,
            )
        else:
            return ChatOllama(
                base_url=self._ollama_base_url,
                model=self._ollama_model,
                temperature=0.1,
            )

    async def invoke(
        self,
        prompt: str,
        agent_name: str,
        timeout: float | None = None,
    ) -> tuple[str | None, dict]:
        """Invoke the LLM with timeout, returning response content and trace metadata."""
        effective_timeout = timeout or AGENT_TIMEOUTS.llm_call
        llm = self.llm

        llm_trace: dict = {
            "llm_prompt": prompt,
            "llm_model": getattr(llm, "model", None) or getattr(llm, "deployment_name", "unknown"),
            "llm_temperature": getattr(llm, "temperature", 0.0),
        }

        try:
            response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=effective_timeout)

            llm_trace["llm_response_raw"] = response.content

            if hasattr(response, "response_metadata"):
                usage = response.response_metadata.get("usage", {})
                llm_trace["llm_tokens_used"] = usage.get("total_tokens")

            return response.content, llm_trace

        except asyncio.TimeoutError:
            logger.error("llm_timeout", agent=agent_name, timeout_seconds=effective_timeout)
            llm_trace["llm_response_raw"] = f"TIMEOUT after {effective_timeout}s"
            return None, llm_trace
        except Exception as e:
            logger.error("llm_call_failed", agent=agent_name, error=str(e))
            llm_trace["llm_response_raw"] = f"ERROR: {e}"
            return None, llm_trace
