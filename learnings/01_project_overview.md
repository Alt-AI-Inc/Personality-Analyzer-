# OCEAN-5 Personality Assessment Project Overview

## Project Goal
Create an accurate LLM-based personality assessment system using writing samples (tweets, WhatsApp messages) to determine Big Five (OCEAN) personality traits.

## Key Challenge
**Variance Problem**: Initial BFI probe results showed large variance compared to actual personality test scores, indicating systematic issues with LLM-based personality assessment.

## Data Sources Processed
1. **Personal Tweets** (`tweets.js`) - 14,736 non-RT tweets → 5,002 personality-relevant → 200 condensed
2. **WhatsApp Messages** - 3,073 total messages → 740 personality-relevant  
3. **Friend's Tweets** (`Abhishek_tweets.js`) - 7,521 tweets → 3,039 personality-relevant → 200 condensed

## Technical Stack
- **Base Framework**: Modified BFI probe with 60-item Big Five inventory
- **Models Tested**: GPT-4o-mini, GPT-5
- **Data Processing**: JSON extraction, intelligent filtering, smart condensation
- **Assessment Methods**: Traditional BFI, calibrated prompts, reasoning-enhanced analysis

## Core Innovation Areas
1. **Smart Data Filtering** - OCEAN-5 pattern matching for personality-relevant content
2. **Calibrated Prompting** - Context-aware system prompts for social media samples  
3. **Baseline Drift Correction** - Measuring and correcting for LLM personality bias
4. **Reasoning-Enhanced Assessment** - Multi-step analysis leveraging GPT-5 capabilities
5. **Empirical Validation** - Stability testing across sample subsets

## Final Architecture
```
Raw Writing Samples → Smart Filtering → Condensation → Enhanced Assessment → Drift Correction → Final Scores
```

## Key Files Generated
- `personality_tweets_condensed.json` - Your curated personality-relevant tweets
- `WhatsApp.json` - Filtered personal messages
- `Abhishek_personality_tweets_condensed.json` - Friend comparison dataset
- Enhanced `bfi_probe.py` with GPT-5 support and calibrated prompts