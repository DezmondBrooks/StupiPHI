import os
import logging
from typing import Literal

try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletionMessage
except ImportError:
    OpenAI = None  # For environments where OpenAI is optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIRedactor:
    def __init__(self, provider: Literal["openai", "local"] = "openai", model="gpt-4o"):
        self.provider = provider
        self.model = model

        if provider == "openai":
            if not OpenAI:
                raise ImportError("OpenAI module not installed. Run `pip install openai`.")

            # Skip API key check during testing if OpenAI is mocked
            if not os.getenv("OPENAI_API_KEY") and not getattr(OpenAI, "__mock__", False):
                raise ValueError("Missing OPENAI_API_KEY environment variable")

            self.client = OpenAI()

    def redact_text(self, text: str) -> str:
        if self.provider == "openai":
            return self._redact_with_openai(text)
        elif self.provider == "local":
            return self._redact_with_local_model(text)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _redact_with_openai(self, text: str) -> str:
        prompt = f"""Redact any personally identifiable health information (PII/PHI) from the text below.
Replace names, dates, locations, IDs with fake but realistic data. Preserve sentence structure.

Text:
{text}

Redacted:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI redaction failed: {e}")
            return "[ERROR: Redaction failed]"

    def _redact_with_local_model(self, text: str) -> str:
        logger.warning("Local AI redaction not yet implemented. Returning input unchanged.")
        return text
