from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class SocialDebtCause(str, Enum):
    A = "A" # Type dependencies, interfaces, and architecture
    B = "B" # Code and repository quality, structure, and traceability
    C = "C" # Context, documentation, and communication dependencies
    D = "D" # Logical or temporal execution, and testing dependencies
    E = "E" # Expertise and support dependencies
    F = "F" # Task allocation and scheduling dependencies
    G = "G" # Resource, tooling, access, and validation dependencies
    H = "H" # No identificable

class ClassificationRequest(BaseModel):
    text: str = Field(..., description="The GitHub comment or text to be classified.")

class ClassificationResponse(BaseModel):
    cause: SocialDebtCause = Field(..., description="The identified sociotechnical cause of Social Debt.")
    confidence: float = Field(..., description="Confidence score of the classification.", ge=0.0, le=1.0)
    reasoning: Optional[str] = Field(None, description="Brief reasoning for the classification.")
