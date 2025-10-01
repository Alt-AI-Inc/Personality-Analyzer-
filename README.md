# OCEAN5 Personality Analysis & Chat System

## Overview

This system creates AI-powered conversational agents that mirror an individual's personality across different contexts (personal vs professional). By analyzing real communication data from multiple sources (WhatsApp, LinkedIn, Twitter), we extract Big Five personality traits (OCEAN: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) and generate context-aware chat personalities.

**Why we built this:**
- **Authentic AI Conversations**: Create AI that responds like a real person, not generic chatbots
- **Context Awareness**: Different personality expressions for professional vs personal settings
- **Multi-Source Analysis**: Combine data from various platforms for comprehensive personality modeling
- **Faceted Personality**: Recognize that people communicate differently in work vs casual contexts
- **Research Tool**: Study how personality manifests across different communication mediums

## End-to-End Workflow

```
Raw Data → Processing Config → Filtered Data → Chat Characteristics → AI Personality Chat
   ↓              ↓                ↓                  ↓                    ↓
Your Files → processing_config → personality JSONs → chat configs → Conversational AI
```

---

## Step 1: Prepare Your Data

Place your data files in the `Data/` folder:

```
Data/
├── tweets.js                    # Twitter export (window.YTD.tweets.part0 format)
├── Abhishek.txt                 # WhatsApp chat export
├── LinkedInMessagesShreyas.csv  # LinkedIn messages export
└── ShreyasLinkedinPosts.csv     # LinkedIn posts export
```

**Supported Data Formats:**
- **WhatsApp**: Text export (`[YYYY/MM/DD, HH:MM:SS] Name: Message`)
- **Twitter**: JavaScript export from Twitter archive (`tweets.js`)
- **LinkedIn Messages**: CSV export with `CONTENT` column
- **LinkedIn Posts**: CSV export with `ShareCommentary` column

---

## Step 2: Create Processing Configuration

### Script: `process_personality_data.py --create-config`

**Purpose**: Generates a template configuration file for your data sources

**Key Options**:
- `--create-config`: Creates sample `processing_config.json`
- `--config PATH`: Specify config file location (default: `processing_config.json`)

```bash
python process_personality_data.py --create-config
```

This creates `processing_config.json` - **edit this file** to match your data:

```json
{
  "sources": [
    {
      "name": "shreyas_tweets",
      "type": "twitter", 
      "input_path": "Data/tweets.js",
      "output_path": "Data/filtered_tweets.json",
      "category": "professional",
      "max_items": null,
      "description": "Twitter posts for personality analysis"
    },
    {
      "name": "shreyas_whatsapp",
      "type": "whatsapp",
      "input_path": "Data/Abhishek.txt", 
      "target_person": "Shreyas Srinivasan",
      "output_path": "Data/WhatsApp.json",
      "category": "personal",
      "max_items": null,
      "description": "WhatsApp messages for personality analysis"
    }
  ]
}
```

**Important**: Set correct `category` values:
- `"personal"`: WhatsApp, personal Twitter accounts, private communications
- `"professional"`: LinkedIn, work Twitter, business communications

---

## Step 3: Process & Filter Personality Data

### Script: `process_personality_data.py`

**Purpose**: Converts raw data into personality-relevant filtered JSON files using LLM pre-filtering

**Key Features**:
- **LLM Pre-filtering**: Uses AI to identify content revealing Big Five personality traits
- **Batch Processing**: Processes 50 items per batch for efficiency  
- **Multi-source Support**: Handles Twitter, WhatsApp, LinkedIn data simultaneously
- **Progress Tracking**: Real-time progress feedback
- **Faceted Organization**: Separates personal vs professional content

**Key Options**:
- `--config PATH`: Processing configuration file (default: `processing_config.json`)
- `--source-type TYPE`: Process only specific source types (`twitter`, `whatsapp`, `linkedin_messages`, `linkedin_posts`, `all`)
- `--model MODEL`: LLM model for filtering (`gpt-4o-mini`, `gpt-4o`, `gpt-5`)
- `--debug`: Enable detailed debug output

**Examples**:
```bash
# Process all data sources
python process_personality_data.py

# Process only LinkedIn data  
python process_personality_data.py --source-type linkedin_messages

# Use different model
python process_personality_data.py --model gpt-4o

# Debug mode
python process_personality_data.py --debug
```

**Output**: 
- Filtered JSON files (e.g., `Data/filtered_tweets.json`, `Data/WhatsApp.json`)
- `data_sources_config.json` (configuration for personality analysis)

**Performance**: Processes ~10,000 items in ~15 minutes with batch optimization

---

## Step 4: Generate Faceted Chat Characteristics

### Script: `generate_chat_characteristics.py`

**Purpose**: Analyzes communication patterns and generates faceted conversation templates

**Key Features**:
- **Faceted Analysis**: Separate characteristics for personal vs professional contexts
- **Communication Pattern Detection**: Identifies greeting styles, philosophical response patterns, conversation flow
- **Context-Aware Templates**: Different prompts for casual vs business conversations
- **Optimal Settings**: Facet-specific token limits and temperature settings

