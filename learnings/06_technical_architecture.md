# Technical Architecture and Implementation Details

## Core System Architecture

### Data Processing Pipeline
```
Raw Export Files (.js) → JSON Extraction → RT Filtering → Personality Filtering → Smart Condensation → Assessment
```

#### Stage 1: JSON Extraction  
```python
# Handle Twitter export format
content = file.read()
json_start = content.find('[')
json_end = content.rfind(']') + 1
json_string = content[json_start:json_end]
tweets = json.loads(json_string)
```

#### Stage 2: Multi-Level Filtering
```python  
def is_personality_relevant(text):
    # Level 1: Exclude non-personality content
    if is_promotional(text) or is_pure_logistics(text):
        return False
    
    # Level 2: Include personality markers
    has_opinion_markers = check_opinion_patterns(text)
    has_emotional_content = check_emotional_patterns(text) 
    has_ocean_indicators = check_personality_patterns(text)
    
    return has_opinion_markers or has_emotional_content or has_ocean_indicators
```

#### Stage 3: Intelligent Condensation
```python
def diversified_sampling(tweets, target_chars):
    # Score each tweet across OCEAN dimensions
    scored_tweets = []
    for tweet in tweets:
        scores = score_tweet(tweet['full_text'])
        scored_tweets.append({'tweet': tweet, 'scores': scores})
    
    # Ensure representation across all personality dimensions
    selected = []
    for dimension in PERSONALITY_PATTERNS.keys():
        top_for_dimension = sorted(scored_tweets, key=lambda x: x['scores'][dimension])[:3]
        selected.extend(top_for_dimension)
    
    # Fill remaining space with highest overall scorers
    # ... (deduplication and final selection)
    
    return selected
```

### Enhanced BFI Probe Architecture

#### Model Abstraction Layer
```python
class LLM:
    def __init__(self, cfg: LLMConfig, debug: bool = False):
        self.cfg = cfg
        self.debug = debug
        
    def chat(self, system: str, user: str, *, max_tokens=None, temperature=None):
        # Handle GPT-4 vs GPT-5 API differences
        if self.cfg.model.startswith('gpt-5'):
            # GPT-5: max_completion_tokens, temperature=1.0 only
            params = {'max_completion_tokens': max_tokens}
        else:
            # GPT-4: max_tokens, custom temperature
            params = {'max_tokens': max_tokens, 'temperature': temperature}
            
        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                return self._make_request(system, user, **params)
            except RateLimitError:
                time.sleep(base_delay * (2 ** attempt))
```

#### Assessment Methods Integration
```python
def administer(llm, items, persona=None, as_if=None, use_calibrated_prompt=False):
    if use_calibrated_prompt and as_if:
        system = create_calibrated_system_prompt(as_if)
    else:
        system = create_standard_system_prompt(persona, as_if)
    
    # Process each BFI item
    answers = {}
    for item in items:
        response = llm.chat(system, item_prompt(item["text"]))
        answers[item["id"]] = extract_rating(response)
        
    return answers
```

### Rate Limiting and Retry Logic

#### Exponential Backoff Implementation
```python
def chat_with_retry(self, system, user, max_tokens=None, temperature=None):
    max_retries = 5
    base_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            return self._make_api_call(system, user, max_tokens, temperature)
        except Exception as e:
            if "rate_limit_exceeded" in str(e):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + (attempt * 0.5)  # Jitter
                    print(f"Rate limit hit, retrying in {delay:.1f}s")
                    time.sleep(delay)
                    continue
            raise e
```

#### Request Pacing
```python
# Built-in delays between requests
for item in BFI_S_ITEMS:
    response = llm.chat(system, item_prompt(item["text"]))
    answers[item["id"]] = process_response(response)
    time.sleep(0.15)  # Prevent rate limit hits
```

## Data Structure Design

### Tweet Processing Data Flow
```python
@dataclass
class TweetData:
    full_text: str
    created_at: str
    retweet_count: int
    favorite_count: int
    
@dataclass  
class PersonalityScore:
    openness: float
    conscientiousness: float  
    extraversion: float
    agreeableness: float
    neuroticism: float

@dataclass
class AssessmentResult:
    baseline_scores: PersonalityScore
    induced_scores: PersonalityScore  
    confidence_intervals: Dict[str, Tuple[float, float]]
    sample_quality: Dict[str, float]
```

### WhatsApp Processing Regex
```python
# Extract messages with timestamp and sender pattern
WHATSAPP_PATTERN = re.compile(
    r'\[([^\]]+)\] Shreyas Srinivasan: (.+?)(?=\n\[|\n‎\[|$)',
    re.MULTILINE | re.DOTALL
)

def extract_whatsapp_messages(content: str) -> List[str]:
    matches = WHATSAPP_PATTERN.findall(content)
    messages = []
    
    for timestamp, message in matches:
        # Clean and normalize message
        cleaned = re.sub(r'\s+', ' ', message.strip())
        if is_valid_message(cleaned):
            messages.append(cleaned)
    
    return messages
```

