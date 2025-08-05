from pydantic import BaseModel, Field
from typing import List, Optional

class ComprehensiveResultSchema(BaseModel):
    """Enhanced schema to capture comprehensive website information"""
    
    title: str = Field(
        ..., 
        description="The primary title or headline of the page"
    )
    
    name: Optional[str] = Field(
        None, 
        description="Specific entity name (person, product, company) if different from title"
    )
    
    description: str = Field(
        ..., 
        description="Comprehensive summary capturing ALL key information including: main purpose, important facts, key people/dates/events, notable features, achievements, and relevant context. Should be 200-500 words."
    )
    
    category: Optional[str] = Field(
        None,
        description="Primary category or type of content (e.g., biography, tutorial, product, news)"
    )
    
    keywords: Optional[List[str]] = Field(
        default_factory=list,
        description="5-10 key terms or topics that represent the core content"
    )
    
    key_facts: Optional[List[str]] = Field(
        default_factory=list,
        description="Bullet points of the most important facts or takeaways"
    )
    
    url: Optional[str] = Field(
        None,
        description="Source URL of the content"
    )
    
    metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Additional structured data like dates, locations, numbers, etc."
    )