**Key Options**:
- `--config PATH`: Processing configuration file (default: `processing_config.json`)
- `--output PATH`: Base output path (default: `chat_characteristics.json`)
- `--debug`: Enable detailed analysis output

**Legacy Options** (single conversation file):
- `--conversation-file FILE`: Single WhatsApp file (legacy mode)
- `--target-person NAME`: Person to analyze (legacy mode)

**Examples**:
```bash
# Faceted analysis (recommended)
python generate_chat_characteristics.py --config processing_config.json

# Custom output location
python generate_chat_characteristics.py --output custom_chat_config.json

# Legacy single-file mode
python generate_chat_characteristics.py --conversation-file Data/Abhishek.txt --target-person "Shreyas Srinivasan"
```

**Output**:
- `chat_characteristics_personal.json`: Personal conversation patterns
- `chat_characteristics_professional.json`: Professional conversation patterns

**Analysis Includes**:
- **Greeting Patterns**: How the person typically responds to "Hey" or "Hello"
- **Philosophical Responses**: Response style for open-ended questions  
- **Conversation Flow**: Natural discussion patterns and transitions
- **Optimal Settings**: Token limits, temperature, context windows

---

## Step 5: Run Personality Analysis

### Script: `bfi_probe_faceted.py`

**Purpose**: Generates Big Five personality profiles for each facet using filtered data

**Key Options**:
- `--facet FACET`: Analyze specific facet (`personal`, `professional`, `both`)
- `--model MODEL`: LLM model for analysis
- `--outdir DIR`: Output directory for results

```bash
python bfi_probe_faceted.py --facet both --model gpt-4o-mini
```

**Output**: P2 personality prompts and OCEAN scores for each facet

---

## Step 6: Interactive Personality Chat

### Script: `chat_with_p2.py`

**Purpose**: Interactive chat system that responds using the analyzed personality across different contexts

**Key Features**:
- **Context Switching**: Automatically detects personal vs professional conversation contexts
- **Personality Consistency**: Maintains personality traits while adapting communication style
- **Template-Driven Responses**: Uses generated chat characteristics for authentic responses
- **Multi-Facet Awareness**: Seamlessly switches between personal and professional modes

**Key Options**:
- `--facet FACET`: Choose conversation context (`personal`, `professional`)
- `--p2-file FILE`: Custom P2 personality file
- `--chat-config FILE`: Custom chat characteristics file
- `--model MODEL`: Chat model to use

**Examples**:
```bash
# Professional chat mode
python chat_with_p2.py --facet professional

# Personal chat mode  
python chat_with_p2.py --facet personal

# Custom configuration
python chat_with_p2.py --facet personal --chat-config custom_chat_characteristics_personal.json
```

**Chat Experience**:
- Responds with authentic personality patterns
- Adapts greeting style based on context
- Uses appropriate conversation flow for facet
- Maintains consistent personality traits while adjusting communication style

---

## Quick Start Guide

```bash
# 1. Create configuration template
python process_personality_data.py --create-config

# 2. Edit processing_config.json with your data paths

# 3. Process all data sources  
python process_personality_data.py

# 4. Generate chat characteristics
python generate_chat_characteristics.py

# 5. Run personality analysis
python bfi_probe_faceted.py --facet both

# 6. Start chatting
python chat_with_p2.py --facet personal
```

## File Structure

```
ocean5/
├── process_personality_data.py     # Main data processing orchestrator
├── process_twitter_data.py         # Twitter-specific processing
├── process_whatsapp_data.py        # WhatsApp-specific processing  
├── process_linkedin_data.py        # LinkedIn-specific processing
├── generate_chat_characteristics.py # Communication pattern analysis
├── bfi_probe_faceted.py            # Personality trait analysis
├── chat_with_p2.py                 # Interactive personality chat
├── processing_config.json          # Data source configuration (user-edited)
├── data_sources_config.json        # Generated personality analysis config
├── chat_characteristics_personal.json    # Personal conversation patterns
├── chat_characteristics_professional.json # Professional conversation patterns
└── Data/
    ├── tweets.js                   # Raw Twitter data
    ├── Abhishek.txt               # Raw WhatsApp data  
    ├── LinkedInMessagesShreyas.csv # Raw LinkedIn messages
    ├── filtered_tweets.json       # Processed Twitter data
    ├── WhatsApp.json              # Processed WhatsApp data
    └── linkedin_messages_simple.json # Processed LinkedIn data
```

## Advanced Usage

### Rate-Limited Processing
For API rate limits, use the rate-limited personality analysis:
```bash
python bfi_probe_rate_limited.py --rpm 15 --compression smart
```

### Custom Data Sources
Add new data sources by extending the processors or creating custom parsers following the established patterns.

### Model Selection
- **gpt-4o-mini**: Fast, cost-effective (recommended for most use cases)
- **gpt-4o**: Higher quality analysis
- **gpt-5**: Premium quality (if available)

## Research Applications

This system enables research into:
- **Personality Expression**: How traits manifest across different communication contexts
- **Platform Effects**: How different platforms influence personality expression
- **Authenticity vs Performance**: Differences between private (WhatsApp) and public (Twitter/LinkedIn) communications
- **Context Adaptation**: How people modify communication styles while maintaining core personality