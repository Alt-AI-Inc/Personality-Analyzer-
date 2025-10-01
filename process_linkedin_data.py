#!/usr/bin/env python3

"""
LinkedIn Data Processor with LLM Pre-filtering
Converts LinkedIn CSV exports to filtered JSON for OCEAN5 personality analysis
"""

import json
import csv
import argparse
import os
from typing import List, Dict, Optional
from bfi_probe import LLM, LLMConfig

class LinkedInProcessor:
    """Process LinkedIn export data with LLM-powered personality relevance filtering"""
    
    def __init__(self, llm: LLM, debug: bool = False):
        self.llm = llm
        self.debug = debug
        self.personality_filter_prompt = self._create_personality_filter_prompt()
        
    def _create_personality_filter_prompt(self) -> str:
        """Create LLM prompt for personality relevance filtering"""
        return """Analyze this LinkedIn content for Big Five personality trait indicators.

Content: "{content}"

Does this content reveal personality traits in these areas:
- OPENNESS: innovative thinking, creative approaches, learning orientation, intellectual curiosity, strategic vision
- CONSCIENTIOUSNESS: planning, goal-setting, professional discipline, attention to detail, project management, reliability
- EXTRAVERSION: leadership, networking, team collaboration, public speaking, influence, social confidence in professional settings
- AGREEABLENESS: collaboration, mentoring, team support, diplomatic communication, helping others professionally
- NEUROTICISM: stress management, handling criticism, confidence under pressure, emotional regulation in work contexts

Answer with ONE WORD: YES (if it reveals meaningful personality traits) or NO (if it's just factual, promotional, or generic).

Focus on:
- Leadership and decision-making style
- Professional values and priorities
- Work approach and problem-solving
- Team interaction and collaboration patterns
- Learning and growth orientation
- Strategic thinking and vision
- Handling challenges and setbacks
- Professional relationship building

Exclude:
- Pure job descriptions or company info
- Generic congratulations or thanks
- Simple link shares without commentary
- Promotional content without personal insight
- Basic networking messages"""

    def parse_linkedin_messages(self, csv_path: str) -> List[Dict]:
        """Parse LinkedIn messages CSV file"""
        print(f"📂 Loading LinkedIn messages CSV: {csv_path}")
        
        messages = []
        
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                # Look for common LinkedIn message CSV columns
                content = None
                
                # Try different possible column names for message content
                for col_name in ['Message', 'Content', 'Text', 'Body', 'message', 'content', 'CONTENT', 'MESSAGE']:
                    if col_name in row and row[col_name]:
                        content = row[col_name].strip()
                        break
                
                if content:
                    messages.append({
                        'content': content,
                        'date': row.get('DATE', row.get('Date', row.get('Timestamp', ''))),
                        'source': 'linkedin_messages'
                    })
        
        print(f"✅ Parsed {len(messages)} LinkedIn messages")
        return messages

    def parse_linkedin_posts(self, csv_path: str) -> List[Dict]:
        """Parse LinkedIn posts CSV file"""
        print(f"📂 Loading LinkedIn posts CSV: {csv_path}")
        
        posts = []
        
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                # Look for common LinkedIn posts CSV columns
                content = None
                
                # Try different possible column names for post content
                for col_name in ['Post', 'Content', 'Text', 'Description', 'Body', 'post', 'content', 'ShareCommentary', 'SHARECOMMENTARY', 'Share Commentary']:
                    if col_name in row and row[col_name]:
                        content = row[col_name].strip()
                        break
                
                if content:
                    posts.append({
                        'content': content,
                        'date': row.get('Date', row.get('DATE', row.get('Published', row.get('Timestamp', '')))),
                        'source': 'linkedin_posts'
                    })
        
        print(f"✅ Parsed {len(posts)} LinkedIn posts")
        return posts

    def basic_content_filter(self, content: str) -> bool:
        """Apply basic filtering before LLM analysis"""
        if not content or len(content.strip()) < 10:
            return False
            
        # Remove very short content (likely not personality revealing)  
        if len(content.split()) < 5:
            return False
            
        # Remove content that's mostly URLs
        url_count = content.count('http')
        if url_count > 3 or (url_count > 0 and len(content.split()) < 20):
            return False
        
        # Filter out pure congratulations/thanks
        congrats_patterns = [
            'congratulations', 'congrats', 'thank you for', 'thanks for',
            'happy to announce', 'pleased to share', 'excited to share'
        ]
        
        content_lower = content.lower()
        is_generic = any(pattern in content_lower for pattern in congrats_patterns)
        
        # If it's congratulatory but very short, skip it
        if is_generic and len(content.split()) < 15:
            return False
            
        return True

    def is_personality_relevant(self, content: str) -> bool:
        """Use LLM to determine if content reveals personality traits (single item - for compatibility)"""
        results = self.batch_personality_analysis([content])
        return results[0] if results else False
    
    def batch_personality_analysis(self, contents: List[str], batch_size: int = 50) -> List[bool]:
        """Process multiple LinkedIn items in batched LLM calls for efficiency"""
        if not contents:
            return []
        
        results = []
        
        # Process in batches
        for i in range(0, len(contents), batch_size):
            batch = contents[i:i + batch_size]
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
            
            # Show progress for batches (always show, not just in debug)
            if len(contents) > batch_size:
                progress = min(i + batch_size, len(contents))
                print(f"   🤖 LLM batch progress: {progress}/{len(contents)} ({progress/len(contents)*100:.1f}%)")
        
        return results
    
    def _process_batch(self, batch_contents: List[str]) -> List[bool]:
        """Process a single batch of LinkedIn content"""
        try:
            # Create batched prompt
            batch_prompt = self._create_batch_prompt(batch_contents)
            
            system_msg = "You are an expert psychologist analyzing professional content for personality research. Respond with ONLY the numbered list as requested."
            response = self.llm.chat(system_msg, batch_prompt)
            
            # Parse batch response
            return self._parse_batch_response(response, len(batch_contents))
            
        except Exception as e:
            if self.debug:
                print(f"❌ Batch LLM analysis error: {e}")
            # Fallback: assume all are relevant to avoid losing data
            return [True] * len(batch_contents)
    
    def _create_batch_prompt(self, batch_contents: List[str]) -> str:
        """Create a batched prompt for multiple LinkedIn content items"""
        prompt = """Analyze these LinkedIn content items for Big Five personality trait indicators.

For each item, determine if it reveals personality traits in these areas:
- OPENNESS: innovative thinking, creative approaches, learning orientation, intellectual curiosity, strategic vision
- CONSCIENTIOUSNESS: planning, goal-setting, professional discipline, attention to detail, project management, reliability
- EXTRAVERSION: leadership, networking, team collaboration, public speaking, influence, social confidence in professional settings
- AGREEABLENESS: collaboration, mentoring, team support, diplomatic communication, helping others professionally
- NEUROTICISM: stress management, handling criticism, confidence under pressure, emotional regulation in work contexts

Focus on:
- Leadership and decision-making style
- Professional values and priorities
- Work approach and problem-solving
- Team interaction and collaboration patterns
- Learning and growth orientation
- Strategic thinking and vision
- Handling challenges and setbacks
- Professional relationship building

Exclude pure job descriptions, generic congratulations, simple link shares, or promotional content without personal insight.

"""
        
        # Add numbered items
        for i, content in enumerate(batch_contents, 1):
            # Truncate very long content to avoid token limits
            truncated_content = content[:250] + "..." if len(content) > 250 else content
            prompt += f"{i}. {truncated_content}\n\n"
        
        prompt += f"""Respond with ONLY a numbered list (1-{len(batch_contents)}) where each line is:
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

    def process_linkedin_data(self, csv_path: str, data_type: str, output_path: str, max_items: int = None) -> Dict:
        """Process LinkedIn CSV file and create filtered JSON"""
        print(f"🚀 Starting LinkedIn {data_type} processing...")
        
        # Parse LinkedIn CSV
        if data_type == 'messages':
            raw_data = self.parse_linkedin_messages(csv_path)
        elif data_type == 'posts':
            raw_data = self.parse_linkedin_posts(csv_path)
        else:
            raise ValueError(f"Unsupported LinkedIn data type: {data_type}")
        
        if not raw_data:
            print(f"❌ No {data_type} found in CSV")
            return {"error": f"No {data_type} found"}
        
        if max_items:
            raw_data = raw_data[:max_items]
            print(f"🔪 Limited to first {max_items} items for processing")
        
        processed_items = []
        stats = {
            "total_parsed": len(raw_data),
            "basic_filtered": 0,
            "llm_analyzed": 0,
            "personality_relevant": 0,
            "final_count": 0
        }
        
        print(f"🔍 Processing {data_type} with batch analysis...")
        
        # First pass: extract and basic filter all content
        basic_filtered_content = []
        for i, item in enumerate(raw_data):
            if self.debug and i % 100 == 0:
                print(f"   Basic filtering progress: {i}/{len(raw_data)} ({i/len(raw_data)*100:.1f}%)")
            
            content = item['content']
            
            # Basic filtering
            if not self.basic_content_filter(content):
                continue
                
            basic_filtered_content.append(content)
            stats["basic_filtered"] += 1
        
        print(f"🔍 Basic filtering complete: {len(basic_filtered_content)} {data_type} passed basic filters")
        print(f"🤖 Running batch LLM analysis on {len(basic_filtered_content)} {data_type}...")
        
        # Batch LLM analysis
        if basic_filtered_content:
            stats["llm_analyzed"] = len(basic_filtered_content)
            personality_results = self.batch_personality_analysis(basic_filtered_content)
            
            # Build final results
            for content, is_relevant in zip(basic_filtered_content, personality_results):
                if is_relevant:
                    processed_items.append({"full_text": content})
                    stats["personality_relevant"] += 1
                    
                    if self.debug:
                        print(f"✅ Personality relevant: {content[:80]}...")
                elif self.debug:
                    print(f"❌ Not personality relevant: {content[:80]}...")
        
        stats["final_count"] = len(processed_items)
        
        # Save results
        print(f"💾 Saving {len(processed_items)} filtered {data_type} to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_items, f, indent=2, ensure_ascii=False)
        
        # Print statistics
        self._print_processing_stats(stats, data_type)
        
        return stats

    def _print_processing_stats(self, stats: Dict, data_type: str):
        """Print processing statistics"""
        print(f"\n📊 LINKEDIN {data_type.upper()} PROCESSING STATISTICS:")
        print("=" * 50)
        print(f"📝 Total {data_type} parsed: {stats['total_parsed']}")
        print(f"🔍 Passed basic filtering: {stats['basic_filtered']} ({stats['basic_filtered']/stats['total_parsed']*100:.1f}%)")
        print(f"🤖 Analyzed by LLM: {stats['llm_analyzed']}")
        print(f"🎯 Personality relevant: {stats['personality_relevant']} ({stats['personality_relevant']/stats['llm_analyzed']*100:.1f}% of analyzed)")
        print(f"✅ Final filtered count: {stats['final_count']}")
        print(f"📈 Overall retention: {stats['final_count']/stats['total_parsed']*100:.1f}%")
        print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Process LinkedIn export data for OCEAN5 personality analysis")
    parser.add_argument("--input", type=str, required=True,
                       help="Path to LinkedIn CSV export file")
    parser.add_argument("--type", type=str, required=True, choices=["messages", "posts"],
                       help="Type of LinkedIn data (messages or posts)")
    parser.add_argument("--output", type=str, required=True,
                       help="Output path for filtered JSON")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                       choices=["gpt-4o-mini", "gpt-4o", "gpt-5"],
                       help="LLM model for personality filtering")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--max-items", type=int,
                       help="Limit processing to first N items (for testing)")
    
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
    processor = LinkedInProcessor(llm, debug=args.debug)
    
    try:
        # Process LinkedIn data
        stats = processor.process_linkedin_data(args.input, args.type, args.output, args.max_items)
        
        if "error" in stats:
            return
        
        print(f"\n🎉 SUCCESS! Processed LinkedIn {args.type}")
        print(f"📁 Input: {args.input}")
        print(f"📁 Output: {args.output}")
        print(f"🤖 Model: {args.model}")
        print(f"📊 Items retained: {stats['final_count']}/{stats['total_parsed']}")
        
    except Exception as e:
        print(f"❌ Error processing LinkedIn data: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()