# Complete Usage Guide

## Setup Instructions

### 1. Environment Setup
```bash
# Create .env file with your OpenAI API key
echo 'OPENAI_API_KEY=your-api-key-here' > .env

# Install required packages
pip install openai pandas numpy python-dotenv

# Verify setup
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Setup OK' if os.getenv('OPENAI_API_KEY') else 'Missing API key')"
```

### 2. Data Preparation
Your project supports platform-specific data sources with automatic calibration:

#### Twitter Data (Social Media Assessment)
```bash
# Use processed personality-relevant tweets
# File: data/personality_tweets_condensed.json
# Contains: ~200 curated tweets optimized for OCEAN assessment
# Auto-applies: Social media amplification calibration
```

#### WhatsApp Data (Authentic Assessment)
```bash
# Use processed private messages
# File: data/WhatsApp.json  
# Contains: ~740 personality-relevant messages
# Auto-applies: Minimal calibration (authentic expression)
```

#### Multi-Platform Data (Comprehensive Assessment)
```bash
# Combine both sources for complete personality picture
# Twitter: Performative, public expression (with calibration)
# WhatsApp: Authentic, private expression (minimal calibration)
# Synthesis: WhatsApp weighted higher for authenticity
```

#### Friend's Data (Optional)
```bash
# Friend's Twitter export: data/Abhishek_tweets.js
# Same format as your Twitter data
```

## Assessment Commands (Platform-Specific)

### Single Platform Assessments

#### Twitter-Only Assessment (Social Media Calibrated)
```bash
# Fast, optimized assessment with Twitter data
python3 bfi_probe.py --twitter data/personality_tweets_condensed.json --batched --debug

# Output: Social media amplification automatically corrected
# Speed: ~30 seconds (15x faster than original)
# Calibration: Reduces extraversion, neuroticism, openness by 1-2 levels
```

#### WhatsApp-Only Assessment (Authentic Expression)
```bash
# Authentic personality assessment with minimal calibration
python3 bfi_probe.py --whatsapp data/WhatsApp.json --batched --debug

# Output: Authentic personality with minimal bias correction
# Speed: ~30 seconds
# Calibration: Minimal (treats as genuine personality expression)
```

### Multi-Platform Assessment (Recommended)
```bash
# Comprehensive assessment combining both data sources
python3 bfi_probe.py --twitter data/personality_tweets_condensed.json --whatsapp data/WhatsApp.json --batched --debug

# Output: Synthesized personality profile with platform-specific calibration
# Speed: ~45 seconds
# Calibration: Differential - heavy for Twitter, minimal for WhatsApp
# Weighting: WhatsApp data weighted higher for authenticity
```

### Advanced Options
```bash
# Different assessment types
--run baseline          # LLM personality only (no user data)
--run induced          # User-influenced LLM personality
--run both             # Both baseline and induced (default)

# Performance options  
--batched              # 15x speed improvement (recommended)
--debug               # Show P2 persona generation and detailed responses

# Output options
--outdir results      # Specify output directory (default: results/)
```

## Assessment Methods

### Method 1: Standard BFI Assessment
```bash
# Basic assessment with your tweets
python3 bfi_probe.py --samples data/personality_tweets_condensed.json --run baseline

# With calibrated prompts (recommended)
python3 bfi_probe.py --samples data/personality_tweets_condensed.json --calibrated --run baseline

# Using GPT-5 (if available)
python3 bfi_probe.py --model gpt-5 --samples data/personality_tweets_condensed.json --calibrated --run baseline
```

### Method 2: Enhanced Reasoning Assessment (GPT-5)
```bash
# Multi-step reasoning analysis
python3 gpt5_reasoning_assessment.py

# This provides:
# - Detailed reasoning for each trait
# - Confidence estimates
# - Supporting evidence quotes  
# - Contradiction analysis
```

### Method 3: Cross-Platform Analysis
```bash
# Compare different data sources
python3 bfi_probe.py --samples data/personality_tweets_condensed.json --calibrated --run baseline
python3 bfi_probe.py --samples data/WhatsApp.json --calibrated --run baseline

# Compare with friend's data
python3 bfi_probe.py --samples data/Abhishek_personality_tweets_condensed.json --calibrated --run baseline
```

### Method 4: Model Comparison
```bash
# Compare GPT-4 vs GPT-5 results
python3 compare_models.py
```

## Recommended Assessment Workflow

### For Best Results:
```bash
# 1. Multiple runs for reliability (GPT-5 especially benefits from this)
for i in {1..3}; do
  echo "Run $i:"
  python3 bfi_probe.py --model gpt-5 --samples data/personality_tweets_condensed.json --calibrated --run baseline
done

# 2. Cross-validation with different sample subsets
python3 bfi_probe.py --samples data/personality_tweets_condensed.json --calibrated --run baseline
python3 bfi_probe.py --samples data/WhatsApp.json --calibrated --run baseline

# 3. Enhanced reasoning analysis (if using GPT-5)
python3 gpt5_reasoning_assessment.py

# 4. Compare all results and look for consistent patterns
```

