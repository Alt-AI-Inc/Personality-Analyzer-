# How To Run OCEAN5 - Simple Guide

## What This Does
Creates an AI that talks like you, with separate personalities for work and personal conversations.

## Prerequisites
- Python 3.8+
- OpenAI API key set in environment (`OPENAI_API_KEY`)

### Install Required Packages
```bash
pip install openai pandas numpy
```

## Quick Setup (5 Steps)

### Step 1: Put Your Data in the `Data/` folder
```
Data/
├── tweets.js                    # Your Twitter export
├── chat_export.txt             # Your WhatsApp export  
├── linkedin_messages.csv       # Your LinkedIn messages
└── linkedin_posts.csv          # Your LinkedIn posts
```

### Step 2: Create Config File
```bash
python process_personality_data.py --create-config
```
Then edit `processing_config.json` to point to your actual files.

### Step 3: Process Your Data  
```bash
python process_personality_data.py
```
*This takes 10-15 minutes and processes all your data with AI filtering*

### Step 4: Generate Chat Personality
```bash
python generate_chat_characteristics.py
```
*Creates personal and professional conversation styles*

### Step 5: Chat With Your AI Personality
```bash
# For personal conversations (casual, like texting friends)
python chat_with_p2.py --facet personal

# For work conversations (professional, like LinkedIn)  
python chat_with_p2.py --facet professional
```

## That's It!

Your AI will now respond like you would, adapting its style based on whether it's a personal or professional conversation.

## Common Issues

**"No data found"**: Check your file paths in `processing_config.json`

**"Rate limit error"**: Wait a few minutes, or use:
```bash
python process_personality_data.py --model gpt-4o-mini
```

**"File not found"**: Make sure your data files are in the `Data/` folder

## What Gets Created
- `Data/filtered_*.json` - Your personality-relevant content
- `chat_characteristics_personal.json` - How you chat casually  
- `chat_characteristics_professional.json` - How you communicate at work
- `data_sources_config.json` - Configuration for personality analysis

## Need More Control?
See the full README.md for advanced options and customization.