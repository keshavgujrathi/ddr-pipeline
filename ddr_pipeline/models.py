from pydantic import BaseModel
from typing import Literal
from enum import Enum
from datetime import datetime, timezone

class ImageRef(BaseModel):
    page: int
    index: int
    caption: str
    area_tag: str
    b64: str

class RawObservation(BaseModel):
    source: Literal["inspection", "thermal"]
    area: str
    text: str
    page: int
    images: list[ImageRef] = []

class ExtractionResult(BaseModel):
    source_file: str
    doc_type: Literal["inspection", "thermal"]
    observations: list[RawObservation]
    all_images: list[ImageRef]
    raw_text_by_page: dict[int, str]

class ConflictNote(BaseModel):
    field: str
    inspection_says: str
    thermal_says: str

class MergedObservation(BaseModel):
    area: str
    inspection_texts: list[str]
    thermal_texts: list[str]
    images: list[ImageRef] = []
    conflicts: list[ConflictNote] = []
    missing: list[str] = []

class FusionResult(BaseModel):
    property_id: str
    areas: list[MergedObservation]
    unmatched_inspection: list[RawObservation] = []
    unmatched_thermal: list[RawObservation] = []
    global_images: list[ImageRef] = []

class SeverityLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"
    INFORMATIONAL = "Informational"

class AreaReport(BaseModel):
    area: str
    observations: str
    probable_root_cause: str
    severity: SeverityLevel
    severity_reasoning: str
    recommended_actions: list[str]
    images: list[ImageRef] = []
    conflicts_noted: list[str] = []
    missing_info: list[str] = []

class DDRReport(BaseModel):
    property_id: str
    generated_at: str
    executive_summary: str
    property_issue_summary: str
    area_reports: list[AreaReport]
    global_recommended_actions: list[str]
    additional_notes: str
    missing_or_unclear: list[str]
