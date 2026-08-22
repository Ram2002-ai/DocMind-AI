"""LLM service backed by the OpenRouter chat completions API."""
import json
import time
from pathlib import Path
from typing import Iterator

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for text generation, summaries, and extraction via OpenRouter."""

    def __init__(self):
        self.model_name = settings.OPENROUTER_MODEL
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL.rstrip("/")
        self.max_retries = settings.LLM_MAX_RETRIES
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        # Local development keeps the shared LLM setting at the repository
        # root while the backend uses its own .env for database settings.
        if not self.api_key:
            try:
                from dotenv import dotenv_values

                root_env = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
                self.api_key = root_env.get("OPENROUTER_API_KEY", "")
                self.model_name = root_env.get("OPENROUTER_MODEL", self.model_name)
                self.base_url = root_env.get("OPENROUTER_BASE_URL", self.base_url).rstrip("/")
            except Exception as exc:
                logger.warning("Unable to load local LLM configuration: %s", exc)

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
        if settings.OPENROUTER_APP_NAME:
            headers["X-Title"] = settings.OPENROUTER_APP_NAME
        return headers

    def _payload(self, prompt: str, stream: bool = False) -> dict:
        return {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "stream": stream,
            "provider": {
                "sort": settings.OPENROUTER_PROVIDER_SORT,
                "allow_fallbacks": True,
            },
        }

    def _extract_text(self, data: dict) -> str:
        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            return "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )
        return content or ""

    def generate(self, prompt: str, retries: int = None) -> str:
        """Generate text from OpenRouter with simple retry logic."""
        if not self.api_key:
            return "OpenRouter API key is not configured."

        if retries is None:
            retries = self.max_retries

        for attempt in range(retries + 1):
            try:
                logger.info(
                    "Generating content with OpenRouter (%s), attempt %s/%s",
                    self.model_name,
                    attempt + 1,
                    retries + 1,
                )
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=self._payload(prompt),
                    )
                    response.raise_for_status()
                text = self._extract_text(response.json())
                if text:
                    return text
                return "The model returned an empty response."
            except httpx.TimeoutException:
                if attempt == retries:
                    logger.error("OpenRouter request timed out after retries")
                    return "The language model timed out. Please try again."
                time.sleep(2 ** attempt)
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:500]
                logger.error("OpenRouter HTTP error: %s", detail)
                if attempt == retries:
                    return f"OpenRouter request failed: {exc.response.status_code}"
                time.sleep(2 ** attempt)
            except Exception as exc:
                logger.error("OpenRouter generation failed: %s", exc)
                if attempt == retries:
                    return f"Error generating content: {exc}"
                time.sleep(2 ** attempt)

        return "Failed to generate content."

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Yield text chunks as OpenRouter streams them."""
        if not self.api_key:
            yield "OpenRouter API key is not configured."
            return

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(prompt, stream=True),
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            payload = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        for choice in payload.get("choices", []):
                            delta = choice.get("delta", {})
                            content = delta.get("content")
                            if isinstance(content, str) and content:
                                yield content
                            elif isinstance(content, list):
                                for item in content:
                                    text = item.get("text", "") if isinstance(item, dict) else ""
                                    if text:
                                        yield text
        except httpx.HTTPStatusError as exc:
            logger.error("Streaming generation failed: %s", exc)
            if exc.response.status_code == 402:
                yield "OpenRouter credits are required. Add credits at https://openrouter.ai/settings/credits and try again."
            else:
                yield f"\n\nOpenRouter request failed ({exc.response.status_code}). Please try again."
        except Exception as exc:
            logger.error("Streaming generation failed: %s", exc)
            yield "\n\nUnable to finish the response. Please try again."

    def summarize(self, text: str) -> str:
        """Generate a concise bullet-point summary for a document."""
        prompt = f"""You are an AI document assistant.

Summarize the following document in clear bullet points. Focus on the key information and main ideas.

Document:
{text}

Provide a concise and well-structured summary."""
        return self.generate(prompt)

    def answer_question(self, context: str, question: str) -> str:
        """Answer a question using only the supplied document context."""
        prompt = f"""You are an AI document assistant.

Answer ONLY based on the given context. If the answer is not available in the context, clearly state:
"I couldn't find that information in the document(s)."

Do not make up or assume information not explicitly stated in the context.

Context:
{context}

Question:
{question}

Answer:"""
        return self.generate(prompt)

    def extract_entities_with_llm(self, text: str) -> dict:
        """Extract structured entities from text via the language model."""
        prompt = f"""Extract the following information from the text and return as a JSON object:
- emails: list of email addresses
- phone_numbers: list of phone numbers
- dates: list of dates
- names: list of person names
- organizations: list of organization names
- locations: list of locations

Only extract information explicitly mentioned in the text.

Text:
{text}

Return valid JSON only, no additional text."""
        response = self.generate(prompt)

        try:
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as exc:
            logger.warning("Failed to parse LLM entity extraction response: %s", exc)

        return {}

    def get_model_info(self) -> dict:
        """Get information about the configured model."""
        return {
            "model_name": self.model_name,
            "provider": "OpenRouter",
        }
