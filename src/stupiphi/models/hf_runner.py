from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from transformers import pipeline


@dataclass(frozen=True)
class HFEntity:
    """
    Normalized entity output from Hugging Face token-classification models.
    """
    label: str
    start: int
    end: int
    score: float
    text: str


class HFTokenClassifier:
    """
    Small wrapper around Hugging Face token-classification pipeline.
    Keeps model usage isolated so the rest of the system doesn't depend on HF details.
    """

    def __init__(
        self,
        model_name: str = "dslim/bert-base-NER",
        device: int = -1,  # -1 CPU, 0+ GPU
    ) -> None:
        self.model_name = model_name
        self._pipe = pipeline(
            "token-classification",
            model=model_name,
            aggregation_strategy="simple",
            device=device,
        )

    def predict(self, text: str) -> List[HFEntity]:
        """
        Return a list of normalized entity spans.
        """
        if not text.strip():
            return []

        raw: List[Dict[str, Any]] = self._pipe(text)  # type: ignore[assignment]
        entities: List[HFEntity] = []

        for r in raw:
            start = int(r.get("start", 0))
            end = int(r.get("end", 0))
            label = str(r.get("entity_group") or r.get("entity") or "UNKNOWN")
            score = float(r.get("score", 0.0))
            span_text = text[start:end] if 0 <= start <= end <= len(text) else str(r.get("word", ""))

            entities.append(
                HFEntity(
                    label=label,
                    start=start,
                    end=end,
                    score=score,
                    text=span_text,
                )
            )

        return entities
