
# bfi_probe_patched.py — Robust JSON-mode + retries for gen_keywords
import argparse, json, os, re, time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

try:
    from openai import OpenAI
    _USE_NEW = True
except Exception:
    import openai
    _USE_NEW = False

# === Extended 60-item Big Five inventory (12 per trait) ===
# Each dict: {"id": "...", "text": "...", "trait": "O|C|E|A|N", "reverse": bool}
# reverse=True means the item is reverse-scored on the 1–5 scale.
BFI_S_ITEMS = [
    # ---------- OPENNESS (O1–O12) ----------
    {"id":"O1", "text":"You have an active imagination.",                          "trait":"O","reverse":False},
    {"id":"O2", "text":"You are original and come up with new ideas.",             "trait":"O","reverse":False},
    {"id":"O3", "text":"You have few artistic interests.",                         "trait":"O","reverse":True},
    {"id":"O4", "text":"You are curious about many different things.",             "trait":"O","reverse":False},
    {"id":"O5", "text":"You prefer routine over variety.",                         "trait":"O","reverse":True},
    {"id":"O6", "text":"You appreciate art, music, or poetry.",                    "trait":"O","reverse":False},
    {"id":"O7", "text":"You avoid abstract conversations.",                        "trait":"O","reverse":True},
    {"id":"O8", "text":"You enjoy exploring new places.",                          "trait":"O","reverse":False},
    {"id":"O9", "text":"You are uninterested in theories.",                        "trait":"O","reverse":True},
    {"id":"O10","text":"You like tackling complex problems.",                      "trait":"O","reverse":False},
    {"id":"O11","text":"You are conservative about new experiences.",              "trait":"O","reverse":True},
    {"id":"O12","text":"You value creativity in your work.",                       "trait":"O","reverse":False},

    # ---------- CONSCIENTIOUSNESS (C1–C12) ----------
    {"id":"C1", "text":"You do a thorough job.",                                   "trait":"C","reverse":False},
    {"id":"C2", "text":"You can be somewhat careless.",                            "trait":"C","reverse":True},
    {"id":"C3", "text":"You are reliable and get things done.",                    "trait":"C","reverse":False},
    {"id":"C4", "text":"You keep things tidy and organized.",                      "trait":"C","reverse":False},
    {"id":"C5", "text":"You leave tasks unfinished.",                              "trait":"C","reverse":True},
    {"id":"C6", "text":"You follow schedules closely.",                            "trait":"C","reverse":False},
    {"id":"C7", "text":"You procrastinate important work.",                        "trait":"C","reverse":True},
    {"id":"C8", "text":"You pay attention to details.",                            "trait":"C","reverse":False},
    {"id":"C9", "text":"You are impulsive with commitments.",                      "trait":"C","reverse":True},
    {"id":"C10","text":"You plan ahead before acting.",                            "trait":"C","reverse":False},
    {"id":"C11","text":"You misplace things often.",                               "trait":"C","reverse":True},
    {"id":"C12","text":"You stick to goals despite obstacles.",                    "trait":"C","reverse":False},

    # ---------- EXTRAVERSION (E1–E12) ----------
    {"id":"E1", "text":"You are talkative.",                                       "trait":"E","reverse":False},
    {"id":"E2", "text":"You are reserved.",                                        "trait":"E","reverse":True},
    {"id":"E3", "text":"You are outgoing and sociable.",                           "trait":"E","reverse":False},
    {"id":"E4", "text":"You are energetic and high-spirited.",                     "trait":"E","reverse":False},
    {"id":"E5", "text":"You are quiet in groups.",                                 "trait":"E","reverse":True},
    {"id":"E6", "text":"You prefer being alone.",                                  "trait":"E","reverse":True},
    {"id":"E7", "text":"You are assertive in discussions.",                        "trait":"E","reverse":False},
    {"id":"E8", "text":"You avoid being the center of attention.",                 "trait":"E","reverse":True},
    {"id":"E9", "text":"You are enthusiastic with strangers.",                     "trait":"E","reverse":False},
    {"id":"E10","text":"You keep conversations short.",                            "trait":"E","reverse":True},
    {"id":"E11","text":"You enjoy parties and gatherings.",                        "trait":"E","reverse":False},
    {"id":"E12","text":"You say little in meetings.",                              "trait":"E","reverse":True},

    # ---------- AGREEABLENESS (A1–A12) ----------
    {"id":"A1", "text":"You are considerate and kind to almost everyone.",         "trait":"A","reverse":False},
    {"id":"A2", "text":"You tend to find fault with others.",                      "trait":"A","reverse":True},
    {"id":"A3", "text":"You are helpful and unselfish with others.",               "trait":"A","reverse":False},
    {"id":"A4", "text":"You stay polite even when stressed.",                      "trait":"A","reverse":False},
    {"id":"A5", "text":"You are stubborn in disagreements.",                       "trait":"A","reverse":True},
    {"id":"A6", "text":"You trust people easily.",                                 "trait":"A","reverse":False},
    {"id":"A7", "text":"You are skeptical of others’ motives.",                    "trait":"A","reverse":True},
    {"id":"A8", "text":"You are forgiving when wronged.",                          "trait":"A","reverse":False},
    {"id":"A9", "text":"You enjoy competition more than cooperation.",             "trait":"A","reverse":True},
    {"id":"A10","text":"You are patient with others’ mistakes.",                   "trait":"A","reverse":False},
    {"id":"A11","text":"You are critical and blunt.",                              "trait":"A","reverse":True},
    {"id":"A12","text":"You are empathetic to others’ feelings.",                  "trait":"A","reverse":False},

    # ---------- NEUROTICISM (N1–N12) ----------
    {"id":"N1", "text":"You are relaxed and handle stress well.",                  "trait":"N","reverse":True},
    {"id":"N2", "text":"You get nervous easily.",                                  "trait":"N","reverse":False},
    {"id":"N3", "text":"You worry a lot.",                                         "trait":"N","reverse":False},
    {"id":"N4", "text":"Your mood changes frequently.",                            "trait":"N","reverse":False},
    {"id":"N5", "text":"You are calm in emergencies.",                             "trait":"N","reverse":True},
    {"id":"N6", "text":"You often feel down or blue.",                             "trait":"N","reverse":False},
    {"id":"N7", "text":"You are rarely irritated.",                                "trait":"N","reverse":True},
    {"id":"N8", "text":"You get frustrated easily.",                               "trait":"N","reverse":False},
    {"id":"N9", "text":"You are emotionally stable day to day.",                   "trait":"N","reverse":True},
    {"id":"N10","text":"You ruminate over problems.",                              "trait":"N","reverse":False},
    {"id":"N11","text":"You take things in stride.",                               "trait":"N","reverse":True},
    {"id":"N12","text":"You feel overwhelmed by pressure.",                        "trait":"N","reverse":False},
]

