from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMConfig, DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import LLMContentFilter
import os
import asyncio

async def main():
    # Initialize LLM filter with specific instruction
    api_key = os.getenv('OPENROUTER_API_KEY')
    filter = LLMContentFilter(
        llm_config = LLMConfig(provider="openai/gpt-4o-mini",api_token=api_key), #or use environment variable
        instruction="""
        Focus on extracting the core educational content.
        Include:
        - Key concepts and explanations
        - Important code examples
        - Essential technical details
        Exclude:
        - Navigation elements
        - Sidebars
        - Footer content
        Format the output as clean markdown with proper code blocks and headers.
        """,
        chunk_token_threshold=4096,  # Adjust based on your needs
        verbose=True
    )
    md_generator = DefaultMarkdownGenerator(
        content_filter=filter,
        options={"ignore_links": True}
    )
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://en.wikipedia.org/wiki/Google", config=config)
        print(result.markdown.fit_markdown)  # Filtered markdown content
if __name__ == "__main__":
    asyncio.run(main()) 