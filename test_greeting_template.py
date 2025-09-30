#!/usr/bin/env python3

"""
Test script for greeting template integration
"""

from chat_with_p2 import P2ChatSession, load_p2_profile
from bfi_probe import LLM, LLMConfig

def test_greeting_responses():
    print("🧪 Testing Greeting Template Integration")
    print("=" * 50)
    
    # Load a P2 profile
    p2_prompt = load_p2_profile("results/p2_prompt_20250924_191704.txt")
    if not p2_prompt:
        print("❌ Failed to load P2 profile")
        return
    
    print(f"✅ Loaded P2 profile ({len(p2_prompt)} chars)")
    
    # Initialize chat session
    llm = LLM(LLMConfig(model="gpt-4o-mini", temperature=0.8), debug=True)
    chat_session = P2ChatSession(p2_prompt, llm, debug=True)
    
    # Test different greeting messages
    test_greetings = [
        "Hey",
        "Hi!",
        "Hello",
        "What's up?",
        "Hey, how's it going?",
        "Good morning",
        "Hi there"
    ]
    
    print(f"🎯 Testing {len(test_greetings)} greeting messages:")
    print()
    
    for i, greeting in enumerate(test_greetings, 1):
        print(f"Test {i}/7: User says '{greeting}'")
        
        try:
            # Clear conversation history for each test
            chat_session.conversation_history = []
            
            response = chat_session.chat_response(greeting)
            print(f"✅ Response: '{response}'")
            
            # Check if response follows template
            starts_with_hey = response.lower().startswith('hey')
            is_brief = len(response.split()) <= 10  # Roughly 1-2 sentences
            
            print(f"   📝 Starts with 'Hey': {'✅' if starts_with_hey else '❌'}")
            print(f"   📏 Brief response: {'✅' if is_brief else '❌'}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)
        print()

if __name__ == "__main__":
    test_greeting_responses()