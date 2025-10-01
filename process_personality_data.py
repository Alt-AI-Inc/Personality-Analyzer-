#!/usr/bin/env python3

"""
Unified Personality Data Processor
Processes multiple data sources (Twitter, WhatsApp, etc.) with LLM pre-filtering for OCEAN5 analysis
"""

import json
import argparse
import os
from typing import Dict, List
from bfi_probe import LLM, LLMConfig
from process_twitter_data import TwitterProcessor
from process_whatsapp_data import WhatsAppProcessor
from process_linkedin_data import LinkedInProcessor

class UnifiedPersonalityProcessor:
    """Unified processor for all personality data sources"""
    
    def __init__(self, llm: LLM, debug: bool = False, source_type_filter: str = "all"):
        self.llm = llm
        self.debug = debug
        self.source_type_filter = source_type_filter
        self.twitter_processor = TwitterProcessor(llm, debug)
        self.whatsapp_processor = WhatsAppProcessor(llm, debug)
        self.linkedin_processor = LinkedInProcessor(llm, debug)
    
    def process_all_sources(self, config_path: str = "processing_config.json") -> Dict:
        """Process all configured data sources from processing_config.json"""
        
        if not os.path.exists(config_path):
            print(f"❌ Configuration file not found: {config_path}")
            print("   Create a processing_config.json file with your data sources")
            return {}
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        results = {}
        
        print("🚀 Starting unified personality data processing...")
        
        # Filter sources based on source_type parameter if provided
        all_sources = config.get('sources', [])
        if self.source_type_filter != "all":
            filtered_sources = [s for s in all_sources if s['type'] == self.source_type_filter]
        else:
            filtered_sources = all_sources
        
        print(f"📋 Processing {len(filtered_sources)} data sources (filter: {self.source_type_filter})")
        
        for source in filtered_sources:
            source_name = source['name']
            source_type = source['type']
            
            print(f"\n📂 Processing: {source_name} ({source_type})")
            
            try:
                if source_type == 'twitter':
                    stats = self.twitter_processor.process_tweets(
                        tweets_js_path=source['input_path'],
                        output_path=source['output_path'],
                        max_tweets=source.get('max_items')
                    )
                    
                elif source_type == 'whatsapp':
                    stats = self.whatsapp_processor.process_whatsapp(
                        whatsapp_path=source['input_path'],
                        target_person=source['target_person'],
                        output_path=source['output_path'],
                        max_messages=source.get('max_items')
                    )
                    
                elif source_type == 'linkedin_messages':
                    stats = self.linkedin_processor.process_linkedin_data(
                        csv_path=source['input_path'],
                        data_type='messages',
                        output_path=source['output_path'],
                        max_items=source.get('max_items')
                    )
                    
                elif source_type == 'linkedin_posts':
                    stats = self.linkedin_processor.process_linkedin_data(
                        csv_path=source['input_path'],
                        data_type='posts',
                        output_path=source['output_path'],
                        max_items=source.get('max_items')
                    )
                else:
                    print(f"⚠️  Unknown source type: {source_type}")
                    continue
                
                results[source_name] = stats
                print(f"✅ Completed {source_name}: {stats.get('final_count', 0)} items processed")
                
            except Exception as e:
                print(f"❌ Error processing {source_name}: {e}")
                results[source_name] = {"error": str(e)}
        
        # Generate data_sources_config.json for bfi_probe_faceted.py
        if results:
            self._generate_data_sources_config(config)
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _generate_data_sources_config(self, processing_config: Dict):
        """Generate data_sources_config.json for bfi_probe_faceted.py"""
        
        data_sources = []
        
        for source in processing_config.get('sources', []):
            if source['type'] == 'whatsapp':
                data_source = {
                    "name": source['name'],
                    "source": "whatsapp", 
                    "type": "chat",
                    "path": source['output_path'],
                    "category": source.get('category', 'personal'),
                    "description": source.get('description', f"WhatsApp messages from {source.get('target_person', 'user')}"),
                    "communication_traits": {
                        "formality": "very_casual",
                        "authenticity": "high", 
                        "filter_level": "minimal",
                        "emotional_openness": "high",
                        "abbreviations": "common",
                        "emojis": "frequent"
                    }
                }
            elif source['type'] == 'twitter':
                data_source = {
                    "name": source['name'],
                    "source": "twitter",
                    "type": "posts",
                    "path": source['output_path'], 
                    "category": source.get('category', 'personal'),
                    "description": source.get('description', "Twitter posts for personality analysis"),
                    "communication_traits": {
                        "formality": "casual",
                        "authenticity": "medium",
                        "filter_level": "public_curation", 
                        "emotional_openness": "medium",
                        "abbreviations": "common",
                        "emojis": "contextual"
                    }
                }
            elif source['type'] == 'linkedin_messages':
                data_source = {
                    "name": source['name'],
                    "source": "linkedin", 
                    "type": "chat",
                    "path": source['output_path'],
                    "category": source.get('category', 'professional'),
                    "description": source.get('description', "LinkedIn direct messages and professional networking conversations"),
                    "communication_traits": {
                        "formality": "semi_formal",
                        "authenticity": "high",
                        "filter_level": "professional_context",
                        "emotional_openness": "medium",
                        "abbreviations": "rare",
                        "emojis": "minimal"
                    }
                }
            elif source['type'] == 'linkedin_posts':
                data_source = {
                    "name": source['name'],
                    "source": "linkedin",
                    "type": "articles",
                    "path": source['output_path'],
                    "category": source.get('category', 'professional'), 
                    "description": source.get('description', "LinkedIn posts and professional thought leadership content"),
                    "communication_traits": {
                        "formality": "formal",
                        "authenticity": "medium",
                        "filter_level": "professional_curation",
                        "emotional_openness": "medium",
                        "abbreviations": "rare",
                        "emojis": "minimal"
                    }
                }
            else:
                continue  # Skip unsupported types
            
            data_sources.append(data_source)
        
        # Create the full data_sources_config.json structure
        data_sources_config = {
            "data_sources": data_sources,
            "facet_definitions": {
                "professional": {
                    "description": "Work-related communication showing professional personality traits",
                    "key_traits": [
                        "conscientiousness_amplified",
                        "agreeableness_work_context", 
                        "extraversion_leadership",
                        "neuroticism_stress_management",
                        "openness_innovation"
                    ],
                    "context_considerations": [
                        "Hierarchy and power dynamics",
                        "Team collaboration patterns",
                        "Decision-making style",
                        "Conflict resolution approach",
                        "Goal orientation and achievement focus"
                    ]
                },
                "personal": {
                    "description": "Private and social communication showing authentic personality traits", 
                    "key_traits": [
                        "neuroticism_authentic",
                        "agreeableness_interpersonal",
                        "extraversion_social", 
                        "openness_interests",
                        "conscientiousness_lifestyle"
                    ],
                    "context_considerations": [
                        "Relationship dynamics",
                        "Emotional expression patterns",
                        "Leisure and hobby preferences", 
                        "Social interaction style",
                        "Personal values and beliefs"
                    ]
                }
            },
            "communication_type_calibrations": {
                "chat": {
                    "characteristics": "Real-time, conversational, reactive",
                    "authenticity_modifier": 1.2,
                    "spontaneity_indicator": "high",
                    "editing_level": "minimal"
                },
                "posts": {
                    "characteristics": "Curated, public-facing, considered",
                    "authenticity_modifier": 0.8,
                    "spontaneity_indicator": "medium", 
                    "editing_level": "moderate"
                }
            },
            "source_specific_calibrations": {
                "whatsapp": {
                    "platform_bias": "authentic_expression",
                    "trait_amplifications": {
                        "neuroticism": 0.1,
                        "agreeableness": 0.2
                    },
                    "trait_suppressions": {},
                    "communication_markers": ["casual_language", "abbreviations", "emojis", "immediate_reactions"]
                },
                "twitter": {
                    "platform_bias": "performative_expression", 
                    "trait_amplifications": {
                        "extraversion": 0.4,
                        "openness": 0.3,
                        "neuroticism": 0.2
                    },
                    "trait_suppressions": {
                        "agreeableness": 0.1
                    },
                    "communication_markers": ["public_performance", "brevity", "engagement_seeking", "opinion_sharing"]
                }
            }
        }
        
        # Save data_sources_config.json
        with open("data_sources_config.json", 'w') as f:
            json.dump(data_sources_config, f, indent=2)
        
        print(f"✅ Generated data_sources_config.json with {len(data_sources)} sources")
    
    def _print_summary(self, results: Dict):
        """Print processing summary"""
        print("\n" + "="*60)
        print("📊 UNIFIED PROCESSING SUMMARY")
        print("="*60)
        
        total_processed = 0
        successful_sources = 0
        
        for source_name, stats in results.items():
            if "error" in stats:
                print(f"❌ {source_name}: ERROR - {stats['error']}")
            else:
                final_count = stats.get('final_count', 0)
                total_parsed = stats.get('total_parsed', 0)
                retention = (final_count/total_parsed*100) if total_parsed > 0 else 0
                
                print(f"✅ {source_name}: {final_count} items ({retention:.1f}% retention)")
                total_processed += final_count
                successful_sources += 1
        
        print("-"*60)
        print(f"🎯 Total items processed: {total_processed}")
        print(f"📁 Successful sources: {successful_sources}/{len(results)}")
        print("="*60)