LIKERT = {"A":5,"B":4,"C":3,"D":2,"E":1}
REV = lambda v: 6 - v
@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.2
    max_tokens: int = 128
class LLM:
    def __init__(self, cfg: LLMConfig, debug: bool=False):
        self.cfg = cfg
        self.debug = debug
        if _USE_NEW:
            self.cli = OpenAI()
        else:
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.cli = None
    def chat(self, system: str, user: str, *, max_tokens: Optional[int]=None, temperature: Optional[float]=None) -> str:
        mt = max_tokens if max_tokens is not None else self.cfg.max_tokens
        temp = temperature if temperature is not None else self.cfg.temperature
        
        max_retries = 5
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                if _USE_NEW:
                    # Build parameters dynamically to avoid None/null values
                    params = {
                        "model": self.cfg.model,
                        "messages": [{"role":"system","content":system},{"role":"user","content":user}]
                    }
                    
                    # Handle parameter differences between reasoning and traditional models
                    if self.cfg.model.startswith(('gpt-5', 'o1', 'o3')):
                        # Reasoning models use max_completion_tokens and NO sampling parameters
                        if mt is not None:
                            params["max_completion_tokens"] = mt
                        # Do not send temperature/top_p/etc for reasoning models
                    else:
                        # Traditional models use max_tokens and support sampling parameters
                        if mt is not None:
                            params["max_tokens"] = mt
                        if temp is not None:
                            params["temperature"] = temp
                    
                    if self.debug:
                        print(f"[DEBUG] API call params: {params}")
                    
                    r = self.cli.chat.completions.create(**params)
                    out = r.choices[0].message.content
                    
                    if self.debug:
                        print(f"[DEBUG] Raw response: {repr(out)}")
                        print(f"[DEBUG] Usage: {r.usage}")
                        if hasattr(r.usage, 'completion_tokens_details'):
                            print(f"[DEBUG] Reasoning tokens: {r.usage.completion_tokens_details.reasoning_tokens}")
                    
                    if out is None:
                        out = ""
                    else:
                        out = out.strip()
                else:
                    r = openai.ChatCompletion.create(
                        model=self.cfg.model,
                        messages=[{"role":"system","content":system},{"role":"user","content":user}],
                        temperature=temp,
                        max_tokens=mt,
                    )
                    out = r["choices"][0]["message"]["content"].strip()
                
                if self.debug:
                    print("\n[chat OUT]\n", out[:800], "\n---")
                return out
                
            except Exception as e:
                if "rate_limit_exceeded" in str(e) or "RateLimitError" in str(type(e)):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                        print(f"Rate limit hit, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                raise e
    def chat_json(self, system: str, user: str, *, max_tokens: int=512, temperature: float=0.0) -> str:
        max_retries = 5
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                if _USE_NEW:
                    # Build parameters dynamically to avoid None/null values
                    params = {
                        "model": self.cfg.model,
                        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
                        "response_format": {"type":"json_object"}
                    }
                    
                    # Handle parameter differences between reasoning and traditional models
                    if self.cfg.model.startswith(('gpt-5', 'o1', 'o3')):
                        # Reasoning models use max_completion_tokens and NO sampling parameters
                        if max_tokens is not None:
                            params["max_completion_tokens"] = max_tokens
                        # Do not send temperature/top_p/etc for reasoning models
                    else:
                        # Traditional models use max_tokens and support sampling parameters
                        if max_tokens is not None:
                            params["max_tokens"] = max_tokens
                        if temperature is not None:
                            params["temperature"] = temperature
                    
                    if self.debug:
                        print(f"[DEBUG JSON] API call params: {params}")
                    
                    r = self.cli.chat.completions.create(**params)
                    out = r.choices[0].message.content
                    
                    if self.debug:
                        print(f"[DEBUG JSON] Raw response: {repr(out)}")
                        print(f"[DEBUG JSON] Usage: {r.usage}")
                        if hasattr(r.usage, 'completion_tokens_details'):
                            print(f"[DEBUG JSON] Reasoning tokens: {r.usage.completion_tokens_details.reasoning_tokens}")
                    
                    if out is None:
                        out = ""
                    else:
                        out = out.strip()
                else:
                    sys2 = system + " Respond with STRICT JSON only. No prose, no code fences."
                    out = self.chat(sys2, user, max_tokens=max_tokens, temperature=temperature)
                return out
                
            except Exception as e:
                if "rate_limit_exceeded" in str(e) or "RateLimitError" in str(type(e)):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + (attempt * 0.5)
                        print(f"Rate limit hit (JSON), retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                raise e


# Converts incoming strings into a dictionary like {"O":"high","C":"med","E":"med","A":"med","N":"low"}
def parse_target(s: str) -> Dict[str,str]:
    tgt = {"O":"med","C":"med","E":"med","A":"med","N":"med"}
    for part in s.split(","):
        if ":" in part:
            k,v = part.split(":")
            k=k.strip().upper(); v=v.strip().lower()
            if v=="medium": v="med"
            if k in tgt and v in {"high","med","low"}: tgt[k]=v
    return tgt

def naive_line(tgt: Dict[str,str]) -> str:
    def phr(tr, lvl):
        if lvl=="high":
            return {"O":"open to experience","C":"conscientious and organized","E":"extraverted and energetic","A":"agreeable and warm","N":"sensitive and easily stressed"}[tr]
        if lvl=="low":
            return {"O":"practical and conventional","C":"flexible and easygoing about structure","E":"introverted and reserved","A":"direct and less people-pleasing","N":"emotionally stable and calm"}[tr]
        return {"O":"moderately curious","C":"moderately organized","E":"moderately outgoing","A":"moderately cooperative","N":"moderately calm"}[tr]
    return "You consistently speak like someone who is " + ", ".join([phr(t, tgt[t]) for t in "OCEAN"]) + "."

def _json_repair(txt: str) -> Dict:
    m1 = txt.find("{"); m2 = txt.rfind("}")
    if m1 == -1 or m2 == -1 or m2 <= m1:
        raise ValueError("No JSON object detected")
    frag = txt[m1:m2+1]
    if '"' not in frag and "'" in frag:
        frag = frag.replace("'", '"')
    frag = re.sub(r",\s*([}\]])", r"\1", frag)
    return json.loads(frag)

def gen_keywords(llm: LLM, tgt: Dict[str,List[str]]) -> Dict[str,List[str]]:
    sys = "You are a psychology-savvy prompt engineer. You must respond with valid JSON only."
    user = (
        "For each Big Five trait (O,C,E,A,N), list 6-10 clear adjectives (no phrases) matching these target levels. "
        "Return STRICT JSON with keys O,C,E,A,N each mapping to a list of adjectives. "
        "Example format: {\"O\": [\"creative\", \"curious\"], \"C\": [\"organized\", \"disciplined\"], \"E\": [\"outgoing\", \"energetic\"], \"A\": [\"cooperative\", \"trusting\"], \"N\": [\"anxious\", \"moody\"]} "
        f"Targets: {json.dumps(tgt)}"
    )
    
    # Try multiple approaches to get valid JSON
    for attempt in range(3):
        try:
            if attempt == 0:
                txt = llm.chat_json(sys, user, max_tokens=600, temperature=0.0)
            elif attempt == 1:
                txt = llm.chat(sys + " Respond ONLY with JSON.", user, max_tokens=600, temperature=0.0)
            else:
                # Fallback: use a simplified approach
                txt = llm.chat(sys, "Return JSON with personality adjectives for O,C,E,A,N traits", max_tokens=600, temperature=0.0)
            
            # Try to parse JSON
            try:
                obj = json.loads(txt)
                break
            except Exception:
                obj = _json_repair(txt)
                break
                
        except Exception as e:
            if attempt == 2:  # Last attempt failed
                print(f"Warning: JSON generation failed, using fallback keywords")
                # Fallback to predefined keywords based on target levels
                obj = generate_fallback_keywords(tgt)
                break
            else:
                print(f"JSON attempt {attempt + 1} failed: {e}")
                continue
    
    # Clean and validate the results
    clean = {}
    for k in ["O","C","E","A","N"]:
        vals = obj.get(k, [])
        if isinstance(vals, str): vals = [vals]
        vals = [str(w).strip().lower().split()[0] for w in vals if str(w).strip()]
        seen=set(); uniq=[]
        for w in vals:
            if w not in seen:
                seen.add(w); uniq.append(w)
        clean[k] = uniq[:10] if uniq else get_default_keywords(k, tgt.get(k, "med"))
    
    return clean

def generate_fallback_keywords(tgt: Dict[str,str]) -> Dict[str,List[str]]:
    """Generate fallback keywords when JSON generation fails."""
    fallback = {
        "O": {
            "high": ["creative", "imaginative", "curious", "original", "artistic", "abstract"],
            "med": ["moderately_curious", "somewhat_creative", "balanced_thinking", "open_minded"],
            "low": ["practical", "conventional", "realistic", "traditional", "concrete"]
        },
        "C": {
            "high": ["organized", "disciplined", "reliable", "systematic", "thorough", "methodical"],
            "med": ["moderately_organized", "somewhat_reliable", "balanced_planning"],
            "low": ["flexible", "spontaneous", "casual", "adaptable", "easygoing"]
        },
        "E": {
            "high": ["outgoing", "energetic", "social", "assertive", "talkative", "enthusiastic"],
            "med": ["moderately_social", "balanced_energy", "selectively_outgoing"],
            "low": ["reserved", "quiet", "introspective", "solitary", "private"]
        },
        "A": {
            "high": ["cooperative", "trusting", "helpful", "empathetic", "considerate", "kind"],
            "med": ["moderately_cooperative", "balanced_trust", "selectively_helpful"],
            "low": ["competitive", "skeptical", "direct", "independent", "critical"]
        },
        "N": {
            "high": ["anxious", "moody", "sensitive", "emotional", "stressed", "reactive"],
            "med": ["moderately_stable", "occasionally_worried", "balanced_emotions"],
            "low": ["calm", "stable", "resilient", "composed", "secure"]
        }
    }
    
    result = {}
    for trait, level in tgt.items():
        result[trait] = fallback.get(trait, {}).get(level, fallback[trait]["med"])
    
    return result

def get_default_keywords(trait: str, level: str) -> List[str]:
    """Get default keywords for a trait/level combination."""
    defaults = generate_fallback_keywords({trait: level})
    return defaults.get(trait, ["moderate"])

def gen_portrait(llm: LLM, seed: str, kw: Dict[str,List[str]]) -> str:
    sys = "You write concise persona prompts about how someone SPEAKS (cadence, hedging, directness, enthusiasm, vocabulary)."
    user = "Seed line: " + seed + "\nKeywords per trait: " + json.dumps(kw) + "\nWrite 5–7 short sentences describing speech patterns only. No biography. Return sentences only."
    print("User persona prompt",user)

    return llm.chat(sys, user, max_tokens=400, temperature=0.2)

def build_calibrated_p2(llm, writing_samples, platforms_used):
    """Build P2 persona from platform-calibrated writing samples"""
    if not writing_samples:
        return "You are high in OCEAN, low in N."
    
    # Apply platform-specific calibration to interpret the data
    calibrated_prompt = "Analyze the following writing samples and describe the author's personality. "
    
    if len(platforms_used) == 1:
        platform = platforms_used[0]
        if platform == "twitter":
            calibrated_prompt += """Apply TWITTER CALIBRATION when analyzing:
- Reduce apparent extraversion by 1 level (Twitter amplifies social behavior)
- Reduce apparent conscientiousness by 1 level if mostly professional content  
- Reduce apparent neuroticism by 1-2 levels (emotional tweets are amplified)
- Reduce apparent openness by 1 level if mostly creative content
- Focus on consistent patterns, not individual dramatic posts"""
        elif platform == "whatsapp":
            calibrated_prompt += """Apply WHATSAPP ANALYSIS (minimal calibration):
- These are authentic private messages, generally reflecting true personality
- Focus on overall communication patterns and relationship dynamics
- Emotional expressions are usually genuine, not amplified"""
    else:
        calibrated_prompt += """Apply MULTI-PLATFORM ANALYSIS:
- For TWITTER sections: Apply social media calibration (reduce amplified traits by 1-2 levels)
- For WHATSAPP sections: Treat as authentic personality expression
- Synthesize across both platforms, giving WhatsApp data slightly more weight for authenticity"""
    
    calibrated_prompt += f"\n\nWRITING SAMPLES:\n{writing_samples}\n\nCreate a comprehensive personality profile using this structure:\n\nBIG FIVE TRAITS:\nO: [one sentence about openness]\nC: [one sentence about conscientiousness] \nE: [one sentence about extraversion]\nA: [one sentence about agreeableness]\nN: [one sentence about neuroticism]\n\nINTERESTS & PREFERENCES:\n[2-3 sentences about what this person is likely interested in, hobbies, topics they enjoy discussing]\n\nCOMMUNICATION STYLE:\n[2-3 sentences about how they typically communicate, their tone, formality level]\n\nLANGUAGE PATTERNS & EXPRESSIONS:\n[List specific phrases, words, or expressions this person commonly uses. Include how they express laughter (haha, lol, 😂, etc.), their typical greeting responses (\"hey!\", \"what's up\", \"good to see you\", etc.), and frequently used verbs or descriptive words]\n\nSOCIAL INTERACTIONS:\n[2-3 sentences about how they respond to initial greetings, their use of humor, emojis, jokes, and social engagement patterns]\n\nWORK & PRODUCTIVITY PATTERNS:\n[2-3 sentences about their approach to work, deadlines, collaboration, and productivity habits]\n\nApply platform calibration as specified above to all sections."
    
    # GPT-5 needs more tokens for reasoning + comprehensive personality analysis
    analysis_token_limit = 4000 if llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')) else 2000
    personality_analysis = llm.chat("You are a personality assessment expert.", calibrated_prompt, max_tokens=analysis_token_limit, temperature=0.2)
    
    if llm.debug:
        print(f"\n[P2 DEBUG] Requested tokens: 2000")
        print(f"[P2 DEBUG] Response length: {len(personality_analysis)} characters")
        print(f"[P2 DEBUG] Full response: {personality_analysis}")
    
    return f"PERSONALITY PROMPT (P²)\nYou are a person with this personality: {personality_analysis}"

def build_p2(llm: LLM, tgt: Dict[str,str]) -> str:
    seed = naive_line(tgt)
    kw = gen_keywords(llm, tgt)
    portrait = gen_portrait(llm, seed, kw)
    print("User potrait",portrait)
    return f"PERSONALITY PROMPT (P²)\n{seed}\nStyle portrait:\n{portrait}\n"

def item_prompt(text: str, reasoning_model: bool = False) -> str:
    if reasoning_model:
        return (f"Consider this statement: \"{text}\"\n\n"
                "Rate how accurate this is:\n"
                "A = Very Accurate\n"
                "B = Accurate\n"
                "C = Neither accurate nor inaccurate\n"
                "D = Inaccurate\n"
                "E = Very Inaccurate\n\n"
                "Think about it, then respond with just the letter (A, B, C, D, or E).")
    else:
        return ("Rate how accurately the statement describes you.\n"
                "Choose exactly one letter:\nA=Very Accurate, B=Accurate, C=Neither, D=Inaccurate, E=Very Inaccurate\n\n"
                f"Statement: {text}\n\n"
                "Respond with a single letter (A/B/C/D/E) and nothing else.")

def get_platform_calibration(platform):
    """Get platform-specific calibration instructions"""
    if platform == "twitter":
        return """TWITTER CALIBRATION CORRECTIONS - Apply these adjustments when rating:
- EXTRAVERSION: Twitter amplifies outgoing behavior. If posts seem highly extraverted, reduce your rating by 1 level (e.g., A→B, B→C). Maximum discount: 1 level.
- CONSCIENTIOUSNESS: Work/professional tweets inflate perceived organization. If you see mostly professional content, reduce conscientiousness ratings by 1 level. Maximum discount: 1 level.
- NEUROTICISM: Emotional tweets are amplified on social media. If posts seem highly neurotic/emotional, reduce your rating by 1-2 levels depending on intensity. Maximum discount: 2 levels.
- OPENNESS: Creative/artistic tweets overemphasize intellectual interests. If posts focus on creative topics, reduce openness ratings by 1 level. Maximum discount: 1 level.
- AGREEABLENESS: Twitter can mask true interpersonal style. Rate based on consistent interaction patterns, not individual posts.

IMPORTANT: Only apply corrections when you see clear evidence of Twitter amplification. If unsure, use your initial judgment."""
    
    elif platform == "whatsapp":
        return """WHATSAPP CALIBRATION NOTES:
- WhatsApp messages are generally more authentic than social media posts
- Focus on consistent communication patterns across multiple conversations
- Consider that personal messages may show more emotional vulnerability (this is normal, not amplification)
- Rate based on overall interaction style and relationship dynamics

MINIMAL CORRECTIONS: Only discount extreme language if it appears to be momentary venting rather than personality patterns."""
    
    elif platform == "multi":
        return """MULTI-PLATFORM CALIBRATION:
- You have both TWITTER and WHATSAPP data - treat each section differently
- For TWITTER sections: Apply social media calibration (reduce amplified traits by 1-2 levels)
- For WHATSAPP sections: Minimal calibration (more authentic personality expression)
- Synthesize across both platforms to get a complete personality picture
- When conflicts arise, give WhatsApp data slightly more weight as it's more authentic

TWITTER CORRECTIONS: Reduce extraversion, conscientiousness, neuroticism, openness by 1-2 levels when amplified
WHATSAPP: Rate authentically with minimal corrections"""
    
    else:
        return ""

def administer_batched(llm, items, persona=None, as_if=None, platform=None):
    """Fast batched administration - splits into 2 batches of 30 questions each"""
    system = """You are completing a standardized personality inventory. Answer honestly in first person.
        
Output format: For each question, respond with only the letter (A/B/C/D/E) where:
A=Very Accurate, B=Accurate, C=Neither, D=Inaccurate, E=Very Inaccurate"""
    
    if persona: 
        system = persona + "\n\n" + system

    # Split into 2 batches of 30 questions each
    batch_size = 30
    all_answers = {}
    
    for batch_num in range(0, len(items), batch_size):
        batch_items = items[batch_num:batch_num + batch_size]
        batch_name = f"Batch {batch_num//batch_size + 1}"
        
        # Build questions for this batch
        questions_text = f"Rate how accurately each statement describes you ({batch_name}):\n\n"
        for i, item in enumerate(batch_items, 1):
            questions_text += f"{i}. {item['text']}\n"
        
        questions_text += f"\n\nRespond with exactly {len(batch_items)} letters separated by spaces.\nFormat: A B C D E A B C D E..."
        
        # API call for this batch
        # GPT-5 needs much more tokens for reasoning + batch output
        batch_token_limit = 1000 if llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')) else 200
        resp = llm.chat(system, questions_text, max_tokens=batch_token_limit, temperature=0.0)
        
        if llm.debug:
            print(f"\n[BATCHED] {batch_name}: Asked {len(batch_items)} questions")
            print(f"[BATCHED] {batch_name} Response: '{resp}'")
        
        # Parse responses for this batch
        answers = re.findall(r'[A-E]', resp, re.I)
        
        # Map back to item IDs
        for i, item in enumerate(batch_items):
            if i < len(answers):
                all_answers[item["id"]] = answers[i].upper()
            else:
                all_answers[item["id"]] = "C"  # Default fallback
                if llm.debug:
                    print(f"[BATCHED] {batch_name}: Missing answer for {item['id']}, using default 'C'")
    
    return all_answers

def administer(llm, items, persona=None, as_if=None, platform=None):
    # Different system prompts for reasoning vs traditional models
    if llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')):
        system = "You are completing a personality test. Think through each statement carefully, then respond with only a single letter (A, B, C, D, or E)."
    else:
        system = "You are completing a standardized personality inventory. Answer honestly in first person. Output only A/B/C/D/E."
    
    if persona: system = persona + "\n\n" + system
    
    out={}
    is_reasoning_model = llm.cfg.model.startswith(('gpt-5', 'o1', 'o3'))
    
    for it in items:
        question = item_prompt(it["text"], reasoning_model=is_reasoning_model)
        # GPT-5 needs much more tokens for reasoning + output  
        token_limit = 1000 if is_reasoning_model else 8
        
        # Retry with more tokens if we hit the limit (reasoning models only)
        for attempt in range(3 if is_reasoning_model else 1):
            try:
                resp = llm.chat(system, question, max_tokens=token_limit, temperature=0.0)
                break  # Success, exit retry loop
            except Exception as e:
                if is_reasoning_model and "max_tokens or model output limit" in str(e):
                    token_limit *= 2  # Double the tokens and retry
                    if llm.debug:
                        print(f"[{it['id']}] Retrying with {token_limit} tokens (attempt {attempt + 2})")
                    continue
                else:
                    # Not a token limit error, or not a reasoning model, re-raise
                    raise e
        else:
            # All retries failed
            resp = ""
            if llm.debug:
                print(f"[{it['id']}] All retries failed, using default answer 'C'")
        
        m = re.search(r"[A-E]", resp, re.I)
        answer = (m.group(0).upper() if m else "C")
        out[it["id"]] = answer
        
        # Enhanced debug output for induced assessments
        if llm.debug and persona:  # Only show for induced (when persona is present)
            print(f"\n[{it['id']}] Question: {it['text']}")
            print(f"[{it['id']}] Answer: {answer} (from: '{resp}')")
        
        time.sleep(0.15)
    return out

def score(items, ans):
    by = {"O":[],"C":[],"E":[],"A":[],"N":[]}
    for it in items:
        raw = LIKERT.get(ans.get(it["id"],"C"),3)
        val = REV(raw) if it["reverse"] else raw
        by[it["trait"]].append(val)
    means = {t: float(np.mean(v)) for t,v in by.items()}
    disp  = {t: float(np.std(v, ddof=0)) for t,v in by.items()}
    return means, disp

def load_drift_corrections(model_name: str, outdir: str = "results") -> Optional[Dict[str, float]]:
    """Load baseline drift corrections if available."""
    profile_path = os.path.join(outdir, f"baseline_profile_{model_name.replace('/', '_')}.json")
    
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            profile = json.load(f)
            return profile.get('corrections', {})
    
    return None

def apply_drift_correction(scores: Dict[str, float], corrections: Dict[str, float]) -> Dict[str, float]:
    """Apply drift corrections to personality scores."""
    if not corrections:
        return scores
    
    corrected = {}
    for trait in "OCEAN":
        if trait in corrections:
            corrected_score = scores[trait] + corrections[trait]
            # Clamp to valid range [1.0, 5.0]
            corrected[trait] = max(1.0, min(5.0, corrected_score))
        else:
            corrected[trait] = scores[trait]
    
    return corrected

def save_detailed_results(base_ans, ind_ans, items, outdir, timestamp):
    """Save question-by-question detailed results"""
    detailed_data = []
    for item in items:
        base_response = base_ans.get(item['id'], 'C') if base_ans else 'N/A'
        ind_response = ind_ans.get(item['id'], 'C') if ind_ans else 'N/A'
        
        # Calculate scores (with reverse scoring if needed)
        base_raw = LIKERT.get(base_response, 3) if base_response != 'N/A' else 'N/A'
        ind_raw = LIKERT.get(ind_response, 3) if ind_response != 'N/A' else 'N/A'
        
        base_score = REV(base_raw) if item['reverse'] and base_raw != 'N/A' else base_raw
        ind_score = REV(ind_raw) if item['reverse'] and ind_raw != 'N/A' else ind_raw
        
        detailed_data.append({
            'Question_ID': item['id'],
            'Trait': item['trait'],
            'Question_Text': item['text'],
            'Reverse_Scored': item['reverse'],
            'Baseline_Answer': base_response,
            'Induced_Answer': ind_response,
            'Baseline_Raw_Score': base_raw,
            'Induced_Raw_Score': ind_raw,
            'Baseline_Final_Score': base_score,
            'Induced_Final_Score': ind_score,
            'Score_Difference': ind_score - base_score if (ind_score != 'N/A' and base_score != 'N/A') else 'N/A'
        })
    
    detailed_df = pd.DataFrame(detailed_data)
    detailed_path = os.path.join(outdir, f"bfi_detailed_{timestamp}.csv")
    detailed_df.to_csv(detailed_path, index=False)
    print(f"📋 Detailed results saved: {detailed_path}")
    return detailed_path

def compare_df(base_m, ind_m, base_d, ind_d, corrections=None):
    rows=[]
    for t in "OCEAN":
        row = {
            "Trait": t,
            "Baseline": round(base_m.get(t, float('nan')),3),
            "Induced": round(ind_m.get(t, float('nan')),3),
            "Δ (Induced - Baseline)": round(ind_m.get(t,0)-base_m.get(t,0),3),
            "Dispersion (Base)": round(base_d.get(t, float('nan')),3),
            "Dispersion (Induced)": round(ind_d.get(t, float('nan')),3),
        }
        
        # Add drift correction info if available
        if corrections and t in corrections:
            row["Drift Correction"] = round(corrections[t], 3)
        
        rows.append(row)
    return pd.DataFrame(rows)

def load_sample_data(samples_path: str) -> Optional[str]:
    """Load sample writing from either text or JSON file."""
    if not samples_path or not os.path.exists(samples_path):
        return None
    
    with open(samples_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    # Check if it's a JSON file
    if samples_path.lower().endswith('.json'):
        try:
            data = json.loads(content)
            
            # Handle list of tweet objects with full_text field
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict) and 'full_text' in data[0]:
                    # Extract full_text from tweet objects
                    texts = [item['full_text'] for item in data if 'full_text' in item]
                    return '\n\n'.join(texts)
                elif isinstance(data[0], str):
                    # Handle list of strings
                    return '\n\n'.join(data)
            
            # Handle single object or other JSON structures
            elif isinstance(data, dict):
                if 'full_text' in data:
                    return data['full_text']
                else:
                    # Convert dict to string representation
                    return str(data)
            
            # Fallback: convert to string
            return str(data)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as plain text
            pass
    
    # Return as plain text
    return content

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, default="gpt-4o-mini")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--run", choices=["baseline","induced","both"], default="both")
    ap.add_argument("--target", type=str, default="O:high,C:high,E:high,A:high,N:low")
    ap.add_argument("--twitter", type=str, default=None, help="Path to Twitter data file - applies social media calibration")
    ap.add_argument("--whatsapp", type=str, default=None, help="Path to WhatsApp data file - applies minimal calibration")
    ap.add_argument("--outdir", type=str, default="results")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--drift-correction", action="store_true", help="Apply baseline drift correction to account for model personality bias")
    ap.add_argument("--batched", action="store_true", help="Use fast batched assessment (all questions in one API call)")
    args = ap.parse_args()
    cfg = LLMConfig(model=args.model, temperature=args.temperature, max_tokens=128)
    llm = LLM(cfg, debug=args.debug)
    os.makedirs(args.outdir, exist_ok=True)
    # Load data from multiple platforms
    combined_data = []
    platforms_used = []
    
    if args.twitter:
        twitter_data = load_sample_data(args.twitter)
        if twitter_data:
            combined_data.append(f"=== TWITTER DATA ===\n{twitter_data}")
            platforms_used.append("twitter")
    
    if args.whatsapp:
        whatsapp_data = load_sample_data(args.whatsapp)
        if whatsapp_data:
            combined_data.append(f"=== WHATSAPP DATA ===\n{whatsapp_data}")
            platforms_used.append("whatsapp")
    
    if not combined_data:
        print("Error: Must specify at least one data source (--twitter or --whatsapp)")
        return
        
    as_if = "\n\n".join(combined_data)
    platform = "multi" if len(platforms_used) > 1 else platforms_used[0]
    
    # P2 will be built only when needed for induced mode
    p2 = None
    
    # Load drift corrections if requested
    corrections = None
    if args.drift_correction:
        corrections = load_drift_corrections(args.model, args.outdir)
        if corrections:
            print(f"✅ Loaded drift corrections for {args.model}")
            for trait, correction in corrections.items():
                print(f"   {trait}: {correction:+.3f}")
        else:
            print(f"⚠️  No drift corrections found for {args.model}")
            print(f"   Run: python3 baseline_drift_correction.py --model {args.model}")
    
    if args.run in ("baseline","both"):
        # Disable batching for reasoning models (GPT-5, o1, o3) as they can't handle 30 questions at once
        use_batched = args.batched and not llm.cfg.model.startswith(('gpt-5', 'o1', 'o3'))
        
        if use_batched:
            base_ans = administer_batched(llm, BFI_S_ITEMS, persona=None, as_if=None, platform=None)
        else:
            if args.batched and llm.cfg.model.startswith(('gpt-5', 'o1', 'o3')):
                print(f"⚠️  Batching disabled for {llm.cfg.model} - reasoning models can't handle 30 questions at once")
                print("   Using individual question processing for better results")
            base_ans = administer(llm, BFI_S_ITEMS, persona=None, as_if=None, platform=None)
        base_m, base_d = score(BFI_S_ITEMS, base_ans)
        
        # Apply drift correction to baseline
        if corrections:
            base_m_corrected = apply_drift_correction(base_m, corrections)
            print(f"\n📊 Baseline scores (before/after drift correction):")
            for trait in "OCEAN":
                print(f"   {trait}: {base_m[trait]:.2f} → {base_m_corrected[trait]:.2f}")
            base_m = base_m_corrected
    else:
        base_m = {t: float('nan') for t in "OCEAN"}; base_d = base_m.copy()

    if args.run in ("induced","both"):
        # Build P2 only when we need it for induced mode
        if not p2:
            p2 = build_calibrated_p2(llm, as_if, platforms_used) if as_if else "You are high in OCEAN, low in N."
        
        # Disable batching for reasoning models (GPT-5, o1, o3) as they can't handle 30 questions at once
        use_batched = args.batched and not llm.cfg.model.startswith(('gpt-5', 'o1', 'o3'))
        
        if use_batched:
            ind_ans = administer_batched(llm, BFI_S_ITEMS, persona=p2, as_if=None, platform=None)
        else:
            ind_ans = administer(llm, BFI_S_ITEMS, persona=p2, as_if=None, platform=None)
        ind_m, ind_d = score(BFI_S_ITEMS, ind_ans)
        
        # Apply drift correction to induced
        if corrections:
            ind_m_corrected = apply_drift_correction(ind_m, corrections)
            print(f"\n📊 Induced scores (before/after drift correction):")
            for trait in "OCEAN":
                print(f"   {trait}: {ind_m[trait]:.2f} → {ind_m_corrected[trait]:.2f}")
            ind_m = ind_m_corrected
    else:
        ind_m = {t: float('nan') for t in "OCEAN"}; ind_d = ind_m.copy()

    df = compare_df(base_m, ind_m, base_d, ind_d, corrections)
    import datetime as dt
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(args.outdir, f"bfi_probe_{stamp}.csv")
    if p2:
        with open(os.path.join(args.outdir, f"p2_prompt_{stamp}.txt"), "w", encoding="utf-8") as f:
            f.write(p2)
    df.to_csv(csv_path, index=False)
    
    # Save detailed question-by-question results
    base_answers = base_ans if args.run in ("baseline","both") else {}
    induced_answers = ind_ans if args.run in ("induced","both") else {}
    save_detailed_results(base_answers, induced_answers, BFI_S_ITEMS, args.outdir, stamp)
    print("Results CSV:", csv_path)
    print(df.to_string(index=False))
if __name__ == "__main__":
    main()
