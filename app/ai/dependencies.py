from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.services.analysis import AnalysisService
from app.services.evaluation import EvaluationService


@dataclass
class ChatDependencies:
    analysis_id: UUID
    analysis_service: AnalysisService
    evaluation_service: EvaluationService
    analysis_context: dict[str, Any]
