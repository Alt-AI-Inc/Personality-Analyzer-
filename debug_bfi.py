#!/usr/bin/env python3

"""
Debug script to find where BFI probe is hanging
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from bfi_probe import LLM, LLMConfig

def test_basic_llm():
    print("🧪 Testing basic LLM functionality...")
    
    try:
        cfg = LLMConfig(model="gpt-4o-mini", temperature=0.2, max_tokens=50)
        llm = LLM(cfg, debug=True)
        
        print("✅ LLM initialized successfully")
        
        # Test a simple chat call
        print("🗣️ Testing simple chat...")
        response = llm.chat(
            "You are a helpful assistant.", 
            "Say 'test successful' and nothing else.",
            max_tokens=10,
            temperature=0.0
        )
        
        print(f"✅ Chat response: '{response}'")
        
        # Test loading samples
        print("📝 Testing sample loading...")
        from bfi_probe import load_sample_data
        
        samples = load_sample_data("data/personality_tweets_condensed.json")
        if samples:
            print(f"✅ Loaded samples: {len(samples)} characters")
            print(f"First 100 chars: {samples[:100]}...")
        else:
            print("❌ Failed to load samples")
            return
            
        # Test a single BFI question
        print("❓ Testing single BFI question...")
        from bfi_probe import BFI_S_ITEMS
        
        test_item = BFI_S_ITEMS[0]  # First item
        print(f"Testing item: {test_item['text']}")
        
        system = f"""You are completing a Big Five personality inventory based on writing samples.

WRITING SAMPLES:
{samples[:1000]}...

Answer each question by considering the OVERALL PATTERN in the writing samples.
Rate how accurately each statement describes the author.
Output only A/B/C/D/E where: A=Very Accurate, B=Accurate, C=Neither, D=Inaccurate, E=Very Inaccurate"""

        user = f"""Rate how accurately the statement describes you.
Choose exactly one letter: A=Very Accurate, B=Accurate, C=Neither, D=Inaccurate, E=Very Inaccurate

Statement: {test_item['text']}

Respond with a single letter (A/B/C/D/E) and nothing else."""
        
        response = llm.chat(system, user, max_tokens=8, temperature=0.0)
        print(f"✅ BFI response: '{response}'")
        
        print("🎉 All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_llm()