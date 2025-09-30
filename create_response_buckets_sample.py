#!/usr/bin/env python3

"""
WhatsApp Response Bucket Analyzer - Sample Version
Analyzes a representative sample of WhatsApp messages to create response buckets
"""

import random
from create_response_buckets import WhatsAppBucketAnalyzer
from bfi_probe import LLM, LLMConfig

class SampleWhatsAppBucketAnalyzer(WhatsAppBucketAnalyzer):
    """Sample-based analyzer for faster processing"""
    
    def categorize_message_pairs(self, person_messages, context_messages, sample_size=500):
        """Categorize a representative sample of message pairs"""
        
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
        
        print(f"🔗 Created {len(message_pairs)} total message pairs")
        
        # Take a representative sample
        if len(message_pairs) > sample_size:
            print(f"📊 Sampling {sample_size} representative pairs from {len(message_pairs)} total")
            # Use random sampling to get variety
            sampled_pairs = random.sample(message_pairs, sample_size)
        else:
            sampled_pairs = message_pairs
            print(f"📊 Using all {len(sampled_pairs)} pairs (less than sample size)")
        
        # Batch categorization with LLM
        return self._batch_categorize_messages(sampled_pairs)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze WhatsApp export sample to create response buckets")
    parser.add_argument("whatsapp_file", help="Path to WhatsApp export file")
    parser.add_argument("person_name", help="Name of person whose messages to analyze")
    parser.add_argument("--output", "-o", help="Output JSON file", default="response_buckets_sample.json")
    parser.add_argument("--sample-size", type=int, default=500, help="Number of pairs to sample")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    print(f"🤖 WhatsApp Response Bucket Analyzer - Sample Version")
    print(f"📱 File: {args.whatsapp_file}")
    print(f"👤 Person: {args.person_name}")
    print(f"📊 Sample size: {args.sample_size}")
    print(f"💾 Output: {args.output}")
    print("=" * 70)
    
    # Set random seed for reproducible sampling
    random.seed(42)
    
    # Initialize analyzer
    llm = LLM(LLMConfig(model=args.model, temperature=0.1), debug=args.debug)
    analyzer = SampleWhatsAppBucketAnalyzer(llm)
    
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
    
    # Categorize sample of message pairs
    buckets = analyzer.categorize_message_pairs(person_messages, context_messages, args.sample_size)
    
    # Analyze response patterns
    bucket_analysis = analyzer.analyze_response_patterns(buckets)
    
    # Save results
    analyzer.save_buckets(bucket_analysis, args.output, args.person_name)
    
    print(f"\n✅ Analysis complete! Sampled {args.sample_size} pairs from {len(person_messages)} total messages.")
    print(f"📁 Results saved to: {args.output}")

if __name__ == "__main__":
    main()