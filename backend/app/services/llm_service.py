"""LLM service backed by Groq's OpenAI-compatible chat completions API."""
import base64
import json
import mimetypes
import time
from typing import Iterator

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for text generation, summaries, and extraction via Groq."""

    def __init__(self):
        self.model_name = settings.GROQ_MODEL
        self.api_key = settings.GROQ_API_KEY
        self.base_url = settings.GROQ_BASE_URL.rstrip("/")
        self.max_retries = settings.LLM_MAX_RETRIES
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
        """Generate text from Groq with simple retry logic."""
        if not self.api_key:
            return "Groq API key is not configured. Set GROQ_API_KEY in your .env file."

        if retries is None:
            retries = self.max_retries

        for attempt in range(retries + 1):
            try:
                logger.info(
                    "Generating content with Groq (%s), attempt %s/%s",
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
                    logger.error("Groq request timed out after retries")
                    return "The language model timed out. Please try again."
                time.sleep(2 ** attempt)
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:500]
                logger.error("Groq HTTP error: %s", detail)
                if attempt == retries:
                    return f"Groq request failed: {exc.response.status_code} - {detail}"
                time.sleep(2 ** attempt)
            except Exception as exc:
                logger.error("Groq generation failed: %s", exc)
                if attempt == retries:
                    return f"Error generating content: {exc}"
                time.sleep(2 ** attempt)

        return "Failed to generate content."

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Yield text chunks as Groq streams them."""
        if not self.api_key:
            yield "Groq API key is not configured. Set GROQ_API_KEY in your .env file."
            return

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(prompt, stream=True),
                ) as response:
                    if response.status_code >= 400:
                        # Read the (non-streamed) error body before raising so the
                        # actual Groq error message reaches the log/response instead
                        # of a bare status code.
                        response.read()
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
            detail = exc.response.text[:500]
            logger.error("Groq streaming HTTP error: %s", detail)
            yield f"\n\nGroq request failed: {exc.response.status_code} - {detail}"
        except Exception as exc:
            logger.error("Groq streaming generation failed: %s", exc)
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
            "provider": "Groq",
        }

    def describe_image(self, image_path: str) -> str:
        """Describe an image's visual contents (and transcribe any visible text)
        using Groq's vision model. Unlike OCR, this actually understands photos,
        charts, and scenes — not just text that happens to appear in the image.
        Returns "" on any failure so callers can fall back gracefully.
        """
        if not self.api_key:
            return ""
        try:
            mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            with open(image_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": settings.GROQ_VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Describe this image in detail for someone who cannot see "
                                    "it: what it shows, any objects, people, or scenes, the "
                                    "layout, and colors. Then transcribe any visible text "
                                    "verbatim under a 'Text in image:' heading, or omit that "
                                    "heading if there is none."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                            },
                        ],
                    }
                ],
                "temperature": settings.LLM_TEMPERATURE,
                "max_completion_tokens": 1024,
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
            return self._extract_text(response.json())
        except Exception as exc:
            logger.error("Groq vision description failed: %s", exc)
            return ""
