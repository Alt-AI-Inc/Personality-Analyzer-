#!/usr/bin/env python3

"""
Rate-Limited Faceted BFI Personality Assessment
Optimized for API rate limits with intelligent batching and delays
"""

import argparse
import json
import os
import time
from typing import Dict, List, Optional
from bfi_probe_faceted import cross_facet_comparison
from faceted_personality import FacetedPersonalitySystem

# Import everything we need from bfi_probe
from bfi_probe import LLM, LLMConfig, BFI_S_ITEMS, administer, score

# Import the OpenAI detection logic from bfi_probe
try:
    from openai import OpenAI
    _USE_NEW = True
except Exception:
    import openai
    _USE_NEW = False

class RateLimitedLLM(LLM):
    """Enhanced LLM class with aggressive rate limiting and smarter retries"""
    
    def __init__(self, cfg: LLMConfig, debug: bool = False, requests_per_minute: int = 30):
        super().__init__(cfg, debug)
        self.requests_per_minute = requests_per_minute
        self.min_delay = 60.0 / requests_per_minute  # Minimum delay between requests
        self.last_request_time = 0
        self.request_count = 0
        
    def _enforce_rate_limit(self):
        """Enforce rate limiting with intelligent delays"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            if self.debug:
                print(f"⏱️  Rate limiting: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Extra cautious delay every 10 requests
        if self.request_count % 10 == 0:
            extra_delay = 2.0
            if self.debug:
                print(f"🛡️  Extra rate limit buffer: {extra_delay}s (request #{self.request_count})")
            time.sleep(extra_delay)
    
    def chat(self, system: str, user: str, *, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """Rate-limited chat with improved error handling"""
        self._enforce_rate_limit()
        
        mt = max_tokens if max_tokens is not None else self.cfg.max_tokens
        temp = temperature if temperature is not None else self.cfg.temperature
        
        max_retries = 8  # Increased retries
        base_delay = 2.0  # Longer base delay
        
        for attempt in range(max_retries):
            try:
                if _USE_NEW:
                    params = {
                        "model": self.cfg.model,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]
                    }
                    
                    # Handle parameter differences between reasoning and traditional models
                    if self.cfg.model.startswith(('gpt-5', 'o1', 'o3')):
                        if mt is not None:
                            params["max_completion_tokens"] = mt
                    else:
                        if mt is not None:
                            params["max_tokens"] = mt
                        if temp is not None:
                            params["temperature"] = temp
                    
                    if self.debug:
                        print(f"[DEBUG] Request #{self.request_count}: {params['model']}")
                    
                    r = self.cli.chat.completions.create(**params)
                    out = r.choices[0].message.content
                    
                    if self.debug:
                        usage = r.usage
                        print(f"[DEBUG] Tokens used: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})")
                    
                    if out is None:
                        out = ""
                    else:
                        out = out.strip()
                    
                    return out
                    
            except Exception as e:
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ["rate_limit", "ratelimit", "quota", "429"]):
                    if attempt < max_retries - 1:
                        # Exponential backoff with longer delays for rate limits
                        delay = base_delay * (2 ** attempt) + (attempt * 1.0)
                        delay = min(delay, 60.0)  # Cap at 1 minute
                        print(f"🚨 Rate limit hit! Waiting {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"❌ Max retries exceeded. Rate limit error: {e}")
                        raise e
                elif "max_tokens or model output limit" in error_str:
                    # Handle token limit errors for reasoning models
                    if self.cfg.model.startswith(('gpt-5', 'o1', 'o3')):
                        print(f"⚠️  Token limit hit, returning empty response")
                        return ""
                    else:
                        raise e
                else:
                    # Other errors - shorter retry
                    if attempt < 2:
                        delay = 1.0 + attempt
                        print(f"🔄 API error, retrying in {delay}s: {e}")
                        time.sleep(delay)
                        continue
                    else:
                        raise e
        
        return ""

def run_rate_limited_assessment():
    """Run faceted assessment with aggressive rate limiting"""
    ap = argparse.ArgumentParser(description="Rate-Limited Faceted BFI Assessment")
    ap.add_argument("--model", type=str, default="gpt-4o-mini")
    ap.add_argument("--facet", type=str, choices=["personal", "professional", "both"], default="both")
    ap.add_argument("--rpm", type=int, default=15, help="Requests per minute limit")
    ap.add_argument("--outdir", type=str, default="results")
    ap.add_argument("--debug", action="store_true")
    
    args = ap.parse_args()
    
    print(f"🐌 Rate-Limited Assessment Starting...")
    print(f"   Model: {args.model}")
    print(f"   Rate limit: {args.rpm} requests/minute")
    print(f"   Facet(s): {args.facet}")
    
    # Initialize rate-limited LLM
    cfg = LLMConfig(model=args.model, temperature=0.2, max_tokens=128)
    llm = RateLimitedLLM(cfg, debug=args.debug, requests_per_minute=args.rpm)
    
    # Estimate time based on rate limits
    if args.facet == "both":
        # P2 generation (2 requests) + BFI questions (120 requests for 2 facets)
        estimated_requests = 122
    else:
        # P2 generation (1 request) + BFI questions (60 requests for 1 facet)
        estimated_requests = 61
    
    estimated_time = (estimated_requests / args.rpm) * 60  # Convert to seconds
    print(f"   Estimated time: {estimated_time/60:.1f} minutes ({estimated_requests} requests)")
    
    # Initialize faceted personality system
    fps = FacetedPersonalitySystem()
    sources = fps.load_available_sources()
    
    if not sources:
        print("❌ No data sources found!")
        return
    
    facet_sources = fps.organize_by_facets()
    
    # Results storage
    results = {}
    os.makedirs(args.outdir, exist_ok=True)
    
    start_time = time.time()
    
    try:
        if args.facet in ["personal", "both"] and facet_sources.get("personal"):
            print(f"\n🎭 Generating Personal facet P2 profile...")
            personal_profile = fps.generate_facet_p2(llm, "personal", facet_sources["personal"])
            
            print(f"✅ Personal P2 generated ({len(personal_profile.p2_prompt)} chars)")
            print(f"🔄 Running Personal BFI assessment (60 questions)...")
            
            # Run BFI with individual questions (no batching to avoid complexity)
            from bfi_probe import administer, score, BFI_S_ITEMS
            personal_answers = administer(llm, BFI_S_ITEMS, persona=personal_profile.p2_prompt)
            personal_scores, personal_details = score(BFI_S_ITEMS, personal_answers)
            
            results['personal'] = {
                'scores': personal_scores,
                'details': personal_details,
                'p2': personal_profile.p2_prompt
            }
            
            print(f"📊 Personal Scores: {', '.join([f'{t}:{s:.2f}' for t, s in personal_scores.items()])}")
        
        if args.facet in ["professional", "both"] and facet_sources.get("professional"):
            print(f"\n💼 Generating Professional facet P2 profile...")
            professional_profile = fps.generate_facet_p2(llm, "professional", facet_sources["professional"])
            
            print(f"✅ Professional P2 generated ({len(professional_profile.p2_prompt)} chars)")
            print(f"🔄 Running Professional BFI assessment (60 questions)...")
            
            professional_answers = administer(llm, BFI_S_ITEMS, persona=professional_profile.p2_prompt)
            professional_scores, professional_details = score(BFI_S_ITEMS, professional_answers)
            
            results['professional'] = {
                'scores': professional_scores,
                'details': professional_details,
                'p2': professional_profile.p2_prompt
            }
            
            print(f"📊 Professional Scores: {', '.join([f'{t}:{s:.2f}' for t, s in professional_scores.items()])}")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Assessment interrupted by user")
        print(f"   Partial results may be available")
    except Exception as e:
        print(f"\n❌ Assessment failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
    
    # Save results and comparison
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\n⏱️  Total time: {elapsed_time/60:.1f} minutes")
    print(f"📝 API requests made: {llm.request_count}")
    print(f"📊 Actual rate: {(llm.request_count / elapsed_time) * 60:.1f} requests/minute")
    
    # Cross-facet comparison
    if 'personal' in results and 'professional' in results:
        print(f"\n🔍 Cross-Facet Comparison:")
        comparison = cross_facet_comparison(results['professional']['scores'], results['personal']['scores'])
        
        # Save detailed results
        import datetime as dt
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for facet, data in results.items():
            if data['p2']:
                p2_path = os.path.join(args.outdir, f"{facet}_facet_p2_rate_limited_{stamp}.txt")
                with open(p2_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {facet.upper()} FACET P2 PROFILE (Rate Limited)\n\n")
                    f.write(data['p2'])
                print(f"💾 Saved {facet} P2: {p2_path}")
        
        # Save comparison
        if comparison:
            import pandas as pd
            comparison_data = []
            for trait in "OCEAN":
                personal_score = results['personal']['scores'].get(trait, 0)
                professional_score = results['professional']['scores'].get(trait, 0)
                difference = professional_score - personal_score
                
                comparison_data.append({
                    'Trait': trait,
                    'Personal': personal_score,
                    'Professional': professional_score,
                    'Difference': difference,
                    'Effect': 'SIGNIFICANT' if abs(difference) >= 0.5 else 'NOTABLE' if abs(difference) >= 0.3 else 'MINIMAL'
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            csv_path = os.path.join(args.outdir, f"facet_comparison_rate_limited_{stamp}.csv")
            comparison_df.to_csv(csv_path, index=False)
            print(f"📊 Saved comparison: {csv_path}")
            print(f"\n{comparison_df.to_string(index=False)}")

if __name__ == "__main__":
    run_rate_limited_assessment()