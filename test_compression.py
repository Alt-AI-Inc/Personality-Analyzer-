#!/usr/bin/env python3

"""
Quick test of compressed P2 generation
"""

from compressed_p2_generator import CompressedP2Generator
from bfi_probe import LLM, LLMConfig

def test_compressed_p2():
    print("🧪 Testing Compressed P2 Generation")
    
    # Initialize compressed generator
    fps = CompressedP2Generator()
    sources = fps.load_available_sources()
    
    if not sources:
        print("❌ No data sources found!")
        return
    
    facet_sources = fps.organize_by_facets()
    
    # Test with gpt-4o-mini which has higher rate limits
    cfg = LLMConfig(model="gpt-4o-mini", temperature=0.2, max_tokens=2000)
    llm = LLM(cfg, debug=True)
    
    # Test personal facet (smaller dataset)
    if facet_sources.get("personal"):
        print("\n🎭 Testing Personal facet compressed P2...")
        try:
            personal_profile = fps.generate_compressed_facet_p2(llm, "personal", facet_sources["personal"])
            
            print(f"✅ Compressed Personal P2 generated!")
            print(f"   Length: {len(personal_profile.p2_prompt)} characters")
            print(f"   Estimated tokens: ~{len(personal_profile.p2_prompt.split())}")
            
            # Show preview
            print(f"\n📝 P2 Preview (first 500 chars):")
            print("-" * 50)
            print(personal_profile.p2_prompt[:500] + "...")
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
    print("\n✅ Compression test completed!")

if __name__ == "__main__":
    test_compressed_p2()