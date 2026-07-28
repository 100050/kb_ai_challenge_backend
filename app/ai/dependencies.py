from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.services.analysis import AnalysisService


@dataclass
class ChatDependencies:
    analysis_id: UUID
    analysis_service: AnalysisService
    analysis_context: dict[str, Any]
