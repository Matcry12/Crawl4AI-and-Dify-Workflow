from pydantic import BaseModel, Field

class ResultSchema(BaseModel):
    title: str = Field(
        ..., 
        description="The primary and most prominent title of the content, typically an H1 or headline. Should reflect the main topic or theme of the page."
    )
    name: str = Field(
        None, 
        description="The specific name of a product, person, company, or service mentioned in the content. Only include if clearly identifiable and distinct from the title."
    )
    description: str = Field(
        None, 
        description="A comprehensive narrative containing ALL information from the page, organized in sections separated by \\n\\n for optimal Dify.ai chunking. Include: overview (paragraph 1), core facts/features (paragraph 2), people/dates/events (paragraph 3), keywords/categories embedded naturally (paragraph 4), statistics/data (paragraph 5), context/background (paragraph 6), significance/impact (paragraph 7). Total 300-800 words."
    )