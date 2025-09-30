#!/usr/bin/env python3

"""
Greeting Bucket Analyzer
Focus on proper greeting conversations by grouping messages by day
"""

import re
import json
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
from bfi_probe import LLM, LLMConfig

class GreetingBucketAnalyzer:
    """Analyzes greeting conversations with proper temporal grouping"""
    
    def __init__(self, llm: LLM):
        self.llm = llm
        
    def parse_whatsapp_export(self, file_path: str) -> List[Dict]:
        """Parse WhatsApp export with proper timestamp handling"""
        messages = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # WhatsApp pattern: [YYYY/MM/DD, HH:MM:SS] Name: Message
        pattern = r'\[(\d{4}/\d{1,2}/\d{1,2}),?\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.*?)(?=\n\[\d{4}/|$)'
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            date_str, time_str, sender, message = match
            message = message.strip().replace('\n', ' ')
            
            # Skip system messages
            if (message and 
                not message.startswith('<Media omitted>') and
                not message.startswith('‎Messages and calls are end-to-end encrypted') and
                len(message.strip()) > 0):
                
                # Parse date properly
                try:
                    date_parts = date_str.split('/')
                    year = int(date_parts[0])
                    month = int(date_parts[1])
                    day = int(date_parts[2])
                    
                    time_parts = time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    second = int(time_parts[2])
                    
                    timestamp = datetime(year, month, day, hour, minute, second)
                    date_key = f"{year}-{month:02d}-{day:02d}"  # YYYY-MM-DD format
                    
                    messages.append({
                        'date_str': date_str,
                        'time_str': time_str,
                        'date_key': date_key,
                        'timestamp': timestamp,
                        'sender': sender.strip(),
                        'message': message
                    })
                except (ValueError, IndexError):
                    # Skip messages with invalid timestamps
                    continue
        
        print(f"📱 Parsed {len(messages)} valid messages")
        return messages
    
    def group_messages_by_day(self, messages: List[Dict], target_person: str) -> Dict[str, List[Dict]]:
        """Group messages by day and identify target person's messages"""
        daily_conversations = defaultdict(list)
        
        # Find name variations for target person
        all_senders = set(msg['sender'] for msg in messages)
        target_variations = []
        target_lower = target_person.lower()
        
        for sender in all_senders:
            if target_lower in sender.lower() or sender.lower() in target_lower:
                target_variations.append(sender)
        
        print(f"🔍 Found name variations for '{target_person}': {target_variations}")
        
        # Group by date
        for msg in messages:
            daily_conversations[msg['date_key']].append(msg)
        
        # Sort each day's messages by timestamp
        for date_key in daily_conversations:
            daily_conversations[date_key].sort(key=lambda x: x['timestamp'])
        
        print(f"📅 Found {len(daily_conversations)} days of conversation")
        return dict(daily_conversations), target_variations
    
    def find_greeting_conversations(self, daily_conversations: Dict[str, List[Dict]], target_variations: List[str]) -> List[Dict]:
        """Find actual greeting conversations within daily context"""
        
        greeting_keywords = [
            'hi', 'hey', 'hello', 'good morning', 'good evening', 'good afternoon',
            'how are you', 'how\'s it going', 'what\'s up', 'wassup', 'sup',
            'hope you', 'how was', 'happy', 'congrats', 'congratulations'
        ]
        
        greeting_pairs = []
        
        for date_key, day_messages in daily_conversations.items():
            if len(day_messages) < 2:
                continue
                
            # Look for greeting patterns within the day
            for i in range(len(day_messages) - 1):
                current_msg = day_messages[i]
                next_msg = day_messages[i + 1]
                
                # Check if current message is a potential greeting
                current_lower = current_msg['message'].lower()
                is_greeting_context = any(keyword in current_lower for keyword in greeting_keywords)
                
                # Check if next message is from our target person (within reasonable time)
                time_diff = (next_msg['timestamp'] - current_msg['timestamp']).total_seconds()
                is_target_response = any(var in next_msg['sender'] for var in target_variations)
                is_reasonable_time = time_diff < 3600  # Within 1 hour
                
                if is_greeting_context and is_target_response and is_reasonable_time:
                    greeting_pairs.append({
                        'date': date_key,
                        'context': current_msg['message'],
                        'response': next_msg['message'],
                        'context_sender': current_msg['sender'],
                        'response_sender': next_msg['sender'],
                        'time_diff_minutes': time_diff / 60
                    })
        
        print(f"👋 Found {len(greeting_pairs)} potential greeting conversations")
        return greeting_pairs
    
    def analyze_greeting_patterns(self, greeting_pairs: List[Dict]) -> Dict:
        """Analyze greeting response patterns using LLM"""
        
        if not greeting_pairs:
            return {"error": "No greeting pairs found"}
        
        # Show some examples first
        print("\n🔍 Sample greeting pairs found:")
        for i, pair in enumerate(greeting_pairs[:5], 1):
            print(f"{i}. [{pair['date']}] \"{pair['context']}\" → \"{pair['response']}\"")
        
        # Prepare data for LLM analysis
        examples_text = []
        for i, pair in enumerate(greeting_pairs[:30], 1):  # Analyze up to 30 examples
            examples_text.append(f"{i}. \"{pair['context']}\" → \"{pair['response']}\"")
        
        examples_str = "\n".join(examples_text)
        
        prompt = f"""Analyze these ACTUAL greeting conversation pairs and identify the top 3 most common response patterns.

GREETING CONVERSATION PAIRS:
{examples_str}

These are real conversations where someone initiated with a greeting/check-in and got a response. 

Focus on identifying the actual patterns in the RESPONSES (right side of →). Look for:
1. How does this person typically respond to greetings?
2. What are the most common greeting response structures?
3. Are there specific phrases or patterns that repeat?

Provide exactly 3 response templates based on what you observe:

Response format:
{{
  "total_examples": {len(greeting_pairs)},
  "typical_length": "description of typical response length",
  "common_starters": ["actual", "words", "that", "start", "responses"],
  "casual_markers": ["yeah", "man", "etc"],
  "top_3_greeting_templates": [
    {{"pattern": "concrete greeting response template", "examples": ["actual example 1", "actual example 2"], "frequency": "how often this appears"}},
    {{"pattern": "concrete greeting response template", "examples": ["actual example 1", "actual example 2"], "frequency": "how often this appears"}},
    {{"pattern": "concrete greeting response template", "examples": ["actual example 1", "actual example 2"], "frequency": "how often this appears"}}
  ]
}}

Be specific about greeting response patterns, not general conversation patterns."""

        try:
            result = self.llm.chat(
                "You are analyzing greeting conversation patterns. Focus on how this person responds to greetings specifically.",
                prompt,
                max_tokens=1000,
                temperature=0.1
            )
            
            # Try to parse JSON
            analysis = json.loads(result.strip())
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print(f"Raw LLM response: {result}")
            return {"error": "JSON parsing failed", "raw_response": result}
        except Exception as e:
            print(f"⚠️  Analysis failed: {e}")
            return {"error": str(e)}

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze greeting conversations specifically")
    parser.add_argument("whatsapp_file", help="Path to WhatsApp export file")
    parser.add_argument("person_name", help="Name of person whose greeting responses to analyze")
    parser.add_argument("--output", "-o", help="Output JSON file", default="greeting_analysis.json")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    print(f"👋 Greeting Conversation Analyzer")
    print(f"📱 File: {args.whatsapp_file}")
    print(f"👤 Person: {args.person_name}")
    print(f"💾 Output: {args.output}")
    print("=" * 50)
    
    # Initialize analyzer
    llm = LLM(LLMConfig(model=args.model, temperature=0.1), debug=args.debug)
    analyzer = GreetingBucketAnalyzer(llm)
    
    # Parse WhatsApp export
    messages = analyzer.parse_whatsapp_export(args.whatsapp_file)
    
    # Group by day
    daily_conversations, target_variations = analyzer.group_messages_by_day(messages, args.person_name)
    
    # Find greeting conversations
    greeting_pairs = analyzer.find_greeting_conversations(daily_conversations, target_variations)
    
    if not greeting_pairs:
        print("❌ No greeting conversations found")
        return
    
    # Analyze patterns
    analysis = analyzer.analyze_greeting_patterns(greeting_pairs)
    
    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump({
            "person_name": args.person_name,
            "analysis_type": "greeting_conversations",
            "total_greeting_pairs": len(greeting_pairs),
            "sample_pairs": greeting_pairs[:10],  # First 10 for reference
            "pattern_analysis": analysis
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Analysis saved to {args.output}")
    
    # Display results
    if "error" not in analysis:
        print(f"\n📊 GREETING ANALYSIS RESULTS:")
        print(f"   Total greeting pairs: {len(greeting_pairs)}")
        print(f"   Typical length: {analysis.get('typical_length', 'unknown')}")
        print(f"   Common starters: {', '.join(analysis.get('common_starters', []))}")
        
        templates = analysis.get('top_3_greeting_templates', [])
        print(f"\n📝 Top 3 Greeting Response Templates:")
        for i, template in enumerate(templates, 1):
            print(f"   {i}. {template.get('pattern', 'Unknown pattern')}")
            examples = template.get('examples', [])
            for example in examples[:2]:  # Show max 2 examples
                print(f"      Example: \"{example}\"")
    else:
        print(f"\n❌ Analysis failed: {analysis.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()