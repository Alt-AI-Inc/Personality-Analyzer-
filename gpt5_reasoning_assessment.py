#!/usr/bin/env python3

"""
Enhanced personality assessment leveraging GPT-5's reasoning capabilities.

Instead of just answering BFI questions, we use multi-step reasoning to:
1. Analyze writing patterns systematically
2. Consider contradictory evidence
3. Provide confidence estimates
4. Account for context effects
"""

import json
import re
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Import existing components
from bfi_probe import LLM, LLMConfig, BFI_S_ITEMS, LIKERT

@dataclass
class ReasoningResult:
    trait: str
    score: float
    confidence: float
    reasoning: str
    evidence: List[str]
    contradictions: List[str]

def reasoning_based_trait_analysis(llm: LLM, trait_name: str, trait_description: str, 
                                 writing_samples: str) -> ReasoningResult:
    """
    Use GPT-5's reasoning to analyze a single personality trait in depth.
    """
    
    reasoning_prompt = f"""You are a personality psychologist analyzing writing samples for the Big Five trait: {trait_name}

{trait_description}

Please analyze these writing samples step-by-step:

STEP 1: EVIDENCE IDENTIFICATION
Identify specific examples from the writing that suggest high, moderate, or low {trait_name}. Quote specific phrases or sentences.

STEP 2: PATTERN ANALYSIS  
Look for consistent patterns across multiple samples. Are there recurring themes or behaviors?

STEP 3: CONTRADICTORY EVIDENCE
Identify any evidence that contradicts your initial assessment. Are there examples that suggest the opposite?

STEP 4: CONTEXT CONSIDERATION
Consider how the medium (social media/messages) might influence the expression of this trait. Might the real trait be different from what's expressed?

STEP 5: CONFIDENCE ASSESSMENT
Based on the quantity and quality of evidence, how confident are you in your assessment?

STEP 6: FINAL SCORING
On a scale of 1.0-5.0, where would you place this person on {trait_name}?
1.0 = Very Low, 2.0 = Low, 3.0 = Moderate, 4.0 = High, 5.0 = Very High

WRITING SAMPLES:
{writing_samples}

Please provide your analysis following the step structure above, ending with:
FINAL SCORE: X.X/5.0
CONFIDENCE: X.X/5.0
"""

    response = llm.chat("You are an expert personality psychologist.", reasoning_prompt, 
                       max_tokens=1000, temperature=0.1)
    
    # Parse the response
    score_match = re.search(r'FINAL SCORE:\s*(\d+\.?\d*)', response, re.IGNORECASE)
    confidence_match = re.search(r'CONFIDENCE:\s*(\d+\.?\d*)', response, re.IGNORECASE)
    
    score = float(score_match.group(1)) if score_match else 3.0
    confidence = float(confidence_match.group(1)) if confidence_match else 2.5
    
    # Extract evidence and contradictions (simplified parsing)
    evidence = []
    contradictions = []
    
    # Look for quoted text as evidence
    quotes = re.findall(r'"([^"]*)"', response)
    evidence.extend(quotes[:5])  # Top 5 pieces of evidence
    
    return ReasoningResult(
        trait=trait_name,
        score=max(1.0, min(5.0, score)),
        confidence=max(1.0, min(5.0, confidence)),
        reasoning=response,
        evidence=evidence,
        contradictions=contradictions
    )

def comprehensive_personality_analysis(llm: LLM, writing_samples: str) -> Dict[str, ReasoningResult]:
    """
    Perform comprehensive reasoning-based analysis for all Big Five traits.
    """
    
    trait_descriptions = {
        "Openness": """
        Openness to Experience reflects creativity, curiosity, and willingness to try new things.
        HIGH: Creative, imaginative, curious, appreciates art/beauty, enjoys variety, abstract thinking
        LOW: Practical, conventional, prefers routine, focused on concrete rather than abstract
        """,
        
        "Conscientiousness": """
        Conscientiousness reflects organization, discipline, and goal-oriented behavior.
        HIGH: Organized, disciplined, reliable, plans ahead, completes tasks, detail-oriented
        LOW: Flexible, spontaneous, casual about schedules, may procrastinate, adaptable
        """,
        
        "Extraversion": """
        Extraversion reflects energy, sociability, and assertiveness.
        HIGH: Outgoing, talkative, energetic, seeks social interaction, assertive, enthusiastic
        LOW: Reserved, quiet, prefers solitude, listens more than talks, less assertive
        """,
        
        "Agreeableness": """
        Agreeableness reflects cooperation, trust, and empathy.
        HIGH: Cooperative, trusting, helpful, empathetic, avoids conflict, considerate
        LOW: Competitive, skeptical, direct, willing to argue, self-focused, critical
        """,
        
        "Neuroticism": """
        Neuroticism reflects emotional stability and stress response.
        HIGH: Anxious, moody, stressed, worries frequently, emotionally reactive, sensitive
        LOW: Calm, stable, resilient, handles stress well, even-tempered, secure
        """
    }
    
    results = {}
    
    print("🧠 Running GPT-5 reasoning-based personality analysis...")
    
    for trait, description in trait_descriptions.items():
        print(f"   Analyzing {trait}...")
        
        result = reasoning_based_trait_analysis(llm, trait, description, writing_samples)
        results[trait] = result
        
        print(f"      Score: {result.score:.2f}, Confidence: {result.confidence:.2f}")
        
        # Small delay to respect rate limits
        time.sleep(1)
    
    return results

def comparative_bfi_assessment(llm: LLM, writing_samples: str, reasoning_results: Dict[str, ReasoningResult]) -> Dict[str, float]:
    """
    Use reasoning insights to improve traditional BFI assessment.
    """
    
    print("🔄 Running enhanced BFI assessment with reasoning context...")
    
    # Create enhanced context from reasoning
    context_summary = "PERSONALITY ANALYSIS CONTEXT:\n"
    for trait, result in reasoning_results.items():
        context_summary += f"\n{trait}: {result.score:.1f}/5.0 (confidence: {result.confidence:.1f}/5.0)"
        if result.evidence:
            context_summary += f"\n  Key evidence: {result.evidence[0][:100]}..."
    
    enhanced_system = f"""You are completing a Big Five personality inventory based on writing samples.

{context_summary}

INSTRUCTIONS:
- Consider the detailed analysis above when answering each question
- Focus on consistent patterns across the writing samples
- Account for social media context effects
- Be more confident in traits with higher analysis confidence
- Rate how accurately each statement describes the author

Output only A/B/C/D/E where:
A=Very Accurate, B=Accurate, C=Neither, D=Inaccurate, E=Very Inaccurate

WRITING SAMPLES:
{writing_samples}
"""

    # Run traditional BFI with enhanced context
    answers = {}
    for item in BFI_S_ITEMS:
        prompt = f"Rate how accurately this statement describes the author:\n\n{item['text']}\n\nResponse:"
        
        resp = llm.chat(enhanced_system, prompt, max_tokens=8, temperature=0.0)
        m = re.search(r"[A-E]", resp, re.I)
        answers[item["id"]] = (m.group(0).upper() if m else "C")
        time.sleep(0.1)
    
    # Score the results
    by_trait = {"O":[],"C":[],"E":[],"A":[],"N":[]}
    for item in BFI_S_ITEMS:
        raw = LIKERT.get(answers.get(item["id"],"C"), 3)
        val = (6 - raw) if item["reverse"] else raw
        by_trait[item["trait"]].append(val)
    
    means = {t: float(sum(v)/len(v)) for t, v in by_trait.items()}
    return means

def main():
    """Run comprehensive GPT-5 personality assessment."""
    
    # Load writing samples
    try:
        with open('data/personality_tweets_condensed.json', 'r') as f:
            tweets = json.load(f)
        
        writing_samples = '\n\n'.join([tweet['full_text'] for tweet in tweets])
        
    except FileNotFoundError:
        print("❌ Could not find data/personality_tweets_condensed.json")
        return
    
    print("🚀 GPT-5 Enhanced Personality Assessment")
    print("=" * 60)
    print(f"📝 Analyzing {len(tweets)} writing samples")
    
    # Initialize GPT-5
    cfg = LLMConfig(model="gpt-5", temperature=0.1, max_tokens=1000)
    llm = LLM(cfg, debug=False)
    
    # Step 1: Reasoning-based analysis
    reasoning_results = comprehensive_personality_analysis(llm, writing_samples)
    
    # Step 2: Enhanced BFI assessment
    bfi_scores = comparative_bfi_assessment(llm, writing_samples, reasoning_results)
    
    # Step 3: Compare and synthesize results
    print(f"\n📊 Results Comparison:")
    print("Trait | Reasoning | BFI Enhanced | Confidence")
    print("------|-----------|--------------|------------")
    
    trait_map = {"O": "Openness", "C": "Conscientiousness", "E": "Extraversion", 
                 "A": "Agreeableness", "N": "Neuroticism"}
    
    final_results = {}
    
    for trait_code, trait_name in trait_map.items():
        reasoning_score = reasoning_results[trait_name].score
        bfi_score = bfi_scores[trait_code]
        confidence = reasoning_results[trait_name].confidence
        
        # Weighted average based on confidence
        weight = confidence / 5.0
        final_score = (reasoning_score * weight) + (bfi_score * (1 - weight))
        
        final_results[trait_code] = final_score
        
        print(f"  {trait_code}   |    {reasoning_score:.2f}    |     {bfi_score:.2f}     |    {confidence:.2f}")
    
    print(f"\n✨ Final GPT-5 Enhanced Scores:")
    for trait_code, score in final_results.items():
        trait_name = trait_map[trait_code]
        print(f"   {trait_name}: {score:.2f}/5.0")
    
    # Save detailed results
    output = {
        'model': 'gpt-5',
        'method': 'reasoning_enhanced',
        'reasoning_analysis': {trait: {
            'score': result.score,
            'confidence': result.confidence,
            'evidence': result.evidence[:3],  # Top 3 pieces of evidence
            'reasoning_summary': result.reasoning[:500] + "..." if len(result.reasoning) > 500 else result.reasoning
        } for trait, result in reasoning_results.items()},
        'bfi_scores': bfi_scores,
        'final_scores': final_results,
        'sample_size': len(tweets)
    }
    
    with open('results/gpt5_enhanced_assessment.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: results/gpt5_enhanced_assessment.json")
    
    return final_results

if __name__ == "__main__":
    main()