def create_sample_config():
    """Create a sample processing_config.json file"""
    sample_config = {
        "sources": [
            {
                "name": "shreyas_tweets",
                "type": "twitter",
                "input_path": "Data/tweets.js",
                "output_path": "Data/filtered_tweets.json",
                "category": "professional",
                "max_items": None,
                "description": "Shreyas's Twitter posts for personality analysis"
            },
            {
                "name": "shreyas_whatsapp",
                "type": "whatsapp", 
                "input_path": "Data/Abhishek.txt",
                "target_person": "Shreyas Srinivasan",
                "output_path": "Data/WhatsApp.json",
                "category": "personal",
                "max_items": None,
                "description": "Shreyas's WhatsApp messages for personality analysis"
            },
            {
                "name": "shreyas_linkedin_messages",
                "type": "linkedin_messages",
                "input_path": "Data/LinkedInMessagesShreyas.csv",
                "output_path": "Data/linkedin_messages_simple.json",
                "category": "professional",
                "max_items": None,
                "description": "Shreyas's LinkedIn messages for professional personality analysis"
            },
            {
                "name": "shreyas_linkedin_posts", 
                "type": "linkedin_posts",
                "input_path": "Data/ShreyasLinkedInPosts.csv",
                "output_path": "Data/linkedin_posts_simple.json", 
                "category": "professional",
                "max_items": None,
                "description": "Shreyas's LinkedIn posts for professional personality analysis"
            },
            {
                "name": "abhishek_tweets",
                "type": "twitter",
                "input_path": "Data/Abhishek_tweets.js", 
                "output_path": "Data/Abhishek_personality_tweets.json",
                "category": "professional",
                "max_items": None,
                "description": "Abhishek's Twitter posts for personality analysis"
            }
        ]
    }
    
    with open("processing_config.json", 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print("✅ Created sample processing_config.json")
    print("   Edit this file to configure your data sources and file paths")

def main():
    parser = argparse.ArgumentParser(description="Unified personality data processor")
    parser.add_argument("--config", type=str, default="processing_config.json",
                       help="Path to processing configuration file")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                       choices=["gpt-4o-mini", "gpt-4o", "gpt-5"],
                       help="LLM model for personality filtering")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--create-config", action="store_true",
                       help="Create a sample processing_config.json file and exit")
    parser.add_argument("--source-type", type=str, 
                       choices=["twitter", "whatsapp", "linkedin_messages", "linkedin_posts", "all"], default="all",
                       help="Process only sources matching this type from processing_config.json (default: all)")
    
    args = parser.parse_args()
    
    # Create sample config if requested
    if args.create_config:
        create_sample_config()
        return
    
    # Initialize LLM
    print(f"🤖 Initializing {args.model} for personality filtering...")
    cfg = LLMConfig(model=args.model, temperature=0.3, max_tokens=2000)
    llm = LLM(cfg, debug=args.debug)
    
    # Initialize unified processor
    processor = UnifiedPersonalityProcessor(llm, debug=args.debug, source_type_filter=args.source_type)
    
    # Process all sources
    results = processor.process_all_sources(args.config)
    
    if results:
        print(f"\n🎉 Processing complete! Results saved to configured output paths.")
    else:
        print("❌ No processing completed. Check configuration and try again.")

if __name__ == "__main__":
    main()