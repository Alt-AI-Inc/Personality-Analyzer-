#!/usr/bin/env python3

"""
WhatsApp Response Bucket Analyzer
Analyzes WhatsApp export to create response buckets and templates for a specific person
"""

import re
import json
import argparse
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from bfi_probe import LLM, LLMConfig

class WhatsAppBucketAnalyzer:
    """Analyzes WhatsApp messages to create response buckets"""
    
    BUCKET_DEFINITIONS = {
        "introductions_greetings": {
            "description": "Initial greetings, hellos, checking in after time",
            "keywords": ["hey", "hi", "hello", "wassup", "what's up", "how are you", "good morning", "good evening"],
            "context_clues": ["start of conversation", "after long gap", "first message"]
        },
        "scheduling_meetings": {
            "description": "Setting up meetings, appointments, calls, timing discussions",
            "keywords": ["meeting", "call", "schedule", "time", "when", "available", "free", "busy", "calendar"],
            "context_clues": ["time references", "availability queries", "meeting setup"]
        },
        "quick_confirmations": {
            "description": "Simple yes/no, acknowledgments, got it responses", 
            "keywords": ["yes", "no", "ok", "okay", "got it", "sure", "yep", "nope", "alright", "cool"],
            "context_clues": ["one word responses", "simple acknowledgments"]
        },
        "work_technical": {
            "description": "Work discussions, technical questions, project-related topics",
            "keywords": ["project", "work", "code", "fix", "issue", "bug", "feature", "deploy", "build", "test"],
            "context_clues": ["technical terms", "work context", "problem-solving"]
        },
        "location_status": {
            "description": "Where someone is, travel updates, ETA, location sharing",
            "keywords": ["here", "there", "on my way", "arriving", "reached", "location", "traffic", "late", "early"],
            "context_clues": ["movement", "location references", "timing updates"]
        },
        "personal_health": {
            "description": "Health check-ins, how someone is feeling, personal wellbeing",
            "keywords": ["feeling", "sick", "tired", "good", "bad", "better", "worse", "health", "doctor"],
            "context_clues": ["emotional state", "physical condition", "wellbeing"]
        },
        "problem_issues": {
            "description": "Problems, complaints, issues that need solving",
            "keywords": ["problem", "issue", "broken", "not working", "error", "help", "stuck", "wrong"],
            "context_clues": ["negative tone", "requesting help", "describing problems"]
        },
        "open_questions": {
            "description": "Subjective questions, opinions, open-ended discussions",
            "keywords": ["what do you think", "opinion", "should", "would", "could", "thoughts", "advice"],
            "context_clues": ["opinion seeking", "open-ended", "subjective"]
        },
        "urgent_requests": {
            "description": "Time-sensitive, urgent requests or information",
            "keywords": ["urgent", "asap", "now", "immediately", "quick", "fast", "emergency"],
            "context_clues": ["urgency markers", "time pressure", "immediate needs"]
        },
        "casual_social": {
            "description": "Casual chat, social interactions, humor, personal stories",
            "keywords": ["haha", "lol", "funny", "story", "remember", "guess what", "btw", "random"],
            "context_clues": ["humor", "casual tone", "personal sharing"]
        }
    }
    
    def __init__(self, llm: Optional[LLM] = None):
        self.llm = llm or LLM(LLMConfig(model="gpt-4o-mini", temperature=0.1))
        
    def parse_whatsapp_export(self, file_path: str) -> List[Dict]:
        """Parse WhatsApp export file into structured messages"""
        messages = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # WhatsApp export pattern: [YYYY/MM/DD, HH:MM:SS] Name: Message
        # Updated pattern to handle 4-digit years and proper multiline matching
        pattern = r'\[(\d{4}/\d{1,2}/\d{1,2}),?\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.*?)(?=\n\[\d{4}/|$)'
        
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        
        print(f"🔍 Found {len(matches)} message matches with regex")
        
        for match in matches:
            date, time, sender, message = match
            
            # Clean up message text
            message = message.strip().replace('\n', ' ')
            
            # Skip system messages and media omitted
            if (message and 
                not message.startswith('<Media omitted>') and
                not message.startswith('‎Messages and calls are end-to-end encrypted') and
                len(message.strip()) > 0):
                
                messages.append({
                    'date': date,
                    'time': time,
                    'sender': sender.strip(),
                    'message': message
                })
        
        print(f"📱 Parsed {len(messages)} valid messages from WhatsApp export")
        
        # Debug: show unique senders
        if messages:
            senders = set(msg['sender'] for msg in messages)
            print(f"📝 Found senders: {sorted(senders)}")
        
        return messages
    
    def filter_messages_by_person(self, messages: List[Dict], person_name: str) -> Tuple[List[Dict], List[Dict]]:
        """Filter messages to get person's messages and the messages they're responding to"""
        person_messages = []
        context_messages = []
        
        # Get exact name variations
        name_variations = self._get_name_variations(messages, person_name)
        print(f"🔍 Found name variations for '{person_name}': {name_variations}")
        
        for i, msg in enumerate(messages):
            if any(variation.lower() in msg['sender'].lower() for variation in name_variations):
                person_messages.append({**msg, 'index': i})
                
                # Get previous message for context (what they're responding to)
                if i > 0:
                    context_messages.append({**messages[i-1], 'response_index': i})
        
        print(f"📊 Found {len(person_messages)} messages from {person_name}")
        print(f"📋 Found {len(context_messages)} context messages")
        
        return person_messages, context_messages
    
    def _get_name_variations(self, messages: List[Dict], target_name: str) -> List[str]:
        """Get all name variations for the target person from message senders"""
        all_senders = set(msg['sender'] for msg in messages)
        
        # Find senders that match the target name (case-insensitive partial match)
        variations = []
        target_lower = target_name.lower()
        
        for sender in all_senders:
            sender_lower = sender.lower()
            if target_lower in sender_lower or sender_lower in target_lower:
                variations.append(sender)
        
        # If no variations found, use exact name
        if not variations:
            variations = [target_name]
            
        return variations
    
    def categorize_message_pairs(self, person_messages: List[Dict], context_messages: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize message pairs using LLM analysis"""
        
        # Create pairs of context -> response
        message_pairs = []
        context_lookup = {msg['response_index']: msg for msg in context_messages}
        
        for person_msg in person_messages:
            context_msg = context_lookup.get(person_msg['index'])
            if context_msg:
                message_pairs.append({
                    'context': context_msg['message'],
                    'response': person_msg['message'],
                    'date': person_msg['date'],
                    'time': person_msg['time']
                })
        
        print(f"🔗 Created {len(message_pairs)} message pairs for analysis")
        
        # Batch categorization with LLM
        return self._batch_categorize_messages(message_pairs)
    
    def _batch_categorize_messages(self, message_pairs: List[Dict]) -> Dict[str, List[Dict]]:
        """Batch categorize messages using improved LLM approach for all pairs"""
        
        buckets = {bucket: [] for bucket in self.BUCKET_DEFINITIONS.keys()}
        
        print(f"📊 Processing all {len(message_pairs)} message pairs with LLM categorization")
        
        # Process in smaller batches of 15 to avoid token limits
        batch_size = 15
        total_batches = (len(message_pairs) + batch_size - 1) // batch_size
        
        for i in range(0, len(message_pairs), batch_size):
            batch = message_pairs[i:i+batch_size]
            batch_num = i//batch_size + 1
            print(f"🤖 Processing batch {batch_num}/{total_batches} ({len(batch)} pairs) - Progress: {batch_num/total_batches*100:.1f}%")
            
            try:
                batch_results = self._categorize_batch_improved(batch)
                
                # Merge results
                for bucket, pairs in batch_results.items():
                    buckets[bucket].extend(pairs)
                    
            except Exception as e:
                print(f"⚠️  Error processing batch {batch_num}: {e}")
                print("   Falling back to keyword categorization for this batch")
                fallback_results = self._fallback_categorize_batch(batch)
                for bucket, pairs in fallback_results.items():
                    buckets[bucket].extend(pairs)
        
        # Show distribution
        print(f"📈 Categorization complete:")
        for bucket_id, pairs in buckets.items():
            if pairs:
                print(f"   {bucket_id}: {len(pairs)} pairs")
        
        return buckets
    
    def _categorize_batch_improved(self, message_pairs: List[Dict]) -> Dict[str, List[Dict]]:
        """Improved batch categorization with better LLM prompt"""
        
        # Build simpler, more focused prompt
        pairs_text = []
        for i, pair in enumerate(message_pairs, 1):
            context = pair['context'].replace('\n', ' ').strip()
            response = pair['response'].replace('\n', ' ').strip()
            pairs_text.append(f"{i}. \"{context}\" → \"{response}\"")
        
        pairs_list = "\n".join(pairs_text)
        
        prompt = f"""Categorize these conversation pairs by the TYPE of message being responded to.

PAIRS:
{pairs_list}

CATEGORIES:
- greetings: Hi, hey, how are you, checking in
- scheduling: Meeting, time, when, call, calendar  
- confirmations: Yes, no, ok, got it, sure
- work: Project, technical, business discussion
- location: Where, travel, on my way, arrived
- health: How feeling, sick, tired, wellness
- problems: Issues, broken, help needed, complaints
- questions: Opinions, what do you think, advice
- urgent: ASAP, urgent, emergency, now
- social: Casual chat, jokes, stories, random

Just respond with this format:
1=greetings, 2=social, 3=confirmations, 4=work, 5=scheduling, 6=social, 7=questions, 8=social, 9=confirmations, 10=greetings, 11=social, 12=work, 13=social, 14=urgent, 15=social"""

        try:
            result = self.llm.chat(
                "You are a conversation analyst. Categorize messages by their context type.",
                prompt,
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse the simple format response
            batch_buckets = {
                'introductions_greetings': [],
                'scheduling_meetings': [], 
                'quick_confirmations': [],
                'work_technical': [],
                'location_status': [],
                'personal_health': [],
                'problem_issues': [],
                'open_questions': [],
                'urgent_requests': [],
                'casual_social': []
            }
            
            # Mapping from short names to bucket IDs
            category_mapping = {
                'greetings': 'introductions_greetings',
                'scheduling': 'scheduling_meetings',
                'confirmations': 'quick_confirmations', 
                'work': 'work_technical',
                'location': 'location_status',
                'health': 'personal_health',
                'problems': 'problem_issues',
                'questions': 'open_questions',
                'urgent': 'urgent_requests',
                'social': 'casual_social'
            }
            
            # Parse results like "1=greetings, 2=social, 3=confirmations"
            assignments = result.strip().split(',')
            for assignment in assignments:
                if '=' in assignment:
                    try:
                        pair_num, category = assignment.strip().split('=')
                        pair_num = int(pair_num) - 1  # Convert to 0-based index
                        category = category.strip()
                        
                        if 0 <= pair_num < len(message_pairs) and category in category_mapping:
                            bucket_id = category_mapping[category]
                            batch_buckets[bucket_id].append(message_pairs[pair_num])
                    except (ValueError, IndexError):
                        continue
            
            return batch_buckets
            
        except Exception as e:
            print(f"⚠️  LLM categorization failed: {e}")
            return self._fallback_categorize_batch(message_pairs)
    
    def _categorize_batch(self, message_pairs: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize a batch of message pairs"""
        
        # Build analysis prompt
        bucket_descriptions = []
        for bucket_id, definition in self.BUCKET_DEFINITIONS.items():
            bucket_descriptions.append(f"- {bucket_id}: {definition['description']}")
        
        pairs_text = []
        for i, pair in enumerate(message_pairs, 1):
            pairs_text.append(f"{i}. CONTEXT: \"{pair['context']}\"\n   RESPONSE: \"{pair['response']}\"")
        
        bucket_list = "\n".join(bucket_descriptions)
        pairs_list = "\n".join(pairs_text)
        
        prompt = f"""Categorize these message pairs into response buckets based on the TYPE OF MESSAGE being responded to.

AVAILABLE BUCKETS:
{bucket_list}

MESSAGE PAIRS TO CATEGORIZE:
{pairs_list}

For each message pair, determine which bucket the CONTEXT MESSAGE belongs to (what type of message is being responded to).

Respond with JSON format:
{{
    "bucket_name": [1, 3, 5],  // list of pair numbers that belong to this bucket
    "another_bucket": [2, 4],
    // ... etc
}}

Only include buckets that have at least one pair assigned. Be precise about categorization."""

        try:
            result = self.llm.chat(
                "You are a conversation analyst specializing in message categorization.",
                prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse JSON response
            import json
            categorization = json.loads(result.strip())
            
            # Convert back to message pairs
            batch_buckets = {bucket: [] for bucket in self.BUCKET_DEFINITIONS.keys()}
            
            for bucket, pair_numbers in categorization.items():
                if bucket in batch_buckets:
                    for pair_num in pair_numbers:
                        if 1 <= pair_num <= len(message_pairs):
                            batch_buckets[bucket].append(message_pairs[pair_num - 1])
            
            return batch_buckets
            
        except Exception as e:
            print(f"⚠️  Error in batch categorization: {e}")
            # Fallback to keyword-based categorization
            return self._fallback_categorize_batch(message_pairs)
    
    def _fallback_categorize_batch(self, message_pairs: List[Dict]) -> Dict[str, List[Dict]]:
        """Fallback keyword-based categorization if LLM fails"""
        batch_buckets = {bucket: [] for bucket in self.BUCKET_DEFINITIONS.keys()}
        
        for pair in message_pairs:
            context_lower = pair['context'].lower()
            
            # Simple keyword matching
            categorized = False
            for bucket_id, definition in self.BUCKET_DEFINITIONS.items():
                if any(keyword in context_lower for keyword in definition['keywords']):
                    batch_buckets[bucket_id].append(pair)
                    categorized = True
                    break
            
            # Default to casual_social if no match
            if not categorized:
                batch_buckets['casual_social'].append(pair)
        
        return batch_buckets
    
    def analyze_response_patterns(self, buckets: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """Analyze response patterns for each bucket"""
        
        bucket_analysis = {}
        
        for bucket_id, pairs in buckets.items():
            if not pairs:
                continue
                
            print(f"🔍 Analyzing {bucket_id} bucket ({len(pairs)} pairs)")
            
            # Extract just the responses
            responses = [pair['response'] for pair in pairs]
            
            # Analyze patterns with LLM
            analysis = self._analyze_bucket_responses(bucket_id, responses)
            
            bucket_analysis[bucket_id] = {
                "count": len(pairs),
                "definition": self.BUCKET_DEFINITIONS[bucket_id]['description'],
                "response_analysis": analysis,
                "example_pairs": pairs[:5],  # Top 5 examples
                "all_responses": responses
            }
        
        return bucket_analysis
    
    def _analyze_bucket_responses(self, bucket_id: str, responses: List[str]) -> Dict:
        """Analyze response patterns using LLM to identify conversational trends"""
        
        if not responses:
            return {
                "typical_length": "no responses",
                "opening_patterns": [],
                "common_phrases": [], 
                "punctuation_style": "no data",
                "tone_markers": [],
                "top_3_templates": []
            }
        
        # Sample responses for analysis (max 30 for good variety)
        sample_responses = responses[:30] if len(responses) > 30 else responses
        
        responses_text = "\n".join(f"- \"{resp}\"" for resp in sample_responses)
        
        prompt = f"""Analyze these actual responses from {bucket_id} conversations and identify the TOP 3 specific response patterns/templates.

ACTUAL RESPONSES:
{responses_text}

Focus on identifying CONCRETE conversational trends, not generic categories. Look for:
1. How does this person typically start responses in {bucket_id} situations?
2. What are the most common actual response patterns?
3. What specific phrases or structures appear repeatedly?

Provide exactly 3 response templates based on what you observe, ordered by frequency. Each template should be a concrete pattern like:
- "Hey + [action]" (for responses like "Hey, calling you now", "Hey, on my way")
- "Hmmm, + [thought]" (for responses like "Hmmm, let me think", "Hmmm, not sure")  
- "[Short confirmation] + [follow-up]" (for "Got it. Cool", "Sure. Works for me")

Response format:
{{
  "typical_length": "brief description like '1-2 sentences' or '1-3 words'",
  "most_common_starters": ["actual", "words", "found"],
  "casual_markers": ["yeah", "ok", "man", "etc"],
  "top_3_templates": [
    {{"pattern": "concrete template description", "examples": ["actual example 1", "actual example 2"]}},
    {{"pattern": "concrete template description", "examples": ["actual example 1", "actual example 2"]}},
    {{"pattern": "concrete template description", "examples": ["actual example 1", "actual example 2"]}}
  ]
}}"""

        try:
            result = self.llm.chat(
                "You are a conversation pattern analyst. Find specific, actionable response templates.",
                prompt,
                max_tokens=1000,
                temperature=0.1
            )
            
            # Try to parse JSON, with fallback
            try:
                analysis = json.loads(result.strip())
                return analysis
            except json.JSONDecodeError:
                print(f"⚠️  JSON parsing failed for {bucket_id}, attempting to extract patterns manually")
                return self._extract_patterns_from_text(result, responses)
                
        except Exception as e:
            print(f"⚠️  Error analyzing bucket {bucket_id}: {e}")
            return {
                "typical_length": "analysis failed",
                "most_common_starters": [],
                "casual_markers": [],
                "top_3_templates": [
                    {"pattern": "Pattern analysis failed", "examples": responses[:2]}
                ]
            }
    
    def _extract_patterns_from_text(self, llm_response: str, responses: List[str]) -> Dict:
        """Fallback method to extract patterns from LLM text response"""
        # Simple fallback - just use first few responses as examples
        return {
            "typical_length": "varies",
            "most_common_starters": ["analysis", "failed"],
            "casual_markers": [],
            "top_3_templates": [
                {
                    "pattern": "Manual extraction needed",
                    "examples": responses[:2] if len(responses) >= 2 else responses
                },
                {
                    "pattern": "LLM response parsing failed", 
                    "examples": responses[2:4] if len(responses) >= 4 else responses[:1]
                },
                {
                    "pattern": "Check original response",
                    "examples": responses[4:6] if len(responses) >= 6 else responses[:1]
                }
            ]
        }
    
    def save_buckets(self, bucket_analysis: Dict, output_file: str, person_name: str):
        """Save bucket analysis to JSON file"""
        
        output_data = {
            "person_name": person_name,
            "total_buckets": len([b for b in bucket_analysis.values() if b['count'] > 0]),
            "total_message_pairs": sum(b['count'] for b in bucket_analysis.values()),
            "analysis_timestamp": None,  # Could add datetime if needed
            "buckets": bucket_analysis
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved bucket analysis to {output_file}")
        
        # Print summary
        print(f"\n📊 BUCKET SUMMARY for {person_name}:")
        print("=" * 60)
        for bucket_id, analysis in bucket_analysis.items():
            if analysis['count'] > 0:
                template = analysis['response_analysis'].get('response_template', 'No template')
                print(f"{bucket_id}: {analysis['count']} pairs")
                print(f"  Template: {template}")
                print()

def main():
    parser = argparse.ArgumentParser(description="Analyze WhatsApp export to create response buckets")
    parser.add_argument("whatsapp_file", help="Path to WhatsApp export file")
    parser.add_argument("person_name", help="Name of person whose messages to analyze")
    parser.add_argument("--output", "-o", help="Output JSON file", default="response_buckets.json")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    print(f"🤖 WhatsApp Response Bucket Analyzer")
    print(f"📱 File: {args.whatsapp_file}")
    print(f"👤 Person: {args.person_name}")
    print(f"💾 Output: {args.output}")
    print("=" * 60)
    
    # Initialize analyzer
    llm = LLM(LLMConfig(model=args.model, temperature=0.1), debug=args.debug)
    analyzer = WhatsAppBucketAnalyzer(llm)
    
    # Parse WhatsApp export
    messages = analyzer.parse_whatsapp_export(args.whatsapp_file)
    
    # Filter messages for specific person
    person_messages, context_messages = analyzer.filter_messages_by_person(messages, args.person_name)
    
    if not person_messages:
        print(f"❌ No messages found for person '{args.person_name}'")
        print("Available senders:")
        senders = set(msg['sender'] for msg in messages)
        for sender in sorted(senders):
            print(f"  - {sender}")
        return
    
    # Categorize message pairs
    buckets = analyzer.categorize_message_pairs(person_messages, context_messages)
    
    # Analyze response patterns
    bucket_analysis = analyzer.analyze_response_patterns(buckets)
    
    # Save results
    analyzer.save_buckets(bucket_analysis, args.output, args.person_name)
    
    print(f"✅ Analysis complete! Check {args.output} for detailed results.")

if __name__ == "__main__":
    main()