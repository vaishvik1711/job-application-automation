"""
Centralized LLM client with structured output support.
"""
import os
import json
import asyncio
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_retries: int = 3,
        timeout: int = 180,
        max_tokens: int = 16000,
    ):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("ANTHROPIC_MODEL") or os.getenv("LLM_MODEL")
        if not self.model:
            raise ValueError(
                "No LLM model configured. Set ANTHROPIC_MODEL in .claude/settings.json "
                "(or set the LLM_MODEL env var, or pass model= to LLMClient constructor)."
            )
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured. Set it in .env or pass to constructor.")

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ValidationError, json.JSONDecodeError, ConnectionError)),
    )
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        temperature: Optional[float] = None,
    ) -> T:
        """Generate structured JSON output validated against a Pydantic schema."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        try:
            data = json.loads(content)
            return schema(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            # Log the raw response for debugging
            raise ValueError(f"Failed to parse LLM response as {schema.__name__}: {e}\nResponse: {content}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate free-form text output."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")
        return content

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Type[T]] = None,
        temperature: Optional[float] = None,
    ) -> T | str:
        """Generate either structured or free-form output."""
        if schema:
            return await self.generate_json(system_prompt, user_prompt, schema, temperature)
        return await self.generate_text(system_prompt, user_prompt, temperature)


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def set_llm_client(client: LLMClient) -> None:
    global _llm_client
    _llm_client = client