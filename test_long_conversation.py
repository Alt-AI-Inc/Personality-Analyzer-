#!/usr/bin/env python3

"""
Test long conversation to see if philosophical template impact diminishes
"""

from chat_with_p2 import P2ChatSession, load_p2_profile
from bfi_probe import LLM, LLMConfig

def test_long_philosophical_conversation():
    print("🧪 Testing Long Conversation - Philosophical Template Impact")
    print("=" * 70)
    
    # Load P2 profile
    p2_prompt = load_p2_profile("results/p2_prompt_20250924_191704.txt")
    if not p2_prompt:
        print("❌ Failed to load P2 profile")
        return
    
    # Initialize chat session
    llm = LLM(LLMConfig(model="gpt-4o-mini", temperature=0.8), debug=False)  # Turn off debug for cleaner output
    chat_session = P2ChatSession(p2_prompt, llm, debug=False)
    
    # List of philosophical questions to test throughout conversation
    philosophical_questions = [
        "What do you think about the future of remote work?",
        "Should companies prioritize innovation over stability?", 
        "How do you see AI changing the workplace?",
        "What's your opinion on work-life balance?",
        "Do you think startups should focus on growth or profitability first?",
        "What are your thoughts on the subscription economy?",
        "Should we be worried about data privacy in apps?",
        "How do you approach making difficult decisions?",
        "What do you think makes a good product strategy?",
        "Do you believe remote teams can be as effective as in-person ones?",
        "What's your take on the creator economy?",
        "Should businesses prioritize customer acquisition or retention?",
        "How do you think about product-market fit?",
        "What's your opinion on the role of AI in creative work?",
        "Do you think we're building too many similar apps?",
        "What makes a technology trend sustainable vs just hype?",
        "Should we focus more on user experience or feature completeness?",
        "What do you think about the future of payments?",
        "How should companies handle technical debt?",
        "What's your view on open source vs proprietary software?"
    ]
    
    print(f"🎯 Testing {len(philosophical_questions)} philosophical questions in sequence")
    print("Looking for philosophical template patterns in responses...")
    print()
    
    # Track if responses follow philosophical patterns
    pattern_matches = []
    
    for i, question in enumerate(philosophical_questions, 1):
        print(f"📝 Message {i}/20: '{question}'")
        
        try:
            response = chat_session.chat_response(question)
            print(f"🤖 Response: '{response}'")
            
            # Check if response follows philosophical template patterns
            response_lower = response.lower()
            
            # Check for philosophical template markers
            thinking_markers = ['hmmm', 'i think', 'actually', 'honestly', 'makes sense', 'got it', 'yeah', 'ok', 'sure', 'cool', 'yup', 'right', 'not sure', 'no clue', 'nope', 'doh']
            question_patterns = [' right?', 'right?', '?']
            
            has_thinking_marker = any(marker in response_lower for marker in thinking_markers)
            has_question_pattern = any(pattern in response_lower for pattern in question_patterns)
            is_brief = len(response.split()) <= 15  # Brief as per template
            
            # Score the response
            pattern_score = 0
            if has_thinking_marker:
                pattern_score += 1
            if has_question_pattern:
                pattern_score += 1  
            if is_brief:
                pattern_score += 1
                
            pattern_matches.append({
                'message_num': i,
                'has_thinking_marker': has_thinking_marker,
                'has_question_pattern': has_question_pattern,
                'is_brief': is_brief,
                'pattern_score': pattern_score,
                'response_length': len(response.split())
            })
            
            print(f"   📊 Template Adherence: {pattern_score}/3 - Thinking: {'✅' if has_thinking_marker else '❌'}, Questions: {'✅' if has_question_pattern else '❌'}, Brief: {'✅' if is_brief else '❌'}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            pattern_matches.append({
                'message_num': i,
                'has_thinking_marker': False,
                'has_question_pattern': False,
                'is_brief': False,
                'pattern_score': 0,
                'response_length': 0
            })
        
        print("-" * 60)
    
    # Analyze pattern degradation
    print(f"\n📈 PATTERN ANALYSIS ACROSS 20 MESSAGES:")
    print("=" * 70)
    
    # Split into early, middle, late conversation
    early_messages = pattern_matches[:7]    # Messages 1-7
    middle_messages = pattern_matches[7:14] # Messages 8-14  
    late_messages = pattern_matches[14:]    # Messages 15-20
    
    def analyze_group(group, name):
        avg_score = sum(m['pattern_score'] for m in group) / len(group)
        avg_length = sum(m['response_length'] for m in group) / len(group)
        thinking_pct = sum(1 for m in group if m['has_thinking_marker']) / len(group) * 100
        question_pct = sum(1 for m in group if m['has_question_pattern']) / len(group) * 100
        brief_pct = sum(1 for m in group if m['is_brief']) / len(group) * 100
        
        print(f"{name} (Messages {group[0]['message_num']}-{group[-1]['message_num']}):")
        print(f"  Average Template Score: {avg_score:.2f}/3")
        print(f"  Average Response Length: {avg_length:.1f} words")
        print(f"  Thinking Markers: {thinking_pct:.1f}%")
        print(f"  Question Patterns: {question_pct:.1f}%") 
        print(f"  Brief Responses: {brief_pct:.1f}%")
        print()
    
    analyze_group(early_messages, "EARLY CONVERSATION")
    analyze_group(middle_messages, "MIDDLE CONVERSATION")  
    analyze_group(late_messages, "LATE CONVERSATION")
    
    # Overall trend analysis
    overall_avg = sum(m['pattern_score'] for m in pattern_matches) / len(pattern_matches)
    early_avg = sum(m['pattern_score'] for m in early_messages) / len(early_messages)
    late_avg = sum(m['pattern_score'] for m in late_messages) / len(late_messages)
    
    print(f"🎯 TREND ANALYSIS:")
    print(f"Overall Average Template Adherence: {overall_avg:.2f}/3")
    print(f"Early vs Late Degradation: {early_avg:.2f} → {late_avg:.2f} ({late_avg - early_avg:+.2f})")
    
    if late_avg < early_avg - 0.3:
        print("⚠️  SIGNIFICANT DEGRADATION DETECTED - Template impact diminishes over time")
    elif late_avg < early_avg:
        print("📉 Minor degradation observed")
    else:
        print("✅ Template impact maintained throughout conversation")

if __name__ == "__main__":
    test_long_philosophical_conversation()