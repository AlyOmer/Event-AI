from pydantic import BaseModel

from .vendor import VendorRead


class VendorWithScore(BaseModel):
    vendor: VendorRead
    similarity_score: float  # cosine similarity in [0.0, 1.0]
    search_mode: str  # "keyword" | "semantic" | "hybrid"

    model_config = {"from_attributes": True}
