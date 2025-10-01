#!/usr/bin/env python3

"""
Twitter Data Processor with LLM Pre-filtering
Converts tweets.js export to filtered JSON for OCEAN5 personality analysis
"""

import json
import re
import argparse
import os
from typing import List, Dict, Optional
from bfi_probe import LLM, LLMConfig

class TwitterProcessor:
    """Process Twitter export data with LLM-powered personality relevance filtering"""
    
    def __init__(self, llm: LLM, debug: bool = False):
        self.llm = llm
        self.debug = debug
        self.personality_filter_prompt = self._create_personality_filter_prompt()
        
    def _create_personality_filter_prompt(self) -> str:
        """Create LLM prompt for personality relevance filtering"""
        return """Analyze this tweet for Big Five personality trait indicators.

Tweet: "{content}"

Does this tweet reveal personality traits in these areas:
- OPENNESS: creativity, curiosity, abstract thinking, artistic interests, unconventional ideas
- CONSCIENTIOUSNESS: organization, planning, reliability, goal-setting, work ethic, discipline  
- EXTRAVERSION: social energy, enthusiasm, assertiveness, talkativeness, leadership
- AGREEABLENESS: cooperation, trust, empathy, kindness, helping others, conflict avoidance
- NEUROTICISM: emotional reactions, anxiety, stress, mood changes, vulnerability, worry

Answer with ONE WORD: YES (if it reveals meaningful personality traits) or NO (if it's just factual, promotional, or generic).

Focus on authentic personal expression, opinions, reactions, decision-making, social behavior, emotional responses, or lifestyle choices."""

    def parse_twitter_export(self, tweets_js_path: str) -> List[Dict]:
        """Parse Twitter export file (tweets.js format)"""
        print(f"📂 Loading Twitter export: {tweets_js_path}")
        
        with open(tweets_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON from window.YTD.tweets.part0 format
        # Look for the array after the equals sign
        json_start = content.find('[')
        json_end = content.rfind(']') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("Could not find JSON array in tweets.js file")
        
        json_content = content[json_start:json_end]
        
        try:
            tweets_data = json.loads(json_content)
            print(f"✅ Parsed {len(tweets_data)} total tweets")
            return tweets_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}")

    def extract_tweet_content(self, tweet_data: Dict) -> Optional[str]:
        """Extract full_text from complex tweet structure"""
        try:
            # Navigate the nested structure
            if 'tweet' in tweet_data:
                tweet = tweet_data['tweet']
            else:
                tweet = tweet_data
                
            # Try different possible text fields
            for field in ['full_text', 'text', 'content']:
                if field in tweet:
                    return tweet[field].strip()
                    
            return None
        except Exception:
            return None

    def basic_content_filter(self, content: str) -> bool:
        """Apply basic filtering before LLM analysis"""
        if not content or len(content.strip()) < 10:
            return False
            
        # Remove retweets
        if content.startswith('RT @') or content.startswith('RT:'):
            return False
            
        # Remove very short tweets (likely not personality revealing)
        if len(content.split()) < 5:
            return False
            
        # Remove tweets that are mostly URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, content)
        if len(' '.join(urls)) > len(content) * 0.5:
            return False
            
        # Remove tweets that are mostly mentions (likely replies without context)
        mention_pattern = r'@\w+'
        mentions = re.findall(mention_pattern, content)
        if len(' '.join(mentions)) > len(content) * 0.4:
            return False
            
        return True

    def is_personality_relevant(self, content: str) -> bool:
        """Use LLM to determine if content reveals personality traits (single item - for compatibility)"""
        results = self.batch_personality_analysis([content])
        return results[0] if results else False
    
    def batch_personality_analysis(self, contents: List[str], batch_size: int = 50) -> List[bool]:
        """Process multiple items in batched LLM calls for efficiency"""
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
        """Process a single batch of content items"""
        try:
            # Create batched prompt
            batch_prompt = self._create_batch_prompt(batch_contents)
            
            system_msg = "You are an expert psychologist analyzing social media content for personality research. Respond with ONLY the numbered list as requested."
            response = self.llm.chat(system_msg, batch_prompt)
            
            # Parse batch response
            return self._parse_batch_response(response, len(batch_contents))
            
        except Exception as e:
            if self.debug:
                print(f"❌ Batch LLM analysis error: {e}")
            # Fallback: assume all are relevant to avoid losing data
            return [True] * len(batch_contents)
    
    def _create_batch_prompt(self, batch_contents: List[str]) -> str:
        """Create a batched prompt for multiple content items"""
        prompt = """Analyze these tweets for Big Five personality trait indicators.

For each tweet, determine if it reveals personality traits in these areas:
- OPENNESS: creativity, curiosity, abstract thinking, artistic interests, unconventional ideas
- CONSCIENTIOUSNESS: organization, planning, reliability, goal-setting, work ethic, discipline  
- EXTRAVERSION: social energy, enthusiasm, assertiveness, talkativeness, leadership
- AGREEABLENESS: cooperation, trust, empathy, kindness, helping others, conflict avoidance
- NEUROTICISM: emotional reactions, anxiety, stress, mood changes, vulnerability, worry

Focus on authentic personal expression, opinions, reactions, decision-making, social behavior, emotional responses, or lifestyle choices.

Exclude pure factual information, promotional content, or generic statements.

"""
        
        # Add numbered items
        for i, content in enumerate(batch_contents, 1):
            # Truncate very long content to avoid token limits
            truncated_content = content[:300] + "..." if len(content) > 300 else content
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

    def process_tweets(self, tweets_js_path: str, output_path: str, max_tweets: int = None) -> Dict:
        """Process Twitter export file and create filtered JSON"""
        print("🚀 Starting Twitter data processing...")
        
        # Parse Twitter export
        raw_tweets = self.parse_twitter_export(tweets_js_path)
        
        if max_tweets:
            raw_tweets = raw_tweets[:max_tweets]
            print(f"🔪 Limited to first {max_tweets} tweets for processing")
        
        processed_tweets = []
        stats = {
            "total_parsed": len(raw_tweets),
            "basic_filtered": 0,
            "llm_analyzed": 0,
            "personality_relevant": 0,
            "final_count": 0
        }
        
        print("🔍 Processing tweets with batch analysis...")
        
        # First pass: extract and basic filter all tweets
        basic_filtered_tweets = []
        for i, tweet_data in enumerate(raw_tweets):
            if self.debug and i % 500 == 0:
                print(f"   Basic filtering progress: {i}/{len(raw_tweets)} ({i/len(raw_tweets)*100:.1f}%)")
            
            # Extract content
            content = self.extract_tweet_content(tweet_data)
            if not content:
                continue
                
            # Basic filtering
            if not self.basic_content_filter(content):
                continue
                
            basic_filtered_tweets.append(content)
            stats["basic_filtered"] += 1
        
        print(f"🔍 Basic filtering complete: {len(basic_filtered_tweets)} tweets passed basic filters")
        print(f"🤖 Running batch LLM analysis on {len(basic_filtered_tweets)} tweets...")
        
        # Batch LLM analysis
        if basic_filtered_tweets:
            stats["llm_analyzed"] = len(basic_filtered_tweets)
            personality_results = self.batch_personality_analysis(basic_filtered_tweets)
            
            # Build final results
            for content, is_relevant in zip(basic_filtered_tweets, personality_results):
                if is_relevant:
                    processed_tweets.append({"full_text": content})
                    stats["personality_relevant"] += 1
                    
                    if self.debug:
                        print(f"✅ Personality relevant: {content[:80]}...")
                elif self.debug:
                    print(f"❌ Not personality relevant: {content[:80]}...")
        
        stats["final_count"] = len(processed_tweets)
        
        # Save results
        print(f"💾 Saving {len(processed_tweets)} filtered tweets to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_tweets, f, indent=2, ensure_ascii=False)
        
        # Print statistics
        self._print_processing_stats(stats)
        
        return stats

    def _print_processing_stats(self, stats: Dict):
        """Print processing statistics"""
        print("\n📊 PROCESSING STATISTICS:")
        print("=" * 50)
        print(f"📝 Total tweets parsed: {stats['total_parsed']}")
        print(f"🔍 Passed basic filtering: {stats['basic_filtered']} ({stats['basic_filtered']/stats['total_parsed']*100:.1f}%)")
        print(f"🤖 Analyzed by LLM: {stats['llm_analyzed']}")
        print(f"🎯 Personality relevant: {stats['personality_relevant']} ({stats['personality_relevant']/stats['llm_analyzed']*100:.1f}% of analyzed)")
        print(f"✅ Final filtered count: {stats['final_count']}")
        print(f"📈 Overall retention: {stats['final_count']/stats['total_parsed']*100:.1f}%")
        print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Process Twitter export data for OCEAN5 personality analysis")
    parser.add_argument("--input", type=str, required=True,
                       help="Path to tweets.js export file")
    parser.add_argument("--output", type=str, default="filtered_tweets.json",
                       help="Output path for filtered tweets JSON")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                       choices=["gpt-4o-mini", "gpt-4o", "gpt-5"],
                       help="LLM model for personality filtering")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--max-tweets", type=int,
                       help="Limit processing to first N tweets (for testing)")
    
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
    processor = TwitterProcessor(llm, debug=args.debug)
    
    try:
        # Process tweets
        stats = processor.process_tweets(args.input, args.output, args.max_tweets)
        
        print(f"\n🎉 SUCCESS! Processed Twitter data")
        print(f"📁 Input: {args.input}")
        print(f"📁 Output: {args.output}")
        print(f"🤖 Model: {args.model}")
        print(f"📊 Tweets retained: {stats['final_count']}/{stats['total_parsed']}")
        
    except Exception as e:
        print(f"❌ Error processing Twitter data: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()