from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class SocialDebtCause(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"

class ClassificationRequest(BaseModel):
    text: str = Field(..., description="The GitHub comment or text to be classified.")

class ClassificationResponse(BaseModel):
    cause: SocialDebtCause = Field(..., description="The identified sociotechnical cause of Social Debt.")
    confidence: float = Field(..., description="Confidence score of the classification.", ge=0.0, le=1.0)
    reasoning: Optional[str] = Field(None, description="Brief reasoning for the classification.")
