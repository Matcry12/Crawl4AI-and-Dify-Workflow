#!/usr/bin/env python3
"""Simple test of the analysis prompt."""

import json

# Sample content that should clearly be SINGLE_TOPIC
test_content = """
# Brontosaurus

The Brontosaurus is a Mythical pet in Grow a Garden.

## Overview
The Brontosaurus is one of the prehistoric pets available during special events.

## Habitat
Brontosaurus prefers warm, humid environments with plenty of vegetation.

## Diet  
As a herbivore, the Brontosaurus feeds on:
- Tall trees and ferns
- Various prehistoric plants
- Special garden vegetables

## Behavior
The Brontosaurus is generally peaceful and:
- Moves slowly through the garden
- Helps fertilize plants with its droppings
- Can reach high branches to prune trees

## How to Obtain
Players can obtain a Brontosaurus by:
1. Participating in the Prehistoric Event
2. Hatching from Dino Eggs
3. Trading with other players
"""

# Create the analysis prompt
prompt = """You are an expert content analyzer for RAG (Retrieval-Augmented Generation) systems.

IMPORTANT: Focus on the MAIN ARTICLE CONTENT, ignoring navigation menus, sidebars, footers, and ads.

Analyze the provided content and determine:

1. CONTENT VALUE for AI/RAG:
   - HIGH: Tutorials, documentation, guides, technical content, educational material, unique information
   - MEDIUM: General articles, news, reviews with some informational value  
   - LOW: Navigation pages, brief announcements, minimal content
   - SKIP: Error pages, login pages, pure navigation, advertisements, cookie notices

2. CONTENT STRUCTURE - Look at the MAIN CONTENT ONLY:
   - SINGLE_TOPIC: The main article/content is about ONE subject
     * Wiki page about Brontosaurus (even with sections like History, Habitat, Diet) = SINGLE_TOPIC
     * Tutorial about Python (with multiple chapters/sections) = SINGLE_TOPIC
     * Product documentation (with features, setup, usage sections) = SINGLE_TOPIC
     * ANY Wikipedia-style article about one thing = SINGLE_TOPIC
   
   - MULTI_TOPIC: The page contains MULTIPLE SEPARATE articles or very different topics
     * Homepage with different news articles = MULTI_TOPIC
     * Blog index with multiple unrelated posts = MULTI_TOPIC
     * Page with "Python Tutorial" AND "Cooking Recipes" as separate articles = MULTI_TOPIC
     * Documentation hub covering completely different products = MULTI_TOPIC

3. RECOMMENDED MODE:
   - FULL_DOC: Use when the main content is about ONE topic
     * Wiki article about an animal/person/place/thing = FULL_DOC
     * Tutorial or guide (even with many sections) = FULL_DOC
     * Documentation for one product/API = FULL_DOC
     * Blog post about one subject = FULL_DOC
   
   - PARAGRAPH: Use ONLY when page has MULTIPLE DISTINCT topics/articles
     * Homepage with different article previews = PARAGRAPH
     * Search results page = PARAGRAPH
     * Category page listing different items = PARAGRAPH

DECISION RULE:
Ask yourself: "Is this page's MAIN CONTENT about ONE thing or MULTIPLE different things?"
- ONE thing (even with subsections like History, Features, Usage) → FULL_DOC
- MULTIPLE different things → PARAGRAPH

CRITICAL: 
- Different sections about the SAME topic (e.g., Habitat and Diet of Brontosaurus) = STILL ONE TOPIC = FULL_DOC
- Navigation elements don't count as "different topics"
- Focus on the actual article/content, not the page structure

Analyze the content and provide structured assessment.

URL: https://growagarden.fandom.com/wiki/Brontosaurus

CONTENT:
""" + test_content + """

Please analyze this content and provide your response in the following JSON format:
{
    "content_value": "high|medium|low|skip",
    "value_reason": "Brief explanation",
    "content_structure": "single_topic|multi_topic|reference|list|mixed",
    "structure_reason": "Brief explanation", 
    "main_topics": ["topic1", "topic2"],
    "recommended_mode": "full_doc|paragraph",
    "mode_reason": "Detailed explanation of why this mode is recommended",
    "content_type": "Type of content",
    "has_code": false,
    "is_navigational": false
}"""

print("Test Prompt:")
print("=" * 80)
print(prompt)
print("=" * 80)
print("\nExpected output:")
print("- content_structure: single_topic (it's about ONE dinosaur)")
print("- recommended_mode: full_doc (all sections are about the same Brontosaurus)")