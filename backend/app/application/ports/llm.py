"""LLM port — interface for language model invocation."""

from typing import Protocol


class LLMPort(Protocol):
    """Port for invoking a language model.

    Encapsulates LLM selection (Ollama/Azure OpenAI), timeout handling,
    and trace metadata capture.
    """

    async def invoke(
        self,
        prompt: str,
        agent_name: str,
        timeout: float | None = None,
    ) -> tuple[str | None, dict]:
        """Invoke the LLM with a prompt and return response + trace metadata.

        Args:
            prompt: Formatted prompt string.
            agent_name: Name of the calling agent (for logging/tracing).
            timeout: Optional timeout override in seconds.

        Returns:
            Tuple of (response_content, trace_metadata).
            response_content is None on failure (timeout, error).
            trace_metadata always contains llm_prompt, llm_model, etc.
        """
        ...
