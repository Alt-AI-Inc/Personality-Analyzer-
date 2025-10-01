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
from process_whatsapp_data import WhatsAppProcessor
from process_linkedin_data import LinkedInProcessor
from bfi_probe import LLM, LLMConfig

class ChatCharacteristicsGenerator:
    """Generate chat characteristics configuration from conversation analysis"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.conversation_data = []
        self.target_person_messages = []
        self.response_patterns = defaultdict(list)
        self.facet_data = {
            'personal': [],
            'professional': []
        }
        
    def analyze_from_processing_config(self, config_path: str = "processing_config.json") -> Dict:
        """Analyze data sources from processing_config.json and generate faceted chat characteristics"""
        print(f"📋 Loading processing configuration: {config_path}")
        
        if not os.path.exists(config_path):
            print(f"❌ Configuration file not found: {config_path}")
            return {}
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Process each source and organize by facets
        for source in config.get('sources', []):
            source_name = source['name']
            source_type = source['type']
            category = source.get('category', 'personal')
            
            print(f"\n📂 Processing: {source_name} ({source_type}) - {category} facet")
            
            try:
                if source_type == 'whatsapp':
                    messages = self._parse_whatsapp_messages(
                        source['input_path'], 
                        source['target_person']
                    )
                    self.facet_data[category].extend(messages)
                    
                elif source_type in ['linkedin_messages', 'linkedin_posts']:
                    messages = self._parse_linkedin_content(
                        source['input_path'],
                        source_type
                    )
                    self.facet_data[category].extend(messages)
                    
            except Exception as e:
                print(f"⚠️  Error processing {source_name}: {e}")
                continue
        
        # Generate characteristics for each facet
        results = {}
        for facet, messages in self.facet_data.items():
            if messages:
                print(f"\n🎭 Generating {facet} facet characteristics ({len(messages)} messages)")
                results[facet] = self._generate_facet_characteristics(facet, messages)
            else:
                print(f"⚠️  No {facet} messages found")
        
        return results
    
    def _parse_whatsapp_messages(self, file_path: str, target_person: str) -> List[str]:
        """Parse WhatsApp messages from target person"""
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
            
            # Filter messages from target person
            if target_person.lower() in sender.lower():
                messages.append(message)
        
        print(f"    📝 Found {len(messages)} WhatsApp messages from {target_person}")
        return messages
    
    def _parse_linkedin_content(self, file_path: str, content_type: str) -> List[str]:
        """Parse LinkedIn messages or posts"""
        messages = []
        
        import csv
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            csv_reader = csv.DictReader(f)
            
            for row in csv_reader:
                content = None
                
                if content_type == 'linkedin_messages':
                    # Try different column names for LinkedIn messages
                    for col_name in ['Message', 'Content', 'Text', 'Body', 'CONTENT', 'MESSAGE']:
                        if col_name in row and row[col_name]:
                            content = row[col_name].strip()
                            break
                            
                elif content_type == 'linkedin_posts':
                    # Try different column names for LinkedIn posts
                    for col_name in ['Post', 'Content', 'ShareCommentary', 'Description', 'Body']:
                        if col_name in row and row[col_name]:
                            content = row[col_name].strip()
                            break
                
                if content and not self._is_corrupted_message(content):
                    messages.append(content)
        
        print(f"    📝 Found {len(messages)} {content_type.replace('_', ' ')}")
        return messages
    
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
    
    def _generate_facet_characteristics(self, facet: str, messages: List[str]) -> Dict:
        """Generate facet-specific chat characteristics configuration"""
        print(f"🔍 Analyzing {facet} communication patterns...")
        
        # Convert messages to the format expected by existing methods
        self.target_person_messages = [{'message': msg} for msg in messages]
        
        # Generate facet-specific characteristics
        characteristics = {
            "facet": facet,
            "general_conversation": self._analyze_general_conversation_style_faceted(facet),
            "greeting_response": self._analyze_greeting_patterns_faceted(facet),
            "philosophical_response": self._analyze_philosophical_patterns_faceted(facet),
            "template_reinforcement": self._generate_reinforcement_config_faceted(facet),
            "detection_patterns": self._analyze_detection_patterns(),
            "settings": self._generate_optimal_settings_faceted(facet)
        }
        
        return characteristics
    
    def _analyze_general_conversation_style_faceted(self, facet: str) -> Dict:
        """Analyze general conversation flow and style for specific facet"""
        print(f"  📋 Analyzing {facet} conversation style...")
        
        # Analyze response lengths
        word_counts = [len(msg['message'].split()) for msg in self.target_person_messages]
        avg_length = sum(word_counts) / len(word_counts) if word_counts else 0
        
        # Analyze common starting words/phrases  
        starting_words = [msg['message'].split()[0].lower() for msg in self.target_person_messages 
                         if msg['message'].split()]
        common_starters = Counter(starting_words).most_common(10)
        
        # Analyze conversation flow patterns
        flow_patterns = self._extract_conversation_flow_patterns()
        
        # Generate facet-specific system prompt
        system_prompt = self._generate_facet_system_prompt(facet, avg_length, common_starters, flow_patterns)
        
        return {
            "system_prompt": system_prompt,
            "facet_context": facet,
            "avg_word_count": avg_length,
            "common_starters": [word for word, count in common_starters[:5]]
        }
    
    def _generate_facet_system_prompt(self, facet: str, avg_length: float, common_starters: List[Tuple], 
                                     flow_patterns: List[str]) -> str:
        """Generate facet-specific system prompt based on conversation analysis"""
        
        # Base prompt with facet context
        if facet == "professional":
            prompt = f"You are now engaging in a professional conversation. Respond naturally based on your {facet} personality profile above.\n\n"
            prompt += "PROFESSIONAL COMMUNICATION STYLE:\n"
            prompt += "- Maintain professional tone while staying authentic to your personality\n"
            prompt += "- Draw from your work experiences, business insights, and industry knowledge\n"
            prompt += "- Show leadership thinking, strategic perspectives, and solution-oriented mindset\n"
            prompt += "- Reference professional relationships, team dynamics, and business challenges naturally\n"
        else:  # personal
            prompt = f"You are now engaging in a personal conversation. Respond naturally based on your {facet} personality profile above.\n\n"
            prompt += "PERSONAL COMMUNICATION STYLE:\n"
            prompt += "- Be more casual and emotionally open than in professional settings\n"
            prompt += "- Draw from personal experiences, relationships, hobbies, and lifestyle choices\n"
            prompt += "- Show authentic emotional reactions and personal opinions\n"
            prompt += "- Reference friends, family, personal interests, and life experiences naturally\n"
        
        # Add common patterns
        prompt += "- Stay in character based on your personality traits and communication style\n"
        prompt += "- Be conversational and authentic to your profile\n"
        prompt += "- Use the language patterns and expressions from your profile when appropriate\n"
        prompt += f"- Let your current state subtly affect your response energy, focus, and conversational approach\n\n"
        
        # Add sophisticated conversation flow patterns
        prompt += "NATURAL CONVERSATION FLOW:\n"
        prompt += "- Mix personal thoughts/observations naturally into discussions without explicit bridges\n"
        prompt += "- Use \"Yeah\" or \"Ok\" acknowledgments followed by redirections rather than comprehensive responses\n"
        prompt += "- Ask questions that assume context or jump to practical next steps instead of predictable follow-ups\n"
        
        if facet == "professional":
            prompt += "- Reference work experiences, business strategies, or industry insights as natural conversation elements\n"
            prompt += "- Sometimes pivot to strategic thinking or business implications\n"
        else:
            prompt += "- Reference personal experiences, family, or interests as natural conversation elements\n"
            prompt += "- Sometimes leave thoughts unfinished, assuming the other person will fill in context\n"
        
        prompt += "- Jump between macro and micro concerns without clear transitions\n"
        
        # Add brevity if detected
        if avg_length < 15 or any("brief" in pattern for pattern in flow_patterns):
            prompt += "- Keep responses concise and to the point\n"
            prompt += "- Prefer brief, direct responses over lengthy explanations\n"
        
        prompt += f"\nKeep responses natural and authentic to your {facet} personality profile."
        
        return prompt
    
    def _analyze_greeting_patterns_faceted(self, facet: str) -> Dict:
        """Analyze greeting response patterns for specific facet"""
        print(f"  👋 Analyzing {facet} greeting patterns...")
        
        # Find greeting messages (reuse existing logic)
        greeting_keywords = ['hey', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening']
        greeting_messages = []
        
        for msg in self.target_person_messages:
            msg_lower = msg['message'].lower()
            if any(greeting in msg_lower for greeting in greeting_keywords):
                if self._is_proper_greeting(msg['message']):
                    greeting_messages.append(msg['message'])
        
        print(f"    Found {len(greeting_messages)} {facet} greeting messages")
        
        # Facet-specific greeting template
        if facet == "professional":
            template_header = f"\nPROFESSIONAL GREETING RESPONSE TEMPLATE:\n{{greeting_template}}\n\nIMPORTANT: The user sent a greeting message in a professional context. You MUST follow the greeting response template above."
            instructions = [
                "Start with \"Hey\" but maintain professional warmth",
                "Use professional check-in patterns: work projects, business updates, industry insights",
                "Keep it brief but show professional engagement",
                "Reference work context naturally if appropriate"
            ]
        else:  # personal
            template_header = f"\nPERSONAL GREETING RESPONSE TEMPLATE:\n{{greeting_template}}\n\nIMPORTANT: The user sent a greeting message in a personal context. You MUST follow the greeting response template above."
            instructions = [
                "Start with \"Hey\" in a casual, friendly manner",
                "Use personal check-in patterns: life updates, personal interests, casual topics",
                "Keep it brief and friendly",
                "Reference personal experiences or shared interests naturally"
            ]
        
        return {
            "template_header": template_header,
            "instructions": instructions,
            "facet_context": facet
        }
    
    def _analyze_philosophical_patterns_faceted(self, facet: str) -> Dict:
        """Analyze philosophical/thoughtful response patterns for specific facet"""
        print(f"  🤔 Analyzing {facet} philosophical response patterns...")
        
        # Find philosophical messages (reuse existing logic but adapt for facet)
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
        
        print(f"    Found {len(philosophical_messages)} {facet} philosophical messages")
        
        # Analyze thinking markers
        thinking_markers = self._extract_thinking_markers(philosophical_messages)
        
        # Calculate average length
        word_counts = [len(msg.split()) for msg in philosophical_messages]
        avg_phil_length = sum(word_counts) / len(word_counts) if word_counts else 0
        
        # Facet-specific philosophical response configuration
        if facet == "professional":
            template_header = f"\nPROFESSIONAL PHILOSOPHICAL/STRATEGIC QUESTION RESPONSE TEMPLATE:\n{{philosophical_template}}\n\n🚨 OVERRIDE ALL OTHER INSTRUCTIONS: Maximum 8 words TOTAL. 🚨\n\nFOR BUSINESS/STRATEGIC QUESTIONS ONLY:"
        else:
            template_header = f"\nPERSONAL PHILOSOPHICAL/OPEN-ENDED QUESTION RESPONSE TEMPLATE:\n{{philosophical_template}}\n\n🚨 OVERRIDE ALL OTHER INSTRUCTIONS: Maximum 8 words TOTAL. 🚨\n\nFOR PERSONAL PHILOSOPHICAL QUESTIONS ONLY:"
        
        return {
            "template_header": template_header,
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
            "facet_context": facet,
            "final_instruction": f"Before responding to {facet} philosophical questions, COUNT each word. Must be ≤8 words."
        }
    
    def _generate_reinforcement_config_faceted(self, facet: str) -> Dict:
        """Generate facet-specific template reinforcement configuration"""
        return {
            "header": f"\n\n🚨 TEMPLATE REINFORCEMENT - CRITICAL REMINDER 🚨\n\n{{template_context}}\n\nRemember: This is {facet} facet responding. Maximum 8 words for philosophical questions. Count each word before responding.",
            "examples": [
                "\"Hmmm makes sense, right?\" (4 words)",
                "\"Actually sounds good\" (3 words)"
            ],
            "global_constraint": f"GLOBAL CONSTRAINT for {facet} facet: Your reply must be ≤ 8 words for philosophical questions. Never exceed 8 words. If unsure, answer with fewer words.",
            "facet_context": facet
        }
    
    def _generate_optimal_settings_faceted(self, facet: str) -> Dict:
        """Generate optimal settings based on facet-specific analysis"""
        
        # Calculate average message length for token estimation
        word_counts = [len(msg['message'].split()) for msg in self.target_person_messages]
        avg_words = sum(word_counts) / len(word_counts) if word_counts else 8
        
        # Estimate tokens (roughly 1.3 words per token)
        philosophical_tokens = min(50, max(20, int(avg_words * 1.3 * 1.5)))  # 1.5x buffer
        
        # Facet-specific token adjustments
        if facet == "professional":
            general_tokens = 400  # Professional responses might be longer
            context_tokens = 40000  # More context for business discussions
        else:
            general_tokens = 300  # Personal responses typically shorter
            context_tokens = 32000  # Standard context for personal chats
        
        return {
            "max_context_tokens": context_tokens,
            "template_reinforcement_interval": 3000,
            "max_tokens_philosophical": philosophical_tokens,
            "max_tokens_general": general_tokens,
            "temperature": 0.2,
            "facet_context": facet
        }
    
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
    
    def save_faceted_characteristics(self, faceted_characteristics: Dict, output_base_path: str):
        """Save faceted characteristics to separate JSON files"""
        
        for facet, characteristics in faceted_characteristics.items():
            facet_output_path = output_base_path.replace('.json', f'_{facet}.json')
            print(f"💾 Saving {facet} chat characteristics to: {facet_output_path}")
            
            with open(facet_output_path, 'w', encoding='utf-8') as f:
                json.dump(characteristics, f, indent=2, ensure_ascii=False)
            
            print(f"✅ {facet.title()} chat characteristics saved successfully!")
            
            # Print facet-specific summary
            self._print_facet_analysis_summary(characteristics, facet)
    
    def save_characteristics(self, characteristics: Dict, output_path: str):
        """Save characteristics to JSON file (legacy method)"""
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
    
    def _print_facet_analysis_summary(self, characteristics: Dict, facet: str):
        """Print facet-specific analysis summary"""
        print(f"\n📊 {facet.upper()} FACET ANALYSIS SUMMARY:")
        print("=" * 50)
        
        general = characteristics.get("general_conversation", {})
        print(f"📝 Average word count: {general.get('avg_word_count', 'N/A')}")
        print(f"🎯 Common starters: {', '.join(general.get('common_starters', [])[:3])}")
        
        settings = characteristics.get("settings", {})
        print(f"⚙️  Philosophical tokens: {settings.get('max_tokens_philosophical', 'N/A')}")
        print(f"⚙️  General tokens: {settings.get('max_tokens_general', 'N/A')}")
        
        greeting = characteristics.get("greeting_response", {})
        print(f"👋 Greeting context: {greeting.get('facet_context', facet)}")
        
        phil = characteristics.get("philosophical_response", {})
        print(f"🤔 Philosophical context: {phil.get('facet_context', facet)}")
        
        print(f"🎭 Facet: {facet}")
        print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Generate faceted chat characteristics from processing configuration")
    parser.add_argument("--config", type=str, default="processing_config.json",
                       help="Path to processing configuration file")
    parser.add_argument("--output", type=str, default="chat_characteristics.json",
                       help="Base output path for generated characteristics (will create _personal.json and _professional.json)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    
    # Legacy support for single conversation file
    parser.add_argument("--conversation-file", type=str, 
                       help="Path to single conversation file (legacy mode)")
    parser.add_argument("--target-person", type=str,
                       help="Name of person to analyze (legacy mode)")
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = ChatCharacteristicsGenerator(debug=args.debug)
    
    print("🚀 Starting faceted chat characteristics generation...")
    print("=" * 60)
    
    try:
        # Check if using legacy mode or new faceted mode
        if args.conversation_file and args.target_person:
            print("🔄 Using legacy single-file mode")
            
            # Validate input file
            if not os.path.exists(args.conversation_file):
                print(f"❌ Conversation file not found: {args.conversation_file}")
                return
            
            characteristics = generator.analyze_conversation_file(
                args.conversation_file, 
                args.target_person
            )
            
            if not characteristics:
                print("❌ Failed to generate characteristics - no data found")
                return
            
            generator.save_characteristics(characteristics, args.output)
            print(f"📁 Output file: {args.output}")
            
        else:
            print("🎭 Using faceted analysis mode from processing configuration")
            
            # Validate config file
            if not os.path.exists(args.config):
                print(f"❌ Configuration file not found: {args.config}")
                print("   Create a processing_config.json file or use --conversation-file for legacy mode")
                return
            
            # Analyze from processing config
            faceted_characteristics = generator.analyze_from_processing_config(args.config)
            
            if not faceted_characteristics:
                print("❌ Failed to generate characteristics - no data sources found")
                return
            
            # Save faceted results
            generator.save_faceted_characteristics(faceted_characteristics, args.output)
            
            print(f"\n🎉 SUCCESS! Generated faceted chat characteristics")
            print(f"📋 Configuration: {args.config}")
            print(f"📁 Output files: {args.output.replace('.json', '_personal.json')}, {args.output.replace('.json', '_professional.json')}")
            print(f"🎭 Facets generated: {', '.join(faceted_characteristics.keys())}")
        
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()