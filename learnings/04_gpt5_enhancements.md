# GPT-5 Enhancements and API Differences

## GPT-5 API Parameter Changes Discovered

### Parameter Differences
```python
# GPT-4 and earlier
openai.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=128,
    temperature=0.0,  # Supports custom temperature
    # ... other params
)

# GPT-5 
openai.chat.completions.create(
    model="gpt-5", 
    max_completion_tokens=128,  # Changed parameter name
    # temperature=1.0 is default and only supported value
    # ... other params  
)
```

### Implementation Solution
```python
def chat(self, system, user, *, max_tokens=None, temperature=None):
    if self.cfg.model.startswith('gpt-5'):
        # GPT-5: Use max_completion_tokens, omit temperature
        r = self.cli.chat.completions.create(
            model=self.cfg.model,
            messages=[...],
            max_completion_tokens=max_tokens
        )
    else:
        # GPT-4 and earlier: Use max_tokens, include temperature 
        r = self.cli.chat.completions.create(
            model=self.cfg.model,
            messages=[...],
            max_tokens=max_tokens,
            temperature=temperature
        )
```

## GPT-5 Reasoning-Enhanced Assessment Design

### Multi-Step Analysis Framework
```python
def reasoning_based_trait_analysis(llm, trait_name, trait_description, writing_samples):
    reasoning_prompt = f"""
    STEP 1: EVIDENCE IDENTIFICATION
    Identify specific examples suggesting high/moderate/low {trait_name}
    
    STEP 2: PATTERN ANALYSIS  
    Look for consistent patterns across multiple samples
    
    STEP 3: CONTRADICTORY EVIDENCE
    Identify evidence that contradicts initial assessment
    
    STEP 4: CONTEXT CONSIDERATION
    Consider how social media might influence trait expression
    
    STEP 5: CONFIDENCE ASSESSMENT
    Assess confidence based on evidence quality
    
    STEP 6: FINAL SCORING
    Score 1.0-5.0 with justification
    """
```

### Enhanced Context Integration
```python
def comparative_bfi_assessment(llm, writing_samples, reasoning_results):
    # Use reasoning insights to inform traditional BFI assessment
    context_summary = "PERSONALITY ANALYSIS CONTEXT:\n"
    for trait, result in reasoning_results.items():
        context_summary += f"{trait}: {result.score}/5.0 (confidence: {result.confidence}/5.0)"
        context_summary += f"Key evidence: {result.evidence[0][:100]}..."
    
    enhanced_system = f"""
    {context_summary}
    
    Consider the detailed analysis above when answering BFI questions.
    Focus on consistent patterns, account for social media context.
    """
```

### Dual-Method Scoring
```python
# Combine reasoning and BFI results with confidence weighting
def synthesize_results(reasoning_results, bfi_scores):
    final_scores = {}
    for trait_code, trait_name in trait_mapping.items():
        reasoning_score = reasoning_results[trait_name].score
        bfi_score = bfi_scores[trait_code]  
        confidence = reasoning_results[trait_name].confidence
        
        # Weight by confidence: higher confidence = more reasoning weight
        weight = confidence / 5.0
        final_score = (reasoning_score * weight) + (bfi_score * (1 - weight))
        final_scores[trait_code] = final_score
    
    return final_scores
```

## Expected GPT-5 Improvements

### 1. Contextual Sophistication
**Before (GPT-4)**:
```
"I love parties but need quiet time after" → Simple pattern matching → High Extraversion
```

**After (GPT-5)**:
```  
"I love parties but need quiet time after" → Complex reasoning:
- Shows social engagement (extraversion +)
- Shows need for solitude (extraversion -)  
- Indicates energy management awareness (conscientiousness +)
- Suggests self-awareness (openness +)
→ Moderate Extraversion with high confidence
```

### 2. Contradiction Handling
**GPT-5 Reasoning Process**:
```python
evidence = ["I'm excited about the team meeting", "I prefer working alone"]
contradictions = ["Shows both social engagement and preference for solitude"]  
reasoning = """
The subject shows mixed extraversion signals. Professional excitement about
team meetings suggests functional extraversion in work contexts, while 
preference for independent work suggests introversion in task execution.
This pattern suggests moderate extraversion with context-dependent expression.
"""
confidence = 3.8  # High confidence despite contradictory evidence
```

### 3. Temperature=1.0 Benefits for Personality
**Higher Creativity Advantages**:
- More nuanced interpretation of ambiguous statements
- Better handling of sarcasm, humor, implicit cues
- Less rigid pattern matching, more holistic analysis
- Enhanced ability to see personality complexity

**Variance Management**:
```python  
# Multiple run strategy becomes essential
results = []
for run in range(3):
    score = gpt5_assessment(samples)  # Each run may vary
    results.append(score)

final_assessment = {
    'mean': calculate_mean(results),
    'confidence_interval': calculate_95_ci(results),
    'consistency': 'high' if std(results) < 0.3 else 'medium'
}
```

## Integration Strategy

### Phase 1: Direct Comparison
```bash
# Test GPT-5 with existing method
python3 bfi_probe.py --model gpt-5 --samples data/personality_tweets_condensed.json --calibrated
```

### Phase 2: Reasoning Enhancement  
```bash
# Leverage GPT-5's reasoning capabilities
python3 gpt5_reasoning_assessment.py
```

### Phase 3: Cross-Validation
```bash
# Test across different sample sets
python3 compare_models.py  # GPT-4 vs GPT-5 comparison
```

## Key Architectural Changes

### Enhanced BFI Probe Integration
```python
# Added GPT-5 support to existing bfi_probe.py
def administer(llm, items, persona=None, as_if=None, use_calibrated_prompt=False):
    if use_calibrated_prompt and as_if:
        system = """You are completing Big Five inventory based on writing samples.
        
        IMPORTANT CONTEXT:
        - These are social media posts, not formal self-assessments
        - Focus on consistent patterns across samples
        - Consider social media may amplify/minimize certain traits
        
        CALIBRATION NOTES:  
        - Social media writing tends to show higher extraversion
        - Emotional posts may overrepresent neuroticism
        - Creative posts may overrepresent openness
        """
```

### Confidence-Weighted Results
```python
class ReasoningResult:
    trait: str
    score: float  
    confidence: float  # NEW: Explicit confidence assessment
    reasoning: str     # NEW: Detailed reasoning chain
    evidence: List[str]  # NEW: Supporting evidence quotes
    contradictions: List[str]  # NEW: Contradictory evidence
```

## Performance Implications

### Processing Time Impact
- **GPT-5 Reasoning**: ~2-3x longer than traditional BFI (5-6 minutes total)
- **Multiple runs**: 3x processing time but better reliability
- **Trade-off**: Time vs. accuracy and confidence

### Token Usage
- **Reasoning prompts**: 800-1000 tokens per trait analysis  
- **Enhanced context**: Additional 200-300 tokens per BFI question
- **Total increase**: ~5x token usage vs. basic BFI probe

### API Cost Considerations
```python
# Cost optimization strategy
def cost_optimized_assessment():
    # Use reasoning for complex cases, standard BFI for clear cases
    if sample_has_contradictions(writing_samples):
        return reasoning_enhanced_assessment()
    else:
        return standard_calibrated_assessment()
```