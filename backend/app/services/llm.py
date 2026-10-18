from abc import ABC, abstractmethod
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class LLMProvider(ABC):
    """Interface for a future model provider. Answers must be grounded in supplied context."""

    name = "custom"

    @abstractmethod
    def answer(self, question: str, passages: list[dict]) -> str:
        raise NotImplementedError


class ExtractiveProvider(LLMProvider):
    """Useful local fallback until a user-supplied LLM is configured."""

    name = "retrieval-only"

    def answer(self, question: str, passages: list[dict]) -> str:
        if not passages:
            return "I couldn't find a relevant passage in the indexed documents. Try rephrasing the question or upload the filing that contains the information."
        return (
            "No LLM response is available, so this is a retrieval-only response. "
            "The passages below are the closest matches to your question; review the cited excerpts for the source wording."
        )


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url or None)
        self.model = model

    def answer(self, question: str, passages: list[dict]) -> str:
        if not passages:
            return ExtractiveProvider().answer(question, passages)

        source_context = "\n\n".join(
            f"[{index}] {passage['filename']}"
            + (f", page {passage['page']}" if passage["page"] else "")
            + f"\n{passage['content']}"
            for index, passage in enumerate(passages, start=1)
        )
        prompt = (
            "Answer the user's question using only the source excerpts below. "
            "If the excerpts do not contain enough information, say so. Do not invent facts. "
            "Cite claims with the matching bracketed source number, such as [1].\n\n"
            f"Question: {question}\n\nSource excerpts:\n{source_context}"
        )
        response = self.client.responses.create(model=self.model, input=prompt)
        if not response.output_text:
            raise RuntimeError("OpenAI returned an empty response.")
        return response.output_text.strip()


def get_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider_name in {"", "retrieval-only"}:
        return ExtractiveProvider()
    if provider_name == "openai":
        api_key = os.getenv("LLM_API_KEY", "").strip()
        if not api_key:
            return ExtractiveProvider()
        model = os.getenv("LLM_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
        base_url = os.getenv("LLM_BASE_URL", "").strip()
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url or None)
    raise ValueError(f"Unsupported LLM_PROVIDER '{provider_name}'. Set it to 'openai' or 'retrieval-only'.")