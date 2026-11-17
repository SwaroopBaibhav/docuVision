from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedData(BaseModel):
    """
    This is our strict schema. If the AI outputs something that doesn't 
    match this, Pydantic will throw an error, which triggers our retry loop.
    """
    document_id: Optional[str] = Field(description="Any visible ID, invoice number, or reference number")
    total_amount: Optional[float] = Field(description="The total monetary amount, if applicable")
    date: Optional[str] = Field(description="The date of the document")
    key_entities: List[str] = Field(description="List of organizations, people, or items mentioned")