## Configuration Management

### Model-Specific Configuration
```python  
@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.2
    max_tokens: int = 128
    
    def get_api_params(self) -> Dict:
        if self.model.startswith('gpt-5'):
            return {
                'max_completion_tokens': self.max_tokens,
                # temperature omitted - GPT-5 uses default 1.0
            }
        else:
            return {
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            }
```

### Environment Setup
```python
# .env file support
def setup_environment():
    load_dotenv()  # Load from .env file
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment or .env file")
        
    return OpenAI(api_key=api_key)
```

## File I/O and Persistence

### Smart File Handling
```python
def load_sample_data(samples_path: str) -> Optional[str]:
    """Load sample writing from either text or JSON file."""
    if not samples_path or not os.path.exists(samples_path):
        return None
    
    with open(samples_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    # Auto-detect JSON vs text format
    if samples_path.lower().endswith('.json'):
        data = json.loads(content)
        
        # Handle different JSON structures
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict) and 'full_text' in data[0]:
                # Tweet format: [{"full_text": "..."}, ...]
                return '\n\n'.join([item['full_text'] for item in data])
            elif isinstance(data[0], str):
                # String array: ["text1", "text2", ...]
                return '\n\n'.join(data)
        
        return str(data)  # Fallback
    
    return content  # Plain text
```

### Results Persistence
```python
def save_results(results: Dict, timestamp: str, output_dir: str):
    """Save assessment results with timestamp and metadata."""
    
    # CSV for quantitative analysis
    df = create_results_dataframe(results)
    csv_path = os.path.join(output_dir, f"bfi_probe_{timestamp}.csv")  
    df.to_csv(csv_path, index=False)
    
    # JSON for detailed analysis
    detailed_results = {
        'timestamp': timestamp,
        'model_config': results['config'],
        'sample_info': results['sample_info'], 
        'scores': results['scores'],
        'metadata': results['metadata']
    }
    json_path = os.path.join(output_dir, f"detailed_results_{timestamp}.json")
    
    with open(json_path, 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    return csv_path, json_path
```

## Error Handling and Validation

### Robust JSON Parsing
```python
def _json_repair(txt: str) -> Dict:
    """Repair common JSON formatting issues from LLM responses."""
    m1 = txt.find("{")
    m2 = txt.rfind("}")
    
    if m1 == -1 or m2 == -1 or m2 <= m1:
        raise ValueError("No JSON object detected")
    
    frag = txt[m1:m2+1]
    
    # Common fixes
    if '"' not in frag and "'" in frag:
        frag = frag.replace("'", '"')  # Single to double quotes
        
    frag = re.sub(r",\s*([}\]])", r"\1", frag)  # Remove trailing commas
    
    return json.loads(frag)
```

### Response Validation
```python
def extract_bfi_rating(response: str) -> str:
    """Extract A-E rating from LLM response with fallbacks."""
    
    # Primary extraction
    match = re.search(r"[A-E]", response, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    
    # Fallback patterns
    fallback_patterns = [
        r"very accurate|strongly agree" → "A",
        r"accurate|agree" → "B", 
        r"neither|neutral|unsure" → "C",
        r"inaccurate|disagree" → "D",
        r"very inaccurate|strongly disagree" → "E"
    ]
    
    for pattern, rating in fallback_patterns:
        if re.search(pattern, response.lower()):
            return rating
    
    return "C"  # Default to neutral if no match
```

## Performance Optimization

### Memory Efficiency
```python
# Process large tweet files without loading entire content into memory
def process_tweets_streaming(file_path: str):
    """Process large tweet files in chunks to manage memory."""
    
    with open(file_path, 'r') as f:
        # Find JSON boundaries
        json_start = find_json_start(f)
        json_content = extract_json_streaming(f, json_start)
        
        # Process in batches
        batch_size = 1000
        for batch in chunked(json_content, batch_size):
            yield process_tweet_batch(batch)
```

### Caching Strategy
```python
# Cache processed samples to avoid recomputation
@functools.lru_cache(maxsize=10)
def load_and_process_samples(samples_path: str) -> str:
    """Cache processed samples for repeated assessments."""
    return load_sample_data(samples_path)

# Cache personality pattern matching
@functools.lru_cache(maxsize=1000) 
def score_tweet_cached(tweet_text: str) -> Dict[str, float]:
    """Cache tweet scoring to avoid recomputation.""" 
    return score_tweet(tweet_text)
```