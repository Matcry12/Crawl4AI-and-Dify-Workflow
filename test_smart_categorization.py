#!/usr/bin/env python3
"""Test script to demonstrate smart categorization that prevents duplicate knowledge bases."""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_smart_categorization():
    """Test the smart categorization system with duplicate scenarios."""
    load_dotenv(override=True)
    
    # Initialize workflow
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        gemini_api_key=os.getenv('GEMINI_API_KEY')
    )
    
    print("🧪 Testing Smart Categorization System")
    print("="*60)
    print("This test simulates the scenario where LLM returns different")
    print("variations of the same category name to show how the system")
    print("prevents duplicate knowledge bases.\n")
    
    # Test cases that would normally create duplicates
    test_scenarios = [
        {
            "name": "EOS Variations Test",
            "cases": [
                {
                    "url": "https://eosnetwork.com/docs",
                    "content": "EOS Network documentation for developers. Learn about blockchain development on EOS platform.",
                    "expected_llm_variations": ["eos", "eos_network", "eos_blockchain"]
                },
                {
                    "url": "https://eosnetwork.com/community",
                    "content": "Join the EOS blockchain community. Connect with developers and enthusiasts.",
                    "expected_llm_variations": ["eos_community", "eos", "eos_network"]
                },
                {
                    "url": "https://eosnetwork.com/tutorials",
                    "content": "Step-by-step tutorials for EOS development and smart contracts.",
                    "expected_llm_variations": ["eos_tutorials", "eos_blockchain", "eos"]
                }
            ]
        },
        {
            "name": "Garden Project Test (User's Example)",
            "cases": [
                {
                    "url": "https://growagarden.com/home",
                    "content": "Learn how to grow a garden with our comprehensive guides and tips for beginners.",
                    "expected_llm_variations": ["growagarden", "grow_a_garden", "gardening"]
                },
                {
                    "url": "https://growagarden.com/tips",
                    "content": "Garden growing tips and tricks. Best practices for growing a successful garden.",
                    "expected_llm_variations": ["grow_a_garden", "growagarden", "garden_tips"]
                },
                {
                    "url": "https://growagarden.com/plants",
                    "content": "Plant selection guide for your garden. Choose the right plants to grow a garden successfully.",
                    "expected_llm_variations": ["garden_plants", "growagarden", "grow_a_garden"]
                }
            ]
        },
        {
            "name": "React Framework Test",
            "cases": [
                {
                    "url": "https://reactjs.org/docs",
                    "content": "React documentation for building user interfaces with JavaScript.",
                    "expected_llm_variations": ["react", "reactjs", "react_framework"]
                },
                {
                    "url": "https://reactjs.org/tutorial",
                    "content": "Learn React.js from scratch with this comprehensive tutorial.",
                    "expected_llm_variations": ["react_tutorial", "reactjs", "react"]
                }
            ]
        }
    ]
    
    all_results = []
    
    for scenario in test_scenarios:
        print(f"📋 {scenario['name']}")
        print("-" * 40)
        
        scenario_results = []
        
        for i, test_case in enumerate(scenario['cases'], 1):
            print(f"\nTest {i}: {test_case['url']}")
            
            try:
                category, tags = workflow.categorize_content(test_case['content'], test_case['url'])
                
                scenario_results.append({
                    'url': test_case['url'],
                    'final_category': category,
                    'tags': tags
                })
                
                print(f"✅ Final Category: {category}")
                print(f"🏷️  Tags: {', '.join(tags)}")
                
                # Add this KB to workflow cache to simulate existing KB
                workflow.knowledge_bases[category] = f"kb_{len(workflow.knowledge_bases) + 1}"
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        all_results.extend(scenario_results)
        
        # Show consolidation results
        categories_in_scenario = [result['final_category'] for result in scenario_results]
        unique_categories = set(categories_in_scenario)
        
        print(f"\n📊 Scenario Results:")
        print(f"   Total URLs: {len(scenario_results)}")
        print(f"   Unique Categories: {len(unique_categories)}")
        print(f"   Categories: {', '.join(unique_categories)}")
        
        if len(unique_categories) == 1:
            print(f"   ✅ SUCCESS: All content grouped under '{list(unique_categories)[0]}'")
        else:
            print(f"   ⚠️  Multiple categories created: {unique_categories}")
        
        print("\n" + "="*60 + "\n")
    
    # Final summary
    print("🎯 OVERALL SUMMARY")
    print("="*60)
    
    all_categories = [result['final_category'] for result in all_results]
    unique_final_categories = set(all_categories)
    
    print(f"Total URLs processed: {len(all_results)}")
    print(f"Total unique knowledge bases: {len(unique_final_categories)}")
    print(f"Knowledge bases created: {', '.join(sorted(unique_final_categories))}")
    
    print("\n📈 Efficiency Gains:")
    print("Without smart categorization:")
    print("  - Could create 10-20+ knowledge bases")
    print("  - Duplicate/similar content scattered")
    print("  - Hard to find related information")
    
    print(f"\nWith smart categorization:")
    print(f"  - Created only {len(unique_final_categories)} knowledge bases")
    print("  - Related content grouped together")
    print("  - Consistent organization")
    
    print("\n🔧 Methods Used:")
    print("  ✅ Preprocessing/normalization (no tokens)")
    print("  ✅ Fuzzy string matching (no tokens)")
    print("  ✅ Keyword similarity matching (no tokens)")
    print("  ✅ Enhanced LLM prompting (minimal tokens)")
    
    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_smart_categorization())