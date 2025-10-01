#!/usr/bin/env python3

"""
WhatsApp Data Processor with LLM Pre-filtering
Converts WhatsApp chat exports to filtered JSON for OCEAN5 personality analysis
"""

import json
import re
import argparse
import os
from typing import List, Dict, Optional
from bfi_probe import LLM, LLMConfig

class WhatsAppProcessor:
    """Process WhatsApp export data with LLM-powered personality relevance filtering"""
    
    def __init__(self, llm: LLM, debug: bool = False):
        self.llm = llm
        self.debug = debug
        self.personality_filter_prompt = self._create_personality_filter_prompt()
        
    def _create_personality_filter_prompt(self) -> str:
        """Create LLM prompt for personality relevance filtering"""
        return """Analyze this message for Big Five personality trait indicators.

Message: "{content}"

Does this message reveal personality traits in these areas:
- OPENNESS: creative thinking, curiosity, abstract ideas, artistic interests, philosophical thoughts, unconventional views
- CONSCIENTIOUSNESS: planning, organization, reliability, goal-orientation, work habits, time management, responsibility
- EXTRAVERSION: social energy, enthusiasm, assertiveness, leadership, comfort with attention, social confidence
- AGREEABLENESS: cooperation, empathy, trust, helping others, conflict resolution, consideration for others
- NEUROTICISM: emotional reactions, stress responses, anxiety, mood changes, worry, emotional sensitivity

Answer with ONE WORD: YES (if it reveals meaningful personality traits) or NO (if it's just factual, logistical, or generic).

Focus on:
- Personal opinions and values
- Decision-making style
- Emotional expressions and reactions  
- Social behavior and interaction patterns
- Lifestyle choices and preferences
- Problem-solving approaches
- Conflict handling
- Planning and organization style

Exclude:
- Pure logistics ("Meet at 5pm")
- Simple acknowledgments ("OK", "Thanks")
- Factual information sharing
- Media/link sharing without commentary"""

    def parse_whatsapp_export(self, whatsapp_path: str, target_person: str) -> List[Dict]:
        """Parse WhatsApp export file and extract messages from target person"""
        print(f"📂 Loading WhatsApp export: {whatsapp_path}")
        print(f"🎯 Target person: {target_person}")
        
        with open(whatsapp_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # WhatsApp export pattern: [YYYY/MM/DD, HH:MM:SS] Name: Message
        pattern = r'\[(\d{4}/\d{1,2}/\d{1,2}),?\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.*?)(?=\n\[|\Z)'
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        
        messages = []
        target_messages = []
        
        for match in matches:
            date_str, time_str, sender, message = match
            
            # Clean up message content
            message = message.strip().replace('\n', ' ')
            
            # Skip empty messages and system messages
            if not message or message.startswith(('‎', '<Media omitted>', 'image omitted', 'video omitted')):
                continue
            
            messages.append({
                'date': date_str,
                'time': time_str,
                'sender': sender.strip(),
                'message': message
            })
            
            # Filter messages from target person
            if target_person.lower() in sender.lower():
                target_messages.append({
                    'date': date_str,
                    'time': time_str,
                    'sender': sender.strip(),
                    'message': message
                })
        
        print(f"✅ Parsed {len(messages)} total messages")
        print(f"🎭 Found {len(target_messages)} messages from {target_person}")
        
        return target_messages

    def basic_content_filter(self, message: str) -> bool:
        """Apply basic filtering before LLM analysis"""
        if not message or len(message.strip()) < 5:
            return False
            
        # Remove very short messages (likely not personality revealing)  
        if len(message.split()) < 3:
            return False
            
        # Remove messages that are mostly URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, message)
        if len(' '.join(urls)) > len(message) * 0.7:
            return False
        
        # Filter out pure logistics messages
        logistics_patterns = [
            r'^(ok|okay|yes|no|yep|nope|sure|fine|alright)\.?$',
            r'^(thanks?|thank you|thx)\.?$',
            r'^(see you|bye|good night|good morning)\.?$',
            r'^\d{1,2}:\d{2}',  # Time references
            r'^(on my way|omw|coming|reached)\.?$'
        ]
        
        message_lower = message.lower().strip()
        for pattern in logistics_patterns:
            if re.match(pattern, message_lower):
                return False
        
        # Remove messages that are mostly numbers/dates
        words = message.split()
        number_words = sum(1 for word in words if re.match(r'^\d+$', word.strip('.,!?')))
        if number_words > len(words) * 0.5:
            return False
            
        return True

    def is_personality_relevant(self, message: str) -> bool:
        """Use LLM to determine if message reveals personality traits (single item - for compatibility)"""
        results = self.batch_personality_analysis([message])
        return results[0] if results else False
    
    def batch_personality_analysis(self, messages: List[str], batch_size: int = 50) -> List[bool]:
        """Process multiple messages in batched LLM calls for efficiency"""
        if not messages:
            return []
        
        results = []
        
        # Process in batches
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
            
            # Show progress for batches (always show, not just in debug)
            if len(messages) > batch_size:
                progress = min(i + batch_size, len(messages))
                print(f"   🤖 LLM batch progress: {progress}/{len(messages)} ({progress/len(messages)*100:.1f}%)")
        
        return results
    
    def _process_batch(self, batch_messages: List[str]) -> List[bool]:
        """Process a single batch of messages"""
        try:
            # Create batched prompt
            batch_prompt = self._create_batch_prompt(batch_messages)
            
            system_msg = "You are an expert psychologist analyzing private messages for personality research. Respond with ONLY the numbered list as requested."
            response = self.llm.chat(system_msg, batch_prompt)
            
            # Parse batch response
            return self._parse_batch_response(response, len(batch_messages))
            
        except Exception as e:
            if self.debug:
                print(f"❌ Batch LLM analysis error: {e}")
            # Fallback: assume all are relevant to avoid losing data
            return [True] * len(batch_messages)
    
    def _create_batch_prompt(self, batch_messages: List[str]) -> str:
        """Create a batched prompt for multiple messages"""
        prompt = """Analyze these WhatsApp messages for Big Five personality trait indicators.

For each message, determine if it reveals personality traits in these areas:
- OPENNESS: creative thinking, curiosity, abstract ideas, artistic interests, philosophical thoughts, unconventional views
- CONSCIENTIOUSNESS: planning, organization, reliability, goal-orientation, work habits, time management, responsibility
- EXTRAVERSION: social energy, enthusiasm, assertiveness, leadership, comfort with attention, social confidence
- AGREEABLENESS: cooperation, empathy, trust, helping others, conflict resolution, consideration for others
- NEUROTICISM: emotional reactions, stress responses, anxiety, mood changes, worry, emotional sensitivity

Focus on:
- Personal opinions and values
- Decision-making style
- Emotional expressions and reactions  
- Social behavior and interaction patterns
- Lifestyle choices and preferences
- Problem-solving approaches

Exclude pure logistics, simple acknowledgments, or factual information sharing.

"""
        
        # Add numbered items
        for i, message in enumerate(batch_messages, 1):
            # Truncate very long messages to avoid token limits
            truncated_message = message[:200] + "..." if len(message) > 200 else message
            prompt += f"{i}. {truncated_message}\n\n"
        
        prompt += f"""Respond with ONLY a numbered list (1-{len(batch_messages)}) where each line is:
NUMBER: YES or NO

Example format:
1: YES
2: NO  
3: YES"""

        return prompt
    
    def _parse_batch_response(self, response: str, expected_count: int) -> List[bool]:
        """Parse batched LLM response into boolean list"""
        results = []
        
        # Look for pattern "NUMBER: YES/NO"
        import re
        pattern = r'(\d+):\s*(YES|NO)'
        matches = re.findall(pattern, response.upper())
        
        # Create results array
        response_dict = {int(num): answer == 'YES' for num, answer in matches}
        
        # Fill in results in order, defaulting to True if missing
        for i in range(1, expected_count + 1):
            results.append(response_dict.get(i, True))  # Default to True if unclear
        
        if self.debug and len(matches) != expected_count:
            print(f"⚠️  Batch parsing: expected {expected_count}, got {len(matches)} responses")
        
        return results

    def process_whatsapp(self, whatsapp_path: str, target_person: str, output_path: str, max_messages: int = None) -> Dict:
        """Process WhatsApp export file and create filtered JSON"""
        print("🚀 Starting WhatsApp data processing...")
        
        # Parse WhatsApp export
        raw_messages = self.parse_whatsapp_export(whatsapp_path, target_person)
        
        if not raw_messages:
            print(f"❌ No messages found from {target_person}")
            return {"error": "No messages found"}
        
        if max_messages:
            raw_messages = raw_messages[:max_messages]
            print(f"🔪 Limited to first {max_messages} messages for processing")
        
        processed_messages = []
        stats = {
            "total_parsed": len(raw_messages),
            "basic_filtered": 0,
            "llm_analyzed": 0,
            "personality_relevant": 0,
            "final_count": 0
        }
        
        print("🔍 Processing messages with batch analysis...")
        
        # First pass: extract and basic filter all messages
        basic_filtered_messages = []
        for i, msg_data in enumerate(raw_messages):
            if self.debug and i % 200 == 0:
                print(f"   Basic filtering progress: {i}/{len(raw_messages)} ({i/len(raw_messages)*100:.1f}%)")
            
            message = msg_data['message']
            
            # Basic filtering
            if not self.basic_content_filter(message):
                continue
                
            basic_filtered_messages.append(message)
            stats["basic_filtered"] += 1
        
        print(f"🔍 Basic filtering complete: {len(basic_filtered_messages)} messages passed basic filters")
        print(f"🤖 Running batch LLM analysis on {len(basic_filtered_messages)} messages...")
        
        # Batch LLM analysis
        if basic_filtered_messages:
            stats["llm_analyzed"] = len(basic_filtered_messages)
            personality_results = self.batch_personality_analysis(basic_filtered_messages)
            
            # Build final results
            for message, is_relevant in zip(basic_filtered_messages, personality_results):
                if is_relevant:
                    processed_messages.append({"full_text": message})
                    stats["personality_relevant"] += 1
                    
                    if self.debug:
                        print(f"✅ Personality relevant: {message[:80]}...")
                elif self.debug:
                    print(f"❌ Not personality relevant: {message[:80]}...")
        
        stats["final_count"] = len(processed_messages)
        
        # Save results
        print(f"💾 Saving {len(processed_messages)} filtered messages to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_messages, f, indent=2, ensure_ascii=False)
        
        # Print statistics
        self._print_processing_stats(stats)
        
        return stats

    def _print_processing_stats(self, stats: Dict):
        """Print processing statistics"""
        print("\n📊 PROCESSING STATISTICS:")
        print("=" * 50)
        print(f"📝 Total messages parsed: {stats['total_parsed']}")
        print(f"🔍 Passed basic filtering: {stats['basic_filtered']} ({stats['basic_filtered']/stats['total_parsed']*100:.1f}%)")
        print(f"🤖 Analyzed by LLM: {stats['llm_analyzed']}")
        print(f"🎯 Personality relevant: {stats['personality_relevant']} ({stats['personality_relevant']/stats['llm_analyzed']*100:.1f}% of analyzed)")
        print(f"✅ Final filtered count: {stats['final_count']}")
        print(f"📈 Overall retention: {stats['final_count']/stats['total_parsed']*100:.1f}%")
        print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Process WhatsApp export data for OCEAN5 personality analysis")
    parser.add_argument("--input", type=str, required=True,
                       help="Path to WhatsApp export file")
    parser.add_argument("--target-person", type=str, required=True,
                       help="Name of person to extract messages from")
    parser.add_argument("--output", type=str, default="whatsapp_filtered.json",
                       help="Output path for filtered messages JSON")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                       choices=["gpt-4o-mini", "gpt-4o", "gpt-5"],
                       help="LLM model for personality filtering")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--max-messages", type=int,
                       help="Limit processing to first N messages (for testing)")
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        return
    
    # Initialize LLM
    print(f"🤖 Initializing {args.model} for personality filtering...")
    cfg = LLMConfig(model=args.model, temperature=0.3, max_tokens=2000)
    llm = LLM(cfg, debug=args.debug)
    
    # Initialize processor
    processor = WhatsAppProcessor(llm, debug=args.debug)
    
    try:
        # Process messages
        stats = processor.process_whatsapp(args.input, args.target_person, args.output, args.max_messages)
        
        if "error" in stats:
            return
        
        print(f"\n🎉 SUCCESS! Processed WhatsApp data")
        print(f"📁 Input: {args.input}")
        print(f"👤 Target: {args.target_person}")
        print(f"📁 Output: {args.output}")
        print(f"🤖 Model: {args.model}")
        print(f"📊 Messages retained: {stats['final_count']}/{stats['total_parsed']}")
        
    except Exception as e:
        print(f"❌ Error processing WhatsApp data: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()