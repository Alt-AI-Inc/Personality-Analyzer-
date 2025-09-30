#!/usr/bin/env python3

"""
Test smart P2 generation quality vs aggressive compression
"""

from smart_p2_generator import SmartP2Generator
from bfi_probe import LLM, LLMConfig

def test_smart_p2():
    print("🧠 Testing Smart P2 Generation Quality")
    
    # Initialize smart generator
    fps = SmartP2Generator()
    sources = fps.load_available_sources()
    
    if not sources:
        print("❌ No data sources found!")
        return
    
    facet_sources = fps.organize_by_facets()
    
    # Test with gpt-4o-mini
    cfg = LLMConfig(model="gpt-4o-mini", temperature=0.2, max_tokens=4000)
    llm = LLM(cfg, debug=True)
    
    # Test personal facet
    if facet_sources.get("personal"):
        print("\n🎭 Testing Personal facet smart P2...")
        try:
            personal_profile = fps.generate_smart_facet_p2(llm, "personal", facet_sources["personal"])
            
            print(f"✅ Smart Personal P2 generated!")
            print(f"   Length: {len(personal_profile.p2_prompt)} characters")
            print(f"   Estimated tokens: ~{len(personal_profile.p2_prompt.split())}")
            
            # Show preview to verify quality
            print(f"\n📝 Smart P2 Preview (first 800 chars):")
            print("-" * 60)
            print(personal_profile.p2_prompt[:800] + "...")
            print("-" * 60)
            
            # Check if it has all the detailed sections
            sections = ["BIG FIVE TRAITS", "INTERESTS & PREFERENCES", "COMMUNICATION STYLE", 
                       "LANGUAGE PATTERNS", "SOCIAL INTERACTIONS", "WORK & PRODUCTIVITY",
                       "DECISION-MAKING", "EMOTIONAL EXPRESSION", "VALUES & MOTIVATIONS"]
            
            missing_sections = []
            for section in sections:
                if section not in personal_profile.personality_analysis:
                    missing_sections.append(section)
            
            if missing_sections:
                print(f"⚠️  Missing sections: {', '.join(missing_sections)}")
            else:
                print(f"✅ All personality sections present!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
    print("\n✅ Smart compression test completed!")

if __name__ == "__main__":
    test_smart_p2()