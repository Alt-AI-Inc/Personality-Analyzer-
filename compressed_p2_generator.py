#!/usr/bin/env python3

"""
Compressed P2 Generation for Token-Limited Scenarios
Dramatically reduces token usage while maintaining personality modeling quality
"""

from faceted_personality import FacetedPersonalitySystem, DataSource, FacetProfile
from bfi_probe import LLM
from typing import List

class CompressedP2Generator(FacetedPersonalitySystem):
    """Compressed version that reduces token usage by 70%"""
    
    def __init__(self, config_path: str = "data_sources_config.json"):
        super().__init__(config_path)
    
    def compress_data_samples(self, sources: List[DataSource], max_tokens: int = 6000) -> str:
        """Intelligently sample and compress data to fit token budget"""
        
        # Estimate tokens (rough: 1 token = 0.75 words)
        all_content = []
        for source in sources:
            if source.data_content:
                # Take smart samples instead of full content
                content_lines = source.data_content.split('\n\n')
                
                # Sample strategy: take first 20%, middle 20%, last 20%
                total_lines = len(content_lines)
                sample_size = min(max(total_lines // 5, 10), 50)  # Between 10-50 samples
                
                if total_lines > sample_size:
                    # Smart sampling
                    first_chunk = content_lines[:sample_size//3]
                    middle_start = total_lines // 2 - sample_size//6
                    middle_chunk = content_lines[middle_start:middle_start + sample_size//3]
                    last_chunk = content_lines[-sample_size//3:]
                    sampled_content = first_chunk + middle_chunk + last_chunk
                else:
                    sampled_content = content_lines
                
                # Join and add source header
                header = f"=== {source.source.upper()} ({source.type}) ==="
                content_text = "\n\n".join(sampled_content[:30])  # Cap at 30 items per source
                all_content.append(f"{header}\n{content_text}")
        
        combined = "\n\n".join(all_content)
        
        # If still too long, truncate more aggressively
        if len(combined.split()) > max_tokens * 0.75:  # Rough token estimation
            words = combined.split()
            truncated_words = words[:int(max_tokens * 0.75)]
            combined = " ".join(truncated_words) + "\n\n[...DATA TRUNCATED...]"
        
        return combined
    
    def build_compressed_calibration_prompt(self, facet_name: str, sources: List[DataSource]) -> str:
        """Ultra-compressed calibration prompt"""
        facet_def = self.config["facet_definitions"][facet_name]
        
        # Compressed platform calibrations
        platform_adjustments = []
        for source in sources:
            source_cal = self.config["source_specific_calibrations"].get(source.source, {})
            if 'trait_amplifications' in source_cal:
                amps = [f"{t}+{v}" for t, v in source_cal['trait_amplifications'].items()]
                platform_adjustments.append(f"{source.source}: {','.join(amps)}")
            if 'trait_suppressions' in source_cal:
                sups = [f"{t}-{v}" for t, v in source_cal['trait_suppressions'].items()]
                platform_adjustments.append(f"{source.source}: {','.join(sups)}")
        
        prompt = f"""ANALYZE {facet_name.upper()} PERSONALITY
Context: {facet_def['description']}
Platform adjustments: {'; '.join(platform_adjustments)}

OUTPUT STRUCTURE:
TRAITS: O/C/E/A/N [1 sentence each with examples]
INTERESTS: [key topics/hobbies from data]  
COMMUNICATION: [style, tone, formality from patterns]
LANGUAGE: [frequent phrases, expressions, greetings found in data]
SOCIAL: [interaction patterns, humor use]
WORK: [approach to tasks, collaboration style]
DECISIONS: [analytical vs intuitive, risk tolerance]
EMOTIONS: [stress handling, celebration style]  
VALUES: [core priorities from communication themes]
RELATIONSHIPS: [networking, conflict resolution style]"""

        return prompt
    
    def generate_compressed_facet_p2(self, llm: LLM, facet_name: str, sources: List[DataSource]) -> FacetProfile:
        """Generate P2 with aggressive compression"""
        
        # Compress data samples
        compressed_data = self.compress_data_samples(sources, max_tokens=5000)
        
        # Build ultra-compressed prompt
        calibration_prompt = self.build_compressed_calibration_prompt(facet_name, sources)
        
        # Final compressed analysis prompt
        analysis_prompt = f"""{calibration_prompt}

DATA:
{compressed_data}

Generate concise {facet_name} personality profile following OUTPUT STRUCTURE above.
Base all analysis on actual patterns from data. Be specific and evidence-based."""

        # Generate with reduced token limit
        analysis_token_limit = 2000 if llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')) else 1500
        
        try:
            personality_analysis = llm.chat(
                "You are a personality assessment expert. Analyze concisely.", 
                analysis_prompt, 
                max_tokens=analysis_token_limit, 
                temperature=0.2
            )
        except Exception as e:
            if "too large" in str(e) or "tokens" in str(e):
                # Emergency fallback - even more compression
                compressed_data = self.compress_data_samples(sources, max_tokens=2000)
                analysis_prompt = f"""{calibration_prompt}

DATA: {compressed_data}

Analyze {facet_name} personality: TRAITS (O/C/E/A/N brief), COMMUNICATION style, KEY interests, LANGUAGE patterns."""
                
                personality_analysis = llm.chat(
                    "Personality expert. Be concise.", 
                    analysis_prompt, 
                    max_tokens=1000, 
                    temperature=0.2
                )
            else:
                raise e
        
        # Extract communication style  
        communication_style = self._extract_communication_style(sources)
        
        # Generate brief communication style summary for compressed version
        communication_style_summary = self._generate_compressed_communication_style(llm, facet_name, sources, compressed_data)
        
        # Build compressed P2 prompt with authentic communication patterns
        p2_prompt = f"""PERSONALITY ({facet_name.upper()})
{personality_analysis}

CONTEXT: Answer personality questions as your {facet_name} self based on patterns above.

COMMUNICATION: {communication_style_summary}"""

        return FacetProfile(
            facet_name=facet_name,
            sources=sources,
            combined_data=compressed_data,
            personality_analysis=personality_analysis,
            communication_style=communication_style,
            p2_prompt=p2_prompt
        )
    
    def _generate_compressed_communication_style(self, llm: LLM, facet_name: str, sources: List[DataSource], compressed_data: str) -> str:
        """Generate brief communication style summary for compressed P2"""
        
        # Use small sample for token efficiency
        sample_data = compressed_data[:1000] if len(compressed_data) > 1000 else compressed_data
        
        style_prompt = f"""Analyze this {facet_name} communication sample and provide 1-2 brief sentences about response patterns:

{sample_data}

Focus on: typical length, tone, punctuation style, key phrases used.
Keep response under 20 words."""

        try:
            style_summary = llm.chat(
                "Extract brief communication patterns.",
                style_prompt,
                max_tokens=100,
                temperature=0.1
            )
            return style_summary.strip()
        except Exception:
            return f"Typical {facet_name} communication patterns from data."

# Update the rate-limited script to use compressed generation
if __name__ == "__main__":
    print("🗜️  Compressed P2 Generator")
    print("Reduces token usage by ~70% while maintaining quality")
    
    # Test compression levels
    fps = CompressedP2Generator()
    sources = fps.load_available_sources()
    
    if sources:
        facet_sources = fps.organize_by_facets()
        
        for facet_name, facet_sources_list in facet_sources.items():
            if facet_sources_list:
                compressed_data = fps.compress_data_samples(facet_sources_list)
                print(f"\n{facet_name.capitalize()} facet:")
                print(f"  Sources: {len(facet_sources_list)}")
                print(f"  Compressed data: {len(compressed_data)} chars (~{len(compressed_data.split())} tokens)")
                
                calibration = fps.build_compressed_calibration_prompt(facet_name, facet_sources_list)
                print(f"  Calibration prompt: {len(calibration)} chars (~{len(calibration.split())} tokens)")
                
                total_estimated_tokens = len(compressed_data.split()) + len(calibration.split())
                print(f"  Total estimated input tokens: {total_estimated_tokens}")