## Understanding Your Results

### Output Files Generated
```bash
results/
├── bfi_probe_YYYYMMDD_HHMMSS.csv          # Quantitative results
├── p2_prompt_YYYYMMDD_HHMMSS.txt           # Persona prompt used
├── gpt5_enhanced_assessment.json           # Detailed reasoning results
├── model_comparison.json                   # GPT-4 vs GPT-5 comparison
└── baseline_profile_MODEL_NAME.json        # Baseline drift measurements
```

### Interpreting Scores
```python
# OCEAN Scale: 1.0 (Very Low) to 5.0 (Very High)
your_results = {
    "O": 3.52,  # Openness: Moderately curious and creative
    "C": 3.18,  # Conscientiousness: Moderately organized  
    "E": 3.58,  # Extraversion: Moderately outgoing
    "A": 3.71,  # Agreeableness: Quite cooperative
    "N": 2.95   # Neuroticism: Emotionally stable
}
```

### Quality Indicators
**Trust your results more when**:
- Multiple runs show similar scores (standard deviation < 0.3)
- Different data sources (Twitter + WhatsApp) show consistent patterns
- Confidence scores from reasoning analysis are >3.5/5.0
- Sample has good OCEAN coverage (check the condensation output)

**Be cautious when**:
- High variance across runs (standard deviation > 0.5)
- Extreme scores (many traits >4.5 or <1.5)
- Single data source only
- Low first-person content in your samples

## Troubleshooting

### Common Issues

#### API Rate Limits
```bash
# Error: Rate limit exceeded
# Solution: The script has built-in retry logic with exponential backoff
# Just wait for it to recover automatically
```

#### GPT-5 Parameter Errors
```bash
# Error: Unsupported parameter 'max_tokens'
# Solution: Code automatically handles this - uses max_completion_tokens for GPT-5

# Error: Unsupported temperature value
# Solution: Code automatically omits temperature for GPT-5 (uses default 1.0)
```

#### Large File Processing
```bash
# Error: File too large or memory issues
# Solution: Use condensed versions of your data
python3 bfi_probe.py --samples data/personality_tweets_condensed.json  # Not the full data
```

#### Missing Dependencies
```bash
# Error: ModuleNotFoundError
pip install openai pandas numpy python-dotenv

# Error: OPENAI_API_KEY not found
echo 'OPENAI_API_KEY=your-key' > .env
```

### Performance Optimization

#### For Faster Results
```bash
# Use condensed samples (200 tweets vs 5000+)
--samples data/personality_tweets_condensed.json

# Use GPT-4o-mini instead of GPT-5 for speed
--model gpt-4o-mini

# Skip enhanced reasoning for quick tests
# (Use standard BFI instead of gpt5_reasoning_assessment.py)
```

#### For Better Accuracy
```bash
# Use calibrated prompts
--calibrated

# Use GPT-5 with reasoning enhancement
python3 gpt5_reasoning_assessment.py

# Run multiple times and average
for i in {1..5}; do python3 bfi_probe.py --samples ... --calibrated; done
```

## Advanced Usage

### Custom Data Sources
```python
# Your custom writing samples in JSON format:
custom_samples = [
    {"full_text": "Your writing sample 1"},
    {"full_text": "Your writing sample 2"},
    # ...
]

# Save as: data/custom_samples.json
# Then run: python3 bfi_probe.py --samples data/custom_samples.json --calibrated
```

### Batch Processing Multiple People
```bash
# Process friend's data for comparison
python3 bfi_probe.py --samples data/Abhishek_personality_tweets_condensed.json --calibrated --run baseline

# Compare results side by side
python3 compare_personalities.py  # (Custom script you can create)
```

### Custom Calibration
```python
# If you know your real personality test scores, you can manually calibrate:
real_scores = {"O": 3.8, "C": 3.2, "E": 4.1, "A": 3.9, "N": 2.1}
llm_scores = {"O": 3.5, "C": 3.4, "E": 3.8, "A": 4.2, "N": 2.8}

# Calculate your personal calibration factors
calibration = {trait: real_scores[trait] - llm_scores[trait] for trait in "OCEAN"}
# Apply to future assessments
```

## Best Practices Summary

1. **Always use `--calibrated` flag** for social media samples
2. **Run multiple assessments** (3-5 times) and average results  
3. **Use multiple data sources** when available (Twitter + WhatsApp)
4. **Focus on patterns and trends** rather than exact numbers
5. **Report confidence intervals** rather than point estimates
6. **Cross-validate** with different sample subsets
7. **Compare with self-knowledge** for sanity checking
8. **Use GPT-5 reasoning analysis** for complex/contradictory cases
9. **Document your methodology** for reproducible results
10. **Understand limitations** - this measures personality expression in specific contexts, not complete personality