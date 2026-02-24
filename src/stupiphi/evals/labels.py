from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

LabelType = Literal["PHONE", "EMAIL", "NAME"]


@dataclass(frozen=True)
class InjectedLabel:
    """
    Ground-truth label for evaluation. These are tokens we purposely inject.
    """
    label_type: LabelType
    value: str
    field_path: str = "encounter_notes"
    
    start: Optional[int] = None
    end: Optional[int] = None
