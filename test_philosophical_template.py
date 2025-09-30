#!/usr/bin/env python3

"""
Test script for philosophical template integration
"""

from chat_with_p2 import P2ChatSession, load_p2_profile
from bfi_probe import LLM, LLMConfig

def test_philosophical_responses():
    print("🤔 Testing Philosophical Template Integration")
    print("=" * 60)
    
    # Load a P2 profile
    p2_prompt = load_p2_profile("results/p2_prompt_20250924_191704.txt")
    if not p2_prompt:
        print("❌ Failed to load P2 profile")
        return
    
    print(f"✅ Loaded P2 profile ({len(p2_prompt)} chars)")
    
    # Initialize chat session
    llm = LLM(LLMConfig(model="gpt-4o-mini", temperature=0.8), debug=True)
    chat_session = P2ChatSession(p2_prompt, llm, debug=True)
    
    # Test different philosophical questions
    test_questions = [
        "What do you think about the future of AI?",
        "Should we prioritize growth over stability?", 
        "How do you see this trend evolving?",
        "What's your take on remote work?",
        "Do you believe this approach will work?",
        "What would you do in this situation?",
        "Why do you think this is happening?",
        "What's the best strategy here?"
    ]
    
    print(f"🎯 Testing {len(test_questions)} philosophical questions:")
    print()
    
    for i, question in enumerate(test_questions, 1):
        print(f"Test {i}/{len(test_questions)}: User asks '{question}'")
        
        try:
            # Clear conversation history for each test
            chat_session.conversation_history = []
            
            response = chat_session.chat_response(question)
            print(f"✅ Response: '{response}'")
            
            # Check if response follows philosophical template
            thinking_markers = ['hmmm', 'i think', 'actually', 'honestly', 'makes sense']
            starts_with_thinking = any(response.lower().startswith(marker) for marker in thinking_markers)
            is_thoughtful = len(response.split()) > 5  # More than just a quick answer
            
            print(f"   🧠 Starts with thinking marker: {'✅' if starts_with_thinking else '❌'}")
            print(f"   💭 Thoughtful response: {'✅' if is_thoughtful else '❌'}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 50)
        print()

def test_message_detection():
    """Test if messages are correctly identified as philosophical"""
    print("🔍 Testing Philosophical Message Detection")
    print("=" * 50)
    
    # Load P2 profile
    p2_prompt = load_p2_profile("results/p2_prompt_20250924_191704.txt")
    llm = LLM(LLMConfig(model="gpt-4o-mini"), debug=False)
    chat_session = P2ChatSession(p2_prompt, llm)
    
    test_cases = [
        ("What do you think about AI?", True, "Opinion request"),
        ("Hey there!", False, "Greeting"),
        ("Should we go with option A?", True, "Strategic question"),
        ("How was your day?", False, "Casual question"),
        ("What's your take on this trend?", True, "Opinion seeking"),
        ("See you later!", False, "Farewell"),
        ("Why do you believe this will work?", True, "Philosophical inquiry"),
        ("What time is it?", False, "Factual question")
    ]
    
    for message, expected, description in test_cases:
        detected = chat_session._is_philosophical_question(message)
        result = "✅" if detected == expected else "❌"
        print(f"{result} '{message}' → {detected} (Expected: {expected}) - {description}")

if __name__ == "__main__":
    test_message_detection()
    print("\n" + "=" * 60 + "\n")
    test_philosophical_responses()