#!/usr/bin/env python3

"""
Smart P2 Generation with Selective Compression
Maintains full personality analysis quality while reducing input token usage
"""

from faceted_personality import FacetedPersonalitySystem, DataSource, FacetProfile
from bfi_probe import LLM
from typing import List
import re

class SmartP2Generator(FacetedPersonalitySystem):
    """Smart P2 generator that reduces input tokens but keeps full analysis quality"""
    
    def __init__(self, config_path: str = "data_sources_config.json"):
        super().__init__(config_path)
    
    def smart_sample_data(self, sources: List[DataSource], target_tokens: int = 8000) -> str:
        """Intelligently sample data to target token limit while preserving diversity"""
        
        all_sections = []
        
        for source in sources:
            if not source.data_content:
                continue
            
            # Split content into meaningful chunks (paragraphs, messages, etc.)
            if source.type == 'chat':
                # For chat data, split by messages/lines
                chunks = [line.strip() for line in source.data_content.split('\n') if line.strip()]
            elif source.type in ['articles', 'posts']:
                # For articles/posts, split by paragraphs or sentences
                chunks = [p.strip() for p in source.data_content.split('\n\n') if p.strip()]
            else:
                chunks = [line.strip() for line in source.data_content.split('\n') if line.strip()]
            
            if not chunks:
                continue
            
            # Smart sampling strategy based on content type
            total_chunks = len(chunks)
            
            if total_chunks <= 50:
                # Small dataset - keep everything
                selected_chunks = chunks
            else:
                # Large dataset - intelligent sampling
                # Take first 20% (opening patterns)
                first_count = max(10, total_chunks // 5)
                first_chunks = chunks[:first_count]
                
                # Take middle samples (diverse content)
                middle_start = total_chunks // 3
                middle_end = (total_chunks * 2) // 3
                middle_sample_size = max(10, (middle_end - middle_start) // 3)
                middle_chunks = chunks[middle_start:middle_start + middle_sample_size]
                
                # Take recent 20% (current patterns)
                last_count = max(10, total_chunks // 5)
                last_chunks = chunks[-last_count:]
                
                # Look for emotionally rich content (contains emotional words/expressions)
                emotional_patterns = r'\b(love|hate|excited|frustrated|amazing|terrible|brilliant|awful|happy|sad|angry|worried|thrilled|disappointed)\b|[!]{2,}|[?]{2,}|😀|😊|😂|😢|😠|❤️|🎉|😤|😔'
                emotional_chunks = [chunk for chunk in chunks if re.search(emotional_patterns, chunk, re.IGNORECASE)][:15]
                
                # Combine all samples
                selected_chunks = first_chunks + middle_chunks + last_chunks + emotional_chunks
                
                # Remove duplicates while preserving order
                seen = set()
                unique_chunks = []
                for chunk in selected_chunks:
                    if chunk not in seen:
                        seen.add(chunk)
                        unique_chunks.append(chunk)
                
                selected_chunks = unique_chunks
            
            # Add source header and content
            header = f"=== {source.source.upper()} ({source.type}) ==="
            content_text = "\n\n".join(selected_chunks[:60])  # Cap at 60 samples per source
            all_sections.append(f"{header}\n{content_text}")
        
        combined = "\n\n".join(all_sections)
        
        # Final token check - if still too large, truncate more aggressively
        estimated_tokens = len(combined.split()) * 1.3  # More conservative token estimation
        
        if estimated_tokens > target_tokens:
            target_words = int(target_tokens * 0.75)  # Leave room for other parts
            words = combined.split()
            if len(words) > target_words:
                truncated_words = words[:target_words]
                combined = " ".join(truncated_words) + "\n\n[...ADDITIONAL DATA TRUNCATED FOR TOKEN LIMITS...]"
        
        return combined
    
    def generate_smart_facet_p2(self, llm: LLM, facet_name: str, sources: List[DataSource]) -> FacetProfile:
        """Generate P2 with smart data sampling but full analysis quality"""
        
        # Smart sample the data
        target_input_tokens = 12000 if llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')) else 8000
        combined_data = self.smart_sample_data(sources, target_tokens=target_input_tokens)
        
        # Use the FULL calibration prompt (not compressed)
        calibration_prompt = self.build_facet_calibration_prompt(facet_name, sources)
        
        # Use the FULL analysis prompt with all detailed sections
        analysis_prompt = f"""{calibration_prompt}

DATA TO ANALYZE:
{combined_data}

Create a comprehensive {facet_name} personality profile using this detailed structure:

BIG FIVE TRAITS ({facet_name.upper()} FACET):
O: [one sentence about openness in {facet_name} contexts, with specific examples from the data]
C: [one sentence about conscientiousness in {facet_name} contexts, with specific examples from the data]
E: [one sentence about extraversion in {facet_name} contexts, with specific examples from the data] 
A: [one sentence about agreeableness in {facet_name} contexts, with specific examples from the data]
N: [one sentence about neuroticism in {facet_name} contexts, with specific examples from the data]

INTERESTS & PREFERENCES:
[2-3 sentences about what this person is interested in, hobbies, topics they enjoy discussing, professional areas of focus, based on actual content and themes from the data]

COMMUNICATION STYLE:
[2-3 sentences about how they communicate - formality level, directness vs diplomacy, tone, responsiveness, conversation initiation style, based on patterns across different sources]

LANGUAGE PATTERNS & EXPRESSIONS:
[List specific phrases, words, or expressions this person commonly uses. Include: how they express laughter (haha, lol, 😂), greeting responses ("hey!", "thanks", "good to see you"), frequently used verbs, descriptive words, signature expressions, transition phrases, and conversational fillers found in the actual data]

SOCIAL INTERACTIONS:
[2-3 sentences about how they respond to others, initiate conversations, use humor, emojis, maintain relationships, handle social situations, based on actual interpersonal interactions in the data]

WORK & PRODUCTIVITY PATTERNS:
[2-3 sentences about their approach to work, deadlines, collaboration, problem-solving style, goal orientation, project management approach, based on professional communication patterns]

DECISION-MAKING STYLE:
[2-3 sentences about how they approach decisions - analytical vs intuitive, data-driven vs experience-based, collaborative vs independent, risk tolerance, speed of decision-making, based on examples from the data]

EMOTIONAL EXPRESSION PATTERNS:
[2-3 sentences about how they express emotions, handle stress, share vulnerabilities, celebrate successes, deal with frustration, show empathy, based on emotional content and tone variations in the data]

VALUES & MOTIVATIONS:
[2-3 sentences about what matters most to them, what drives them, their principles and beliefs, life/career priorities, causes they care about, based on recurring themes and passionate language in their communication]

RELATIONSHIP DYNAMICS:
[2-3 sentences about how they build and maintain relationships, networking style, mentoring approach, conflict resolution, support-giving style, based on interpersonal interactions in the data]

LEARNING & ADAPTATION STYLE:
[2-3 sentences about how they approach new information, adapt to change, seek feedback, share knowledge, handle mistakes, embrace challenges, based on intellectual content and growth-related communication in the data]

TIME & ENERGY MANAGEMENT:
[2-3 sentences about their relationship with time, urgency, scheduling, energy patterns, multitasking tendencies, based on temporal patterns and productivity-related communication in the data]

CROSS-SOURCE CONSISTENCY:
[Note similarities and differences across the different communication types/platforms for this facet, highlighting authentic vs performative elements]

FACET-SPECIFIC INSIGHTS:
[Unique observations about how personality manifests in {facet_name} contexts vs other contexts, including situational adaptability and context-dependent traits]

Apply all platform-specific calibrations as specified above when analyzing these patterns."""

        # Generate with appropriate token limits
        analysis_token_limit = 6000 if llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')) else 4000
        
        try:
            personality_analysis = llm.chat(
                "You are a personality assessment expert specializing in faceted personality analysis.", 
                analysis_prompt, 
                max_tokens=analysis_token_limit, 
                temperature=0.2
            )
        except Exception as e:
            if "too large" in str(e).lower() or "tokens" in str(e).lower():
                # Fall back to more aggressive data sampling
                print(f"⚠️  Token limit hit, trying more aggressive sampling...")
                combined_data = self.smart_sample_data(sources, target_tokens=6000)
                analysis_prompt = f"""{calibration_prompt}

DATA TO ANALYZE:
{combined_data}

Create a comprehensive {facet_name} personality profile with all sections above."""
                
                personality_analysis = llm.chat(
                    "You are a personality assessment expert specializing in faceted personality analysis.", 
                    analysis_prompt, 
                    max_tokens=analysis_token_limit, 
                    temperature=0.2
                )
            else:
                raise e
        
        # Extract communication style
        communication_style = self._extract_communication_style(sources)
        
        # Generate dynamic communication style analysis
        communication_style_analysis = self._generate_communication_style_analysis(llm, facet_name, sources, combined_data)
        
        # Build comprehensive P2 prompt with authentic communication patterns
        p2_prompt = f"""PERSONALITY PROFILE ({facet_name.upper()} FACET)

{personality_analysis}

ASSESSMENT CONTEXT:
You are answering personality questions from the perspective of your {facet_name} personality facet.
Consider how you behave, think, and feel specifically in {facet_name} contexts.
Base your responses on the patterns identified above.

COMMUNICATION STYLE ANALYSIS:
{communication_style_analysis}"""

        return FacetProfile(
            facet_name=facet_name,
            sources=sources,
            combined_data=combined_data,
            personality_analysis=personality_analysis,
            communication_style=communication_style,
            p2_prompt=p2_prompt
        )

# Update the main section
if __name__ == "__main__":
    print("🧠 Smart P2 Generator")
    print("Balances token efficiency with personality analysis quality")
    
    # Test smart sampling
    fps = SmartP2Generator()
    sources = fps.load_available_sources()
    
    if sources:
        facet_sources = fps.organize_by_facets()
        
        for facet_name, facet_sources_list in facet_sources.items():
            if facet_sources_list:
                sampled_data = fps.smart_sample_data(facet_sources_list)
                print(f"\n{facet_name.capitalize()} facet:")
                print(f"  Sources: {len(facet_sources_list)}")
                print(f"  Smart sampled data: {len(sampled_data)} chars (~{len(sampled_data.split())} tokens)")
                
                # Show sampling efficiency
                original_size = sum(len(s.data_content or '') for s in facet_sources_list)
                compression_ratio = (1 - len(sampled_data) / max(original_size, 1)) * 100
                print(f"  Compression ratio: {compression_ratio:.1f}%")