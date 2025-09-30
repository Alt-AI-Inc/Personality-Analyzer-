#!/usr/bin/env python3

"""
Generate chat_characteristics.json from conversation data analysis
Analyzes WhatsApp conversation files to extract communication patterns and create configuration
"""

import json
import re
import argparse
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set
import os

class ChatCharacteristicsGenerator:
    """Generate chat characteristics configuration from conversation analysis"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.conversation_data = []
        self.target_person_messages = []
        self.response_patterns = defaultdict(list)
        
    def analyze_conversation_file(self, file_path: str, target_person: str) -> Dict:
        """Analyze conversation file and extract communication patterns"""
        print(f"📖 Analyzing conversation file: {file_path}")
        print(f"🎯 Target person: {target_person}")
        
        # Store target person for personalization
        self.current_target_person = target_person
        
        # Extract messages from conversation file
        self.conversation_data = self._parse_conversation_file(file_path)
        print(f"📝 Found {len(self.conversation_data)} total messages")
        
        # Filter messages from target person
        self.target_person_messages = [
            msg for msg in self.conversation_data 
            if target_person.lower() in msg['sender'].lower()
        ]
        print(f"🎭 Found {len(self.target_person_messages)} messages from {target_person}")
        
        if not self.target_person_messages:
            print(f"❌ No messages found from {target_person}")
            return {}
        
        # Analyze communication patterns
        return self._generate_chat_characteristics()
    
    def _parse_conversation_file(self, file_path: str) -> List[Dict]:
        """Parse WhatsApp conversation file into structured format"""
        messages = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # WhatsApp pattern: [YYYY/MM/DD, HH:MM:SS] Name: Message
        pattern = r'\[(\d{4}/\d{1,2}/\d{1,2}),?\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.*?)(?=\n\[|\Z)'
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            date_str, time_str, sender, message = match
            
            # Clean up message content
            message = message.strip().replace('\n', ' ')
            
            # Skip corrupted/invalid messages
            if not message or self._is_corrupted_message(message):
                continue
                
            messages.append({
                'date': date_str,
                'time': time_str, 
                'sender': sender.strip(),
                'message': message
            })
        
        return messages
    
    def _is_corrupted_message(self, message: str) -> bool:
        """Check if message is corrupted or inappropriate for analysis"""
        # Skip media messages
        if message.startswith(('‎', '<Media omitted>', 'image omitted', 'video omitted')):
            return True
            
        # Skip messages with embedded timestamps (corruption)
        if re.search(r'\[\d{4}/\d{1,2}/\d{1,2},\s+\d{1,2}:\d{2}:\d{2}\]', message):
            return True
            
        # Skip very long messages (likely corrupted multi-line)
        if len(message.split()) > 100:
            return True
            
        # Skip messages with unusual Unicode characters indicating corruption
        if '‎' in message or message.count('�') > 2:
            return True
            
        # Skip empty or whitespace-only messages
        if not message.strip():
            return True
            
        return False
    
    def _generate_chat_characteristics(self) -> Dict:
        """Generate complete chat characteristics configuration"""
        print("🔍 Analyzing communication patterns...")
        
        # Get target person name for personalization
        target_person = getattr(self, 'current_target_person', '')
        
        characteristics = {
            "general_conversation": self._analyze_general_conversation_style(),
            "greeting_response": self._analyze_greeting_patterns(),
            "philosophical_response": self._analyze_philosophical_patterns(),
            "template_reinforcement": self._generate_reinforcement_config(target_person),
            "detection_patterns": self._analyze_detection_patterns(),
            "settings": self._generate_optimal_settings()
        }
        
        return characteristics
    
    def _analyze_general_conversation_style(self) -> Dict:
        """Analyze general conversation flow and style"""
        print("  📋 Analyzing general conversation style...")
        
        # Analyze response lengths
        word_counts = [len(msg['message'].split()) for msg in self.target_person_messages]
        avg_length = sum(word_counts) / len(word_counts) if word_counts else 0
        
        # Analyze common starting words/phrases  
        starting_words = [msg['message'].split()[0].lower() for msg in self.target_person_messages 
                         if msg['message'].split()]
        common_starters = Counter(starting_words).most_common(10)
        
        # Analyze conversation flow patterns
        flow_patterns = self._extract_conversation_flow_patterns()
        
        # Generate system prompt based on patterns
        system_prompt = self._generate_system_prompt(avg_length, common_starters, flow_patterns)
        
        return {
            "system_prompt": system_prompt
        }
    
    def _extract_conversation_flow_patterns(self) -> List[str]:
        """Extract conversation flow patterns from messages"""
        patterns = []
        
        # Analyze acknowledgment patterns
        acknowledgments = ['yeah', 'ok', 'sure', 'cool', 'got it', 'makes sense']
        ack_count = sum(1 for msg in self.target_person_messages 
                       if any(ack in msg['message'].lower() for ack in acknowledgments))
        
        if ack_count > len(self.target_person_messages) * 0.3:
            patterns.append("Uses frequent acknowledgments (Yeah, Ok, Sure)")
        
        # Analyze question patterns
        question_count = sum(1 for msg in self.target_person_messages if '?' in msg['message'])
        if question_count > len(self.target_person_messages) * 0.4:
            patterns.append("Asks follow-up questions frequently")
        
        # Analyze brevity patterns
        brief_responses = sum(1 for msg in self.target_person_messages 
                            if len(msg['message'].split()) <= 10)
        if brief_responses > len(self.target_person_messages) * 0.6:
            patterns.append("Prefers brief, concise responses")
        
        # Analyze topic jumping
        topic_words = ['actually', 'speaking of', 'by the way', 'also']
        topic_jump_count = sum(1 for msg in self.target_person_messages 
                              if any(word in msg['message'].lower() for word in topic_words))
        if topic_jump_count > len(self.target_person_messages) * 0.2:
            patterns.append("Makes natural topic transitions and associations")
        
        return patterns
    
    def _generate_system_prompt(self, avg_length: float, common_starters: List[Tuple], 
                               flow_patterns: List[str]) -> str:
        """Generate system prompt based on conversation analysis"""
        
        # Base prompt
        prompt = "You are now engaging in a casual conversation. Respond naturally based on your personality profile above.\n\n"
        
        # Add personality & style section
        prompt += "PERSONALITY & STYLE:\n"
        prompt += "- Stay in character based on your personality traits and communication style\n"
        prompt += "- Be conversational and authentic to your profile\n"
        prompt += "- Use the language patterns and expressions from your profile when appropriate\n"
        prompt += "- Let your current state subtly affect your response energy, focus, and conversational approach\n\n"
        
        # Add sophisticated conversation flow patterns based on analysis
        prompt += "NATURAL CONVERSATION FLOW:\n"
        
        # Add sophisticated conversational patterns from original
        prompt += "- Mix personal thoughts/observations naturally into discussions without explicit bridges\n"
        prompt += "- Use \"Yeah\" or \"Ok\" acknowledgments followed by redirections rather than comprehensive responses\n"
        prompt += "- Ask questions that assume context or jump to practical next steps instead of predictable follow-ups\n"
        prompt += "- Reference personal experiences, family, or interests as natural conversation elements\n"
        prompt += "- Sometimes leave thoughts unfinished, assuming the other person will fill in context\n"
        prompt += "- Jump between macro and micro concerns without clear transitions\n"
        
        # Add brevity if detected
        if avg_length < 15 or any("brief" in pattern for pattern in flow_patterns):
            prompt += "- Keep responses concise and to the point\n"
            prompt += "- Prefer brief, direct responses over lengthy explanations\n"
        
        # Add response patterns section with sophisticated examples
        prompt += "\nRESPONSE PATTERNS:\n"
        prompt += "- Instead of \"What do you think about X?\", ask \"Should we just do Y?\"\n"
        prompt += "- When discussing problems, jump to solutions or next steps rather than analyzing extensively\n"
        
        # Add common starters if identified (but limit to meaningful ones)
        meaningful_starters = [word for word, count in common_starters[:3] 
                             if word not in ['i', 'the', 'a', 'an', 'is', 'it', 'we']]
        if meaningful_starters:
            prompt += f"- Common conversation starters: {', '.join(meaningful_starters)}\n"
        
        prompt += "\nKeep responses natural and authentic to your personality profile."
        
        return prompt
    
    def _analyze_greeting_patterns(self) -> Dict:
        """Analyze greeting response patterns"""
        print("  👋 Analyzing greeting patterns...")
        
        # Find greeting messages
        greeting_keywords = ['hey', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening']
        greeting_messages = []
        
        for i, msg in enumerate(self.target_person_messages):
            msg_lower = msg['message'].lower()
            if any(greeting in msg_lower for greeting in greeting_keywords):
                # Only add if it's a proper greeting (short and appropriate)
                if self._is_proper_greeting(msg['message']):
                    greeting_messages.append(msg['message'])
        
        print(f"    Found {len(greeting_messages)} greeting messages")
        
        # Analyze greeting response patterns
        patterns = self._extract_greeting_patterns(greeting_messages)
        
        template_header = "\nGREETING RESPONSE TEMPLATE:\n{greeting_template}\n\nIMPORTANT: The user sent a greeting message. You MUST follow the greeting response template above."
        
        instructions = [
            "Start with \"Hey\" as specified in the template",
            "Use one of the three patterns: Acknowledgment + Check-in, Simple Acknowledgment + Friendly Addition, or Acknowledgment + Well-wishing",
            "Keep it brief (1-2 sentences maximum) as per template guidelines",
            "Only add additional context if the user's message specifically requested it (e.g., asked about something specific)",
            "Do NOT elaborate beyond the template patterns unless the user's message demands it"
        ]
        
        return {
            "template_header": template_header,
            "instructions": instructions
        }
    
    def _is_proper_greeting(self, message: str) -> bool:
        """Check if message is a proper greeting (not corrupted or too long)"""
        # Skip very long messages that aren't pure greetings
        if len(message.split()) > 15:
            return False
            
        # Skip messages with embedded timestamps or corruption indicators
        if '[' in message or '‎' in message:
            return False
            
        msg_lower = message.lower()
        
        # Must start with or contain greeting words in the first 3 words
        first_three_words = ' '.join(message.split()[:3]).lower()
        greeting_starters = ['hey', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening']
        
        has_greeting_start = any(starter in first_three_words for starter in greeting_starters)
        if not has_greeting_start:
            return False
        
        # Exclude messages that are clearly not greetings despite containing greeting words
        non_greeting_indicators = [
            'was a', 'this was', 'which i', 'build', 'order', 'totally agree', 
            'innovative', 'experience', 'envelope', 'chinese', 'stuff'
        ]
        
        if any(indicator in msg_lower for indicator in non_greeting_indicators):
            return False
            
        # Greeting should be relatively short and focused
        greeting_words = ['hey', 'hi', 'hello', 'good', 'morning', 'afternoon', 'evening', 'whats', 'how', 'up']
        greeting_word_count = sum(1 for word in greeting_words if word in msg_lower)
        total_words = len(message.split())
        
        # For messages over 5 words, greeting words should make up at least 30% 
        if total_words > 5 and greeting_word_count / total_words < 0.3:
            return False
            
        return True
    
    def _extract_greeting_patterns(self, greeting_messages: List[str]) -> List[str]:
        """Extract common patterns from greeting messages"""
        patterns = []
        
        if not greeting_messages:
            return patterns
        
        # Analyze greeting styles
        casual_greetings = sum(1 for msg in greeting_messages 
                              if any(word in msg.lower() for word in ['hey', 'hi']))
        if casual_greetings > len(greeting_messages) * 0.7:
            patterns.append("Prefers casual greetings (Hey, Hi)")
        
        # Analyze follow-up patterns
        question_greetings = sum(1 for msg in greeting_messages if '?' in msg)
        if question_greetings > len(greeting_messages) * 0.5:
            patterns.append("Often includes questions in greetings")
        
        # Analyze length patterns
        brief_greetings = sum(1 for msg in greeting_messages if len(msg.split()) <= 5)
        if brief_greetings > len(greeting_messages) * 0.6:
            patterns.append("Keeps greetings brief and direct")
        
        return patterns
    
    def _analyze_philosophical_patterns(self) -> Dict:
        """Analyze philosophical/thoughtful response patterns"""
        print("  🤔 Analyzing philosophical response patterns...")
        
        # Find philosophical/opinion messages
        philosophical_keywords = [
            'think', 'opinion', 'believe', 'feel', 'perspective', 'view',
            'approach', 'strategy', 'should', 'would', 'could', 'might'
        ]
        
        philosophical_messages = []
        for msg in self.target_person_messages:
            msg_lower = msg['message'].lower()
            if (any(word in msg_lower for word in philosophical_keywords) and 
                ('?' in msg['message'] or len(msg['message'].split()) > 5)):
                philosophical_messages.append(msg['message'])
        
        print(f"    Found {len(philosophical_messages)} philosophical messages")
        
        # Analyze thinking markers
        thinking_markers = self._extract_thinking_markers(philosophical_messages)
        
        # Analyze response brevity
        word_counts = [len(msg.split()) for msg in philosophical_messages]
        avg_phil_length = sum(word_counts) / len(word_counts) if word_counts else 0
        
        # Generate philosophical response configuration
        return {
            "template_header": "\nPHILOSOPHICAL/OPEN-ENDED QUESTION RESPONSE TEMPLATE:\n{philosophical_template}\n\n🚨 OVERRIDE ALL OTHER INSTRUCTIONS: Maximum 8 words TOTAL. 🚨\n\nFOR PHILOSOPHICAL QUESTIONS ONLY:",
            "override_instructions": [
                "IGNORE all \"natural conversation flow\" instructions",
                "IGNORE \"ask follow-up questions\" instructions",
                "IGNORE \"add personal thoughts\" instructions", 
                "IGNORE \"pivot to related topics\" instructions"
            ],
            "mandatory_rules": {
                "brevity_rule": f"Exactly 4-8 words. No exceptions. (Analyzed avg: {avg_phil_length:.1f} words)",
                "format": "[Thinking marker] + [brief insight] + \"right?\"",
                "examples": self._generate_philosophical_examples(thinking_markers)
            },
            "forbidden": [
                "Any response over 8 words",
                "Follow-up questions beyond \"right?\"",
                "Multiple sentences",
                "Personal anecdotes or elaborations", 
                "Topic transitions or associations",
                "\"What do you think?\" or similar"
            ],
            "final_instruction": "Before responding, COUNT each word. Must be ≤8 words."
        }
    
    def _extract_thinking_markers(self, messages: List[str]) -> List[str]:
        """Extract common thinking markers from messages"""
        thinking_words = ['hmmm', 'hmm', 'i think', 'actually', 'honestly', 
                         'makes sense', 'yeah', 'ok', 'sure', 'cool', 'got it']
        
        marker_counts = Counter()
        
        for msg in messages:
            msg_lower = msg.lower()
            for marker in thinking_words:
                if marker in msg_lower:
                    marker_counts[marker] += 1
        
        # Return most common markers
        return [marker for marker, count in marker_counts.most_common(10)]
    
    def _generate_philosophical_examples(self, thinking_markers: List[str]) -> List[str]:
        """Generate example philosophical responses based on analysis"""
        examples = []
        
        # Always include the core template example from the original
        examples.append("\"Hmmm makes sense, right?\" (4 words) ✅")
        
        # Add marker-specific examples based on analysis
        if 'i think' in thinking_markers:
            examples.append("\"I think balance works, right?\" (5 words) ✅")
        if 'actually' in thinking_markers:
            examples.append("\"Actually depends on context, right?\" (5 words) ✅")
        if 'honestly' in thinking_markers:
            examples.append("\"Honestly not sure\" (3 words) ✅")
        
        # Ensure we have exactly 4 examples like the original
        while len(examples) < 4:
            remaining_examples = [
                "\"Makes sense, right?\" (3 words) ✅",
                "\"Yeah, sounds good\" (3 words) ✅",
                "\"Cool approach, right?\" (3 words) ✅",
                "\"Got it, works\" (3 words) ✅"
            ]
            
            for example in remaining_examples:
                if example not in examples and len(examples) < 4:
                    examples.append(example)
        
        return examples[:4]  # Exactly 4 examples
    
    def _generate_reinforcement_config(self, target_person: str) -> Dict:
        """Generate template reinforcement configuration"""
        # Extract first name for personalization
        first_name = target_person.split()[0] if target_person else "authentic"
        
        return {
            "header": f"\n\n🚨 TEMPLATE REINFORCEMENT - CRITICAL REMINDER 🚨\n\n{{template_context}}\n\nRemember: This is {first_name} responding. Maximum 8 words. Count each word before responding.",
            "examples": [
                "\"Hmmm makes sense, right?\" (4 words)",
                "\"Actually sounds good\" (3 words)"
            ],
            "global_constraint": "GLOBAL CONSTRAINT: Your reply must be ≤ 8 words. Never exceed 8 words. If unsure, answer with fewer words."
        }
    
    def _analyze_detection_patterns(self) -> Dict:
        """Analyze patterns for message type detection"""
        print("  🔍 Analyzing detection patterns...")
        
        # Extract greeting patterns
        greeting_starters = set()
        for msg in self.target_person_messages:
            words = msg['message'].lower().split()[:3]  # First 3 words
            for word in words:
                if word in ['hey', 'hi', 'hello', 'morning', 'afternoon', 'evening', 'sup', 'wassup']:
                    greeting_starters.add(word)
        
        # Extract philosophical patterns  
        philosophical_patterns = set()
        for msg in self.target_person_messages:
            msg_lower = msg['message'].lower()
            
            # Look for opinion-seeking patterns
            patterns_to_check = [
                'what do you think', 'thoughts on', 'opinion on', 'your take',
                'do you believe', 'should we', 'would you', 'how do you',
                'strategy', 'approach', 'better', 'worse'
            ]
            
            for pattern in patterns_to_check:
                if pattern in msg_lower:
                    philosophical_patterns.add(pattern)
        
        return {
            "greeting_patterns": list(greeting_starters) + [
                "good morning", "good afternoon", "good evening", 
                "what's up", "whats up", "how are you"
            ],
            "philosophical_patterns": list(philosophical_patterns) + [
                "what do you think", "what are your thoughts", "opinion about",
                "perspective on", "your view", "how do you see",
                "future", "trend", "right", "wrong", "best way"
            ]
        }
    
    def _generate_optimal_settings(self) -> Dict:
        """Generate optimal settings based on analysis"""
        
        # Calculate average message length for token estimation
        word_counts = [len(msg['message'].split()) for msg in self.target_person_messages]
        avg_words = sum(word_counts) / len(word_counts) if word_counts else 8
        
        # Estimate tokens (roughly 1.3 words per token)
        philosophical_tokens = min(50, max(20, int(avg_words * 1.3 * 1.5)))  # 1.5x buffer
        
        return {
            "max_context_tokens": 32000,
            "template_reinforcement_interval": 3000,
            "max_tokens_philosophical": philosophical_tokens,
            "max_tokens_general": 300,
            "temperature": 0.2
        }
    
    def save_characteristics(self, characteristics: Dict, output_path: str):
        """Save characteristics to JSON file"""
        print(f"💾 Saving chat characteristics to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(characteristics, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Chat characteristics saved successfully!")
        
        # Print summary
        self._print_analysis_summary(characteristics)
    
    def _print_analysis_summary(self, characteristics: Dict):
        """Print analysis summary"""
        print("\n📊 ANALYSIS SUMMARY:")
        print("=" * 50)
        
        general = characteristics.get("general_conversation", {})
        print(f"📝 Average word count: {general.get('avg_word_count', 'N/A')}")
        print(f"🎯 Common starters: {', '.join(general.get('common_starters', [])[:5])}")
        
        settings = characteristics.get("settings", {})
        print(f"⚙️  Philosophical tokens: {settings.get('max_tokens_philosophical', 'N/A')}")
        
        detection = characteristics.get("detection_patterns", {})
        print(f"👋 Greeting patterns: {len(detection.get('greeting_patterns', []))} found")
        print(f"🤔 Philosophical patterns: {len(detection.get('philosophical_patterns', []))} found")
        
        phil = characteristics.get("philosophical_response", {})
        print(f"💭 Thinking markers found: {len(phil.get('thinking_markers_found', []))}")
        print(f"📏 Avg philosophical length: {phil.get('avg_philosophical_length', 'N/A')} words")
        
        print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Generate chat characteristics from conversation analysis")
    parser.add_argument("--conversation-file", type=str, required=True,
                       help="Path to conversation file (e.g., Data/Abhishek.txt)")
    parser.add_argument("--target-person", type=str, required=True,
                       help="Name of person to analyze (e.g., 'Shreyas Srinivasan')")
    parser.add_argument("--output", type=str, default="chat_characteristics_generated.json",
                       help="Output path for generated characteristics")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.conversation_file):
        print(f"❌ Conversation file not found: {args.conversation_file}")
        return
    
    # Initialize generator
    generator = ChatCharacteristicsGenerator(debug=args.debug)
    
    # Analyze conversation and generate characteristics
    print("🚀 Starting chat characteristics generation...")
    print("=" * 60)
    
    try:
        characteristics = generator.analyze_conversation_file(
            args.conversation_file, 
            args.target_person
        )
        
        if not characteristics:
            print("❌ Failed to generate characteristics - no data found")
            return
        
        # Save results
        generator.save_characteristics(characteristics, args.output)
        
        print(f"\n🎉 SUCCESS! Generated chat characteristics from conversation analysis")
        print(f"📁 Output file: {args.output}")
        print(f"🎭 Analyzed: {args.target_person}")
        print(f"📖 Source: {args.conversation_file}")
        
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()