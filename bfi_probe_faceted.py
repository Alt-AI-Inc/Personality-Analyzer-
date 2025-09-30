#!/usr/bin/env python3

"""
Enhanced BFI Probe with Faceted Personality Assessment
Supports Professional vs Personal personality facets
"""

import argparse
import json
import os
from typing import Dict, List, Optional
from bfi_probe import LLM, LLMConfig, BFI_S_ITEMS, administer, score, compare_df, save_detailed_results
from faceted_personality import FacetedPersonalitySystem
import datetime as dt

def load_faceted_assessment_config(config_path: str = "data_sources_config.json") -> Dict:
    """Load the faceted assessment configuration"""
    if not os.path.exists(config_path):
        print(f"⚠️  Config file not found: {config_path}")
        print("   Using fallback to single-source mode")
        return None
        
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def faceted_assessment(llm: LLM, facet_name: str, config: Dict, args) -> tuple:
    """Run BFI assessment for a specific personality facet"""
    print(f"\n🎭 Running {facet_name} facet assessment...")
    
    # Initialize faceted personality system
    fps = FacetedPersonalitySystem()
    fps.load_available_sources()
    
    # Generate P2 profile for the specified facet
    facet_profiles = fps.generate_all_facets(llm)
    
    if facet_name not in facet_profiles:
        print(f"❌ No data available for {facet_name} facet")
        return None, None
    
    facet_p2 = facet_profiles[facet_name].p2_prompt
    
    print(f"✅ Generated {facet_name} P2 profile ({len(facet_p2)} chars)")
    
    if args.debug:
        print(f"\n[{facet_name.upper()} P2 PROFILE]")
        print(facet_p2[:1000] + "..." if len(facet_p2) > 1000 else facet_p2)
        print("---")
    
    # Run BFI assessment with facet-specific P2
    # Disable batching for reasoning models  
    use_batched = args.batched and not llm.cfg.model.startswith(('gpt-5', 'o1', 'o3'))
    
    if use_batched:
        from bfi_probe import administer_batched
        facet_answers = administer_batched(llm, BFI_S_ITEMS, persona=facet_p2, as_if=None, platform=None)
    else:
        if args.batched and llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')):
            print(f"⚠️  Batching disabled for {llm.cfg.model} - reasoning models can't handle 30 questions at once")
        facet_answers = administer(llm, BFI_S_ITEMS, persona=facet_p2, as_if=None, platform=None)
    
    facet_scores, facet_details = score(BFI_S_ITEMS, facet_answers)
    
    print(f"📊 {facet_name.capitalize()} Facet Scores:")
    for trait, score in facet_scores.items():
        print(f"   {trait}: {score:.2f}")
    
    return facet_scores, facet_details, facet_p2, facet_profiles[facet_name]

def cross_facet_comparison(professional_scores: Dict, personal_scores: Dict) -> Dict:
    """Compare personality traits across professional and personal facets"""
    if not professional_scores or not personal_scores:
        return {}
    
    comparison = {}
    print(f"\n🔍 Cross-Facet Comparison:")
    print(f"{'Trait':<12} {'Personal':<10} {'Professional':<12} {'Difference':<12} {'Context Effect'}")
    print("-" * 65)
    
    for trait in "OCEAN":
        personal = personal_scores.get(trait, 0)
        professional = professional_scores.get(trait, 0)
        difference = professional - personal
        
        if abs(difference) >= 0.3:
            effect = "SIGNIFICANT" if abs(difference) >= 0.5 else "NOTABLE"
        else:
            effect = "MINIMAL"
            
        comparison[trait] = {
            'personal': personal,
            'professional': professional, 
            'difference': difference,
            'effect': effect
        }
        
        print(f"{trait:<12} {personal:<10.2f} {professional:<12.2f} {difference:<+12.2f} {effect}")
    
    return comparison

def main():
    ap = argparse.ArgumentParser(description="Faceted BFI Personality Assessment")
    ap.add_argument("--model", type=str, default="gpt-4o-mini")
    ap.add_argument("--temperature", type=float, default=0.2) 
    ap.add_argument("--facet", type=str, choices=["personal", "professional", "both"], default="both",
                   help="Which personality facet(s) to assess")
    ap.add_argument("--config", type=str, default="data_sources_config.json",
                   help="Path to data sources configuration file")
    ap.add_argument("--outdir", type=str, default="results")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--batched", action="store_true", help="Use fast batched assessment")
    ap.add_argument("--compare-facets", action="store_true", 
                   help="Generate detailed comparison between facets")
    
    # Fallback options for single-source mode
    ap.add_argument("--twitter", type=str, default=None, help="Twitter data file (fallback mode)")
    ap.add_argument("--whatsapp", type=str, default=None, help="WhatsApp data file (fallback mode)")
    
    args = ap.parse_args()
    
    # Initialize LLM
    cfg = LLMConfig(model=args.model, temperature=args.temperature, max_tokens=128)
    llm = LLM(cfg, debug=args.debug)
    os.makedirs(args.outdir, exist_ok=True)
    
    # Load configuration
    config = load_faceted_assessment_config(args.config)
    
    if not config:
        # Fallback to original single-source mode
        print("🔄 Falling back to single-source assessment mode...")
        if args.twitter or args.whatsapp:
            # Import and run original BFI probe logic
            print("   Use the original bfi_probe.py for single-source assessment")
        else:
            print("❌ No data sources specified. Use --twitter or --whatsapp for fallback mode")
        return
    
    # Results storage
    results = {
        'personal': {'scores': None, 'details': None, 'p2': None, 'profile': None},
        'professional': {'scores': None, 'details': None, 'p2': None, 'profile': None},
        'comparison': None
    }
    
    # Run faceted assessments
    if args.facet in ["personal", "both"]:
        try:
            personal_data = faceted_assessment(llm, "personal", config, args)
            if personal_data and len(personal_data) >= 4:
                results['personal']['scores'] = personal_data[0]
                results['personal']['details'] = personal_data[1] 
                results['personal']['p2'] = personal_data[2]
                results['personal']['profile'] = personal_data[3]
        except Exception as e:
            print(f"❌ Personal facet assessment failed: {e}")
    
    if args.facet in ["professional", "both"]:
        try:
            professional_data = faceted_assessment(llm, "professional", config, args)
            if professional_data and len(professional_data) >= 4:
                results['professional']['scores'] = professional_data[0]
                results['professional']['details'] = professional_data[1]
                results['professional']['p2'] = professional_data[2]
                results['professional']['profile'] = professional_data[3]
        except Exception as e:
            print(f"❌ Professional facet assessment failed: {e}")
    
    # Cross-facet comparison
    if args.facet == "both" and results['personal']['scores'] and results['professional']['scores']:
        results['comparison'] = cross_facet_comparison(
            results['professional']['scores'],
            results['personal']['scores']
        )
    
    # Save results
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save P2 profiles
    for facet in ['personal', 'professional']:
        if results[facet]['p2']:
            p2_path = os.path.join(args.outdir, f"{facet}_facet_p2_{stamp}.txt")
            with open(p2_path, 'w', encoding='utf-8') as f:
                f.write(f"# {facet.upper()} FACET P2 PROFILE\n\n")
                f.write(results[facet]['p2'])
            print(f"💾 Saved {facet} P2 profile: {p2_path}")
    
    # Create comparison DataFrame and save
    if results['personal']['scores'] and results['professional']['scores']:
        # Create a comparison CSV
        comparison_data = []
        for trait in "OCEAN":
            personal_score = results['personal']['scores'].get(trait, 0)
            professional_score = results['professional']['scores'].get(trait, 0)
            difference = professional_score - personal_score
            
            comparison_data.append({
                'Trait': trait,
                'Personal_Score': personal_score,
                'Professional_Score': professional_score, 
                'Difference': difference,
                'Abs_Difference': abs(difference),
                'Context_Effect': 'SIGNIFICANT' if abs(difference) >= 0.5 else 'NOTABLE' if abs(difference) >= 0.3 else 'MINIMAL'
            })
        
        import pandas as pd
        comparison_df = pd.DataFrame(comparison_data)
        csv_path = os.path.join(args.outdir, f"facet_comparison_{stamp}.csv")
        comparison_df.to_csv(csv_path, index=False)
        print(f"📊 Saved facet comparison: {csv_path}")
        print(f"\n{comparison_df.to_string(index=False)}")
        
        # Detailed comparison report
        if args.compare_facets:
            report_path = os.path.join(args.outdir, f"facet_analysis_report_{stamp}.txt")
            with open(report_path, 'w') as f:
                f.write("FACETED PERSONALITY ANALYSIS REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("CROSS-FACET TRAIT COMPARISON\n")
                f.write("-" * 30 + "\n")
                f.write(comparison_df.to_string(index=False))
                f.write("\n\n")
                
                # Add insights about significant differences
                significant_diffs = comparison_df[comparison_df['Context_Effect'] != 'MINIMAL']
                if not significant_diffs.empty:
                    f.write("SIGNIFICANT CONTEXT EFFECTS\n")
                    f.write("-" * 25 + "\n")
                    for _, row in significant_diffs.iterrows():
                        trait = row['Trait']
                        diff = row['Difference']
                        direction = "higher in professional" if diff > 0 else "higher in personal"
                        f.write(f"{trait}: {direction} contexts ({diff:+.2f} difference)\n")
                
            print(f"📋 Saved detailed analysis: {report_path}")
    
    else:
        print("⚠️  Could not create comparison - missing facet data")

if __name__ == "__main__":
    main()