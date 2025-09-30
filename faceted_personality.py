#!/usr/bin/env python3

"""
Faceted Personality Assessment System
Supports Professional vs Personal personality facets with source-specific calibration
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from bfi_probe import LLM, load_sample_data

@dataclass
class DataSource:
    name: str
    source: str  # whatsapp, twitter, linkedin, etc.
    type: str    # chat, posts, articles, correspondence
    path: str
    category: str  # professional, personal
    description: str
    communication_traits: Dict
    data_content: Optional[str] = None

@dataclass 
class FacetProfile:
    facet_name: str  # "professional" or "personal"
    sources: List[DataSource]
    combined_data: str
    personality_analysis: str
    communication_style: Dict
    p2_prompt: str

class FacetedPersonalitySystem:
    """Multi-facet personality assessment system"""
    
    def __init__(self, config_path: str = "data_sources_config.json"):
        self.config = self._load_config(config_path)
        self.sources: List[DataSource] = []
        self.facets: Dict[str, FacetProfile] = {}
        
    def _load_config(self, config_path: str) -> Dict:
        """Load data sources configuration"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def load_available_sources(self) -> List[DataSource]:
        """Load all available data sources from config"""
        available_sources = []
        
        for source_config in self.config["data_sources"]:
            if os.path.exists(source_config["path"]):
                # Load the actual data content
                data_content = load_sample_data(source_config["path"])
                
                source = DataSource(
                    name=source_config["name"],
                    source=source_config["source"], 
                    type=source_config["type"],
                    path=source_config["path"],
                    category=source_config["category"],
                    description=source_config["description"],
                    communication_traits=source_config["communication_traits"],
                    data_content=data_content
                )
                available_sources.append(source)
                print(f"✅ Loaded {source.name}: {len(data_content) if data_content else 0} characters")
            else:
                print(f"⚠️  Skipped {source_config['name']}: File not found at {source_config['path']}")
        
        self.sources = available_sources
        return available_sources
    
    def organize_by_facets(self) -> Dict[str, List[DataSource]]:
        """Organize loaded sources by professional vs personal facets"""
        facet_sources = {"professional": [], "personal": []}
        
        for source in self.sources:
            if source.category in facet_sources:
                facet_sources[source.category].append(source)
        
        print(f"\n📊 Facet Organization:")
        for facet, sources in facet_sources.items():
            print(f"  {facet.capitalize()}: {len(sources)} sources")
            for source in sources:
                print(f"    - {source.name} ({source.source}/{source.type})")
                
        return facet_sources
    
    def build_facet_calibration_prompt(self, facet_name: str, sources: List[DataSource]) -> str:
        """Build platform and type-specific calibration prompt for a facet"""
        facet_def = self.config["facet_definitions"][facet_name]
        
        prompt = f"""Analyze the following {facet_name} communication samples and create a personality profile.

FACET CONTEXT: {facet_def['description']}
KEY TRAITS TO ASSESS: {', '.join(facet_def['key_traits'])}
CONTEXT CONSIDERATIONS: {', '.join(facet_def['context_considerations'])}

MULTI-SOURCE CALIBRATION INSTRUCTIONS:"""
        
        for source in sources:
            source_cal = self.config["source_specific_calibrations"].get(source.source, {})
            type_cal = self.config["communication_type_calibrations"].get(source.type, {})
            
            prompt += f"""

=== {source.name.upper()} CALIBRATION ===
Source: {source.source} | Type: {source.type} | Traits: {source.communication_traits['formality']} formality, {source.communication_traits['authenticity']} authenticity
Platform Bias: {source_cal.get('platform_bias', 'neutral')}
Communication Style: {type_cal.get('characteristics', 'standard')}"""
            
            # Add trait-specific adjustments
            if 'trait_amplifications' in source_cal:
                amplifications = [f"{trait}: +{value}" for trait, value in source_cal['trait_amplifications'].items()]
                prompt += f"\nExpected Amplifications: {', '.join(amplifications)}"
                
            if 'trait_suppressions' in source_cal:
                suppressions = [f"{trait}: -{value}" for trait, value in source_cal['trait_suppressions'].items()]
                prompt += f"\nExpected Suppressions: {', '.join(suppressions)}"
                
            prompt += f"\nCommunication Markers: {', '.join(source_cal.get('communication_markers', []))}"
        
        return prompt
        
    def generate_facet_p2(self, llm: LLM, facet_name: str, sources: List[DataSource]) -> FacetProfile:
        """Generate comprehensive P2 personality profile for a specific facet"""
        
        # Combine all data for this facet
        combined_sections = []
        for source in sources:
            if source.data_content:
                section_header = f"=== {source.name.upper()} ({source.source}/{source.type}) ==="
                combined_sections.append(f"{section_header}\n{source.data_content}")
        
        combined_data = "\n\n".join(combined_sections)
        
        # Build calibration prompt
        calibration_prompt = self.build_facet_calibration_prompt(facet_name, sources)
        
        # Add the comprehensive personality profile structure with enhanced parameters
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
[List specific phrases and expressions this person commonly uses. Include: how they express laughter (haha, lol, 😂), greeting responses ("hey!", "thanks", "good to see you"), frequently used expressions, signature phrases, transition patterns, and conversational fillers found in the actual data]

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

        # Generate the personality analysis
        analysis_token_limit = 5000 if llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')) else 3000
        personality_analysis = llm.chat(
            "You are a personality assessment expert specializing in faceted personality analysis.", 
            analysis_prompt, 
            max_tokens=analysis_token_limit, 
            temperature=0.2
        )
        
        # Extract communication style information
        communication_style = self._extract_communication_style(sources)
        
        # Generate dynamic communication style analysis
        communication_style_analysis = self._generate_communication_style_analysis(llm, facet_name, sources, combined_data)
        
        # Build the final P2 prompt for BFI assessment with authentic communication patterns
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
    
    def _extract_communication_style(self, sources: List[DataSource]) -> Dict:
        """Extract aggregated communication style from sources"""
        styles = {
            "formality_levels": [s.communication_traits["formality"] for s in sources],
            "authenticity_levels": [s.communication_traits["authenticity"] for s in sources], 
            "platforms": [s.source for s in sources],
            "types": [s.type for s in sources]
        }
        return styles
    
    def _generate_communication_style_analysis(self, llm: LLM, facet_name: str, sources: List[DataSource], combined_data: str) -> str:
        """Generate dynamic communication style analysis from actual data patterns"""
        
        # Sample data for analysis (use first 3000 characters to avoid token limits)
        sample_data = combined_data[:3000] if len(combined_data) > 3000 else combined_data
        
        style_prompt = f"""Analyze the communication patterns in this {facet_name} data and extract specific messaging/response style guidelines.

DATA SAMPLE:
{sample_data}

Based on this actual communication data, provide specific response guidelines for:

VERBOSITY PATTERNS:
- Typical message/response length patterns
- When this person uses brief vs detailed responses  
- Sentence structure patterns (single sentence, fragments, etc.)

LANGUAGE STYLE:
- Common phrases and expressions this person uses
- Punctuation patterns (periods, question marks, exclamations, fragments)
- Casual markers and conversation fillers they use
- How they start and end messages

CONVERSATION FLOW:
- How they respond to questions (direct vs tangential)
- How they transition between topics  
- How they acknowledge others before responding
- Their pattern of asking follow-up questions

CONTEXT PATTERNS:
- How their style differs by topic/urgency
- Formal vs informal context adaptations

Output as specific, actionable response guidelines based on the actual patterns you observe in the data above."""

        try:
            style_analysis = llm.chat(
                "You are a communication style analyst. Extract authentic patterns from actual data.",
                style_prompt,
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent analysis
            )
            return style_analysis
        except Exception as e:
            # Fallback to basic style info if analysis fails
            return f"Communication style based on {facet_name} context with {len(sources)} data sources."
        
    def generate_all_facets(self, llm: LLM) -> Dict[str, FacetProfile]:
        """Generate P2 profiles for all available facets"""
        facet_sources = self.organize_by_facets()
        
        for facet_name, sources in facet_sources.items():
            if sources:  # Only process facets with data
                print(f"\n🔄 Generating {facet_name} facet P2 profile...")
                self.facets[facet_name] = self.generate_facet_p2(llm, facet_name, sources)
                print(f"✅ {facet_name.capitalize()} facet profile complete")
            else:
                print(f"⚠️  Skipping {facet_name} facet - no data sources available")
                
        return self.facets
    
    def get_facet_p2(self, facet_name: str) -> Optional[str]:
        """Get P2 prompt for specific facet"""
        facet = self.facets.get(facet_name)
        return facet.p2_prompt if facet else None
    
    def compare_facets(self) -> Dict:
        """Compare personality traits across different facets"""
        if len(self.facets) < 2:
            return {"error": "Need at least 2 facets to compare"}
            
        comparison = {
            "facets": list(self.facets.keys()),
            "differences": {},
            "similarities": {},
            "context_specific_traits": {}
        }
        
        return comparison
    
    def save_facet_profiles(self, output_dir: str = "results") -> Dict[str, str]:
        """Save all facet profiles to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = {}
        for facet_name, facet in self.facets.items():
            filename = f"{facet_name}_facet_p2.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {facet_name.upper()} FACET P2 PROFILE\n\n")
                f.write(f"Sources: {', '.join([s.name for s in facet.sources])}\n\n")
                f.write(facet.p2_prompt)
                
            saved_files[facet_name] = filepath
            print(f"💾 Saved {facet_name} facet profile: {filepath}")
            
        return saved_files

# Example usage and testing
if __name__ == "__main__":
    print("🧬 Faceted Personality Assessment System")
    print("=" * 50)
    
    # Initialize system
    fps = FacetedPersonalitySystem()
    
    # Load available data sources
    available_sources = fps.load_available_sources()
    print(f"\n📊 Found {len(available_sources)} available data sources")
    
    # Organize by facets
    facet_sources = fps.organize_by_facets()
    
    if not any(sources for sources in facet_sources.values()):
        print("\n❌ No data sources found. Please add data files according to the config.")
    else:
        print(f"\n✅ Ready to generate faceted personality profiles!")
        print("   Use fps.generate_all_facets(llm) to create P2 profiles for each facet.")