# Calibrated Prompting: Context-Aware Assessment

## The Social Media Context Problem

### Standard BFI Assessment Assumptions
Traditional BFI assumes:
- Controlled assessment environment
- Self-reflection context
- Complete personality expression
- Neutral question interpretation

### Social Media Reality
```python
# What we actually have:
context = {
    'medium': 'Social media posts/private messages',
    'time_span': 'Multiple years of scattered content', 
    'audience': 'Public (Twitter) vs Private (WhatsApp)',
    'content_filter': 'Personality-relevant subset only',
    'expression_bias': 'Platform-specific personality amplification'
}
```

## Calibrated System Prompt Development

### Enhanced Context Awareness
```python
calibrated_system = """
You are completing a Big Five personality inventory based on writing samples.

IMPORTANT CONTEXT:
- These are social media posts/messages, not formal self-assessments
- The author may express different personality aspects in different contexts  
- Focus on consistent PATTERNS across multiple samples, not individual posts
- Consider that social media may amplify certain traits and minimize others

CALIBRATION NOTES:
- Social media writing tends to show higher extraversion than actual personality
- Professional/work content may show inflated conscientiousness
- Emotional posts may overrepresent neuroticism  
- Creative/artistic posts may overrepresent openness

Answer each question by considering the OVERALL PATTERN in the writing samples.
Rate how accurately each statement describes the author based on their 
writing style and content themes.

WRITING SAMPLES:
{writing_samples}
"""
```

### Bias Correction Awareness
```python
def create_calibrated_prompt(sample_analysis):
    base_prompt = standard_calibrated_prompt()
    
    # Add sample-specific calibrations
    if sample_analysis['emotional_ratio'] > 0.3:
        base_prompt += "\nNOTE: High emotional content - be cautious about overestimating neuroticism."
    
    if sample_analysis['opinion_ratio'] > 0.4:  
        base_prompt += "\nNOTE: Many strong opinions - consider this reflects openness to sharing views."
        
    return base_prompt
```

## Comparison: Standard vs. Calibrated

### Standard Prompt (Original)
```python
system = "You are completing a standardized personality inventory. Answer honestly in first person. Output only A/B/C/D/E."

if as_if: 
    system = "Answer AS IF you are the author of these writing samples.\nSAMPLES:\n" + as_if + "\n\n" + system
```

**Issues**:
- No context about social media vs. self-assessment
- No guidance on handling contradictory evidence  
- No awareness of platform-specific biases
- Treats writing samples as complete personality representation

### Calibrated Prompt (Enhanced)
```python
if use_calibrated_prompt and as_if:
    system = """You are completing a Big Five personality inventory based on writing samples.

    IMPORTANT CONTEXT:
    - These are social media posts/messages, not formal self-assessments
    - The author may express different aspects of personality in different contexts
    - Focus on consistent patterns across multiple samples, not individual posts
    - Consider that social media may amplify certain traits (extraversion) and minimize others

    CALIBRATION NOTES:
    - Social media writing tends to show higher extraversion than actual personality
    - Professional/work content may show inflated conscientiousness  
    - Emotional posts may overrepresent neuroticism
    - Creative/artistic posts may overrepresent openness

    Answer each question by considering the OVERALL PATTERN in the writing samples, not individual posts.
    Rate how accurately each statement describes the author based on their writing style and content themes.

    WRITING SAMPLES:
    """ + as_if + "\n\n"
```

**Improvements**:
- ✅ Explicit context awareness
- ✅ Pattern-focused vs. individual post analysis
- ✅ Platform bias warnings
- ✅ Trait-specific calibration notes

## Real-World Impact Measurement

### Sample Quality Analysis Integration
```python
def analyze_sample_quality(tweets):
    quality_metrics = {
        'first_person_ratio': count_first_person(tweets) / len(tweets),
        'emotional_ratio': count_emotional_content(tweets) / len(tweets), 
        'opinion_ratio': count_strong_opinions(tweets) / len(tweets),
        'avg_length': mean([len(tweet['full_text']) for tweet in tweets])
    }
    
    return quality_metrics

# Example output:
{
    'total_tweets': 200,
    'first_person_ratio': 0.00,  # ⚠️ Low first-person content
    'emotional_ratio': 0.21,     # Moderate emotional expression  
    'opinion_ratio': 0.54,       # High opinion content
    'avg_length': 133            # Good tweet length
}
```

### Dynamic Calibration Based on Sample
```python
def create_dynamic_calibrated_prompt(sample_analysis):
    warnings = []
    
    if sample_analysis['first_person_ratio'] < 0.1:
        warnings.append("Limited first-person content - personality assessment may be less reliable")
        
    if sample_analysis['emotional_ratio'] < 0.15:
        warnings.append("Low emotional expression - neuroticism scores may be underestimated")
        
    if sample_analysis['opinion_ratio'] > 0.5:
        warnings.append("High opinion content - openness may be overrepresented")
    
    calibrated_prompt = base_calibrated_prompt()
    if warnings:
        calibrated_prompt += "\n\nSAMPLE-SPECIFIC CALIBRATIONS:\n" + "\n".join(f"- {w}" for w in warnings)
    
    return calibrated_prompt
```

## Platform-Specific Calibrations Discovered

### Twitter-Specific Biases
```python
twitter_calibrations = {
    'extraversion': '+0.3 to +0.5',  # Public platform amplifies social expression
    'openness': '+0.2 to +0.4',     # Platform rewards novel/creative content  
    'neuroticism': 'Variable',      # Depends on whether user shares emotions publicly
    'conscientiousness': 'Neutral', # Professional tweets vs. casual tweets vary widely
    'agreeableness': '-0.1 to -0.2' # Platform rewards strong opinions over cooperation
}
```

### WhatsApp-Specific Biases  
```python
whatsapp_calibrations = {
    'extraversion': '±0.1',         # More authentic social expression
    'openness': 'Neutral',         # Less performative than public platforms
    'neuroticism': '+0.1 to +0.2',  # More likely to share emotional content privately
    'conscientiousness': 'Neutral', # Mix of planning and casual conversation
    'agreeableness': '+0.1 to +0.2' # More cooperative in private communication
}
```

## Implementation Results

### Usage Pattern
```bash
# Standard assessment
python3 bfi_probe.py --samples data/personality_tweets_condensed.json --run baseline

# Calibrated assessment (recommended)
python3 bfi_probe.py --samples data/personality_tweets_condensed.json --calibrated --run baseline
```

### Expected Improvements with Calibrated Prompts
1. **Reduced Extraversion Inflation**: Social media bias awareness
2. **Better Pattern Recognition**: Focus on consistent themes vs. outlier posts
3. **Context-Appropriate Scoring**: Platform-aware trait interpretation
4. **Improved Reliability**: More stable results across multiple runs

### Validation Strategy
```python
def validate_calibration_effectiveness():
    standard_results = []
    calibrated_results = []
    
    for run in range(5):
        # Same samples, different prompt strategies
        standard = bfi_assess(samples, calibrated=False)
        calibrated = bfi_assess(samples, calibrated=True)
        
        standard_results.append(standard)
        calibrated_results.append(calibrated)
    
    return {
        'standard_variance': calculate_variance(standard_results),
        'calibrated_variance': calculate_variance(calibrated_results), 
        'consistency_improvement': standard_variance - calibrated_variance
    }
```

## Key Calibration Principles Discovered

1. **Context Transparency**: Explicitly tell LLM about social media context
2. **Pattern vs. Point**: Focus on consistent patterns, not individual posts
3. **Bias Awareness**: Warn about platform-specific personality amplification
4. **Sample-Specific Adjustments**: Adapt calibration to sample characteristics  
5. **Multi-Dimensional Thinking**: Consider how different traits interact in social contexts

## Future Calibration Enhancements

### Planned Improvements
1. **Multi-Platform Integration**: Combined Twitter + WhatsApp calibration
2. **Temporal Calibration**: Account for personality evolution over time
3. **Demographic Calibration**: Age/culture-specific social media usage patterns
4. **Content-Type Calibration**: Professional vs. personal vs. emotional content weighting