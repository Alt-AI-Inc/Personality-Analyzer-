
# bfi_probe_patched.py — Robust JSON-mode + retries for gen_keywords
import argparse, json, os, re, time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

try:
    from openai import OpenAI
    _USE_NEW = True
except Exception:
    import openai
    _USE_NEW = False

BFI_S_ITEMS = [
    {"id":"E1","text":"You are talkative.","trait":"E","reverse":False},
    {"id":"E2","text":"You are reserved.","trait":"E","reverse":True},
    {"id":"E3","text":"You are outgoing, sociable.","trait":"E","reverse":False},
    {"id":"A1","text":"You are considerate and kind to almost everyone.","trait":"A","reverse":False},
    {"id":"A2","text":"You tend to find fault with others.","trait":"A","reverse":True},
    {"id":"A3","text":"You are helpful and unselfish with others.","trait":"A","reverse":False},
    {"id":"C1","text":"You do a thorough job.","trait":"C","reverse":False},
    {"id":"C2","text":"You can be somewhat careless.","trait":"C","reverse":True},
    {"id":"C3","text":"You are reliable and get things done.","trait":"C","reverse":False},
    {"id":"N1","text":"You are relaxed, handle stress well.","trait":"N","reverse":True},
    {"id":"N2","text":"You get nervous easily.","trait":"N","reverse":False},
    {"id":"N3","text":"You worry a lot.","trait":"N","reverse":False},
    {"id":"O1","text":"You have an active imagination.","trait":"O","reverse":False},
    {"id":"O2","text":"You are original, come up with new ideas.","trait":"O","reverse":False},
    {"id":"O3","text":"You have few artistic interests.","trait":"O","reverse":True},
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
        if _USE_NEW:
            r = self.cli.chat.completions.create(
                model=self.cfg.model,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                temperature=temp,
                max_tokens=mt,
            )
            out = r.choices[0].message.content.strip()
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
    def chat_json(self, system: str, user: str, *, max_tokens: int=512, temperature: float=0.0) -> str:
        if _USE_NEW:
            r = self.cli.chat.completions.create(
                model=self.cfg.model,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type":"json_object"},
            )
            out = r.choices[0].message.content.strip()
        else:
            sys2 = system + " Respond with STRICT JSON only. No prose, no code fences."
            out = self.chat(sys2, user, max_tokens=max_tokens, temperature=temperature)
        return out


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
    sys = "You are a psychology-savvy prompt engineer."
    user = (
        "For each Big Five trait (O,C,E,A,N), list 6-10 clear adjectives (no phrases) matching these target levels. "
        "Return STRICT JSON with keys O,C,E,A,N each mapping to a list of adjectives. "
        f"Targets: {json.dumps(tgt)}"
    )
    #print(user)
    txt = llm.chat_json(sys, user, max_tokens=600, temperature=0.0)
    try:
        obj = json.loads(txt)
    except Exception:
        try:
            obj = _json_repair(txt)
        except Exception:
            txt2 = llm.chat_json(sys, "STRICT JSON ONLY. NO commentary. " + user, max_tokens=600, temperature=0.0)
            try:
                obj = json.loads(txt2)
            except Exception:
                obj = _json_repair(txt2)
    #print(obj)
    clean = {}
    for k in ["O","C","E","A","N"]:
        vals = obj.get(k, [])
        if isinstance(vals, str): vals = [vals]
        vals = [str(w).strip().lower().split()[0] for w in vals if str(w).strip()]
        seen=set(); uniq=[]
        for w in vals:
            if w not in seen:
                seen.add(w); uniq.append(w)
        clean[k] = uniq[:10]
    #print(clean)
    return clean

def gen_portrait(llm: LLM, seed: str, kw: Dict[str,List[str]]) -> str:
    sys = "You write concise persona prompts about how someone SPEAKS (cadence, hedging, directness, enthusiasm, vocabulary)."
    user = "Seed line: " + seed + "\nKeywords per trait: " + json.dumps(kw) + "\nWrite 5–7 short sentences describing speech patterns only. No biography. Return sentences only."
    print("User persona prompt",user)

    return llm.chat(sys, user, max_tokens=400, temperature=0.2)

def build_p2(llm: LLM, tgt: Dict[str,str]) -> str:
    seed = naive_line(tgt)
    kw = gen_keywords(llm, tgt)
    portrait = gen_portrait(llm, seed, kw)
    print("User potrait",portrait)
    return f"PERSONALITY PROMPT (P²)\n{seed}\nStyle portrait:\n{portrait}\n"

def item_prompt(text: str) -> str:
    return ("Rate how accurately the statement describes you.\n"
            "Choose exactly one letter:\nA=Very Accurate, B=Accurate, C=Neither, D=Inaccurate, E=Very Inaccurate\n\n"
            f"Statement: {text}\n\n"
            "Respond with a single letter (A/B/C/D/E) and nothing else.")

def administer(llm, items, persona=None, as_if=None):
    system = "You are completing a standardized personality inventory. Answer honestly in first person. Output only A/B/C/D/E."
    if persona: system = persona + "\n\n" + system
    if as_if: system = "Answer AS IF you are the author of these writing samples.\nSAMPLES:\n" + as_if + "\n\n" + system
    out={}
    for it in items:
        resp = llm.chat(system, item_prompt(it["text"]), max_tokens=8, temperature=0.0)
        m = re.search(r"[A-E]", resp, re.I)
        out[it["id"]] = (m.group(0).upper() if m else "C")
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

def compare_df(base_m, ind_m, base_d, ind_d):
    rows=[]
    for t in "OCEAN":
        rows.append({
            "Trait": t,
            "Baseline": round(base_m.get(t, float('nan')),3),
            "Induced": round(ind_m.get(t, float('nan')),3),
            "Δ (Induced - Baseline)": round(ind_m.get(t,0)-base_m.get(t,0),3),
            "Dispersion (Base)": round(base_d.get(t, float('nan')),3),
            "Dispersion (Induced)": round(ind_d.get(t, float('nan')),3),
        })
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, default="gpt-4o-mini")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--run", choices=["baseline","induced","both"], default="both")
    ap.add_argument("--target", type=str, default="O:high,C:high,E:high,A:high,N:low")
    ap.add_argument("--samples", type=str, default=None)
    ap.add_argument("--outdir", type=str, default="results")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    cfg = LLMConfig(model=args.model, temperature=args.temperature, max_tokens=128)
    llm = LLM(cfg, debug=args.debug)
    os.makedirs(args.outdir, exist_ok=True)
    tgt = parse_target(args.target)
    p2 = build_p2(llm, tgt)
    as_if = None
    if args.samples and os.path.exists(args.samples):
        with open(args.samples, "r", encoding="utf-8") as f:
            as_if = f.read().strip()
    if args.run in ("baseline","both"):
        base_ans = administer(llm, BFI_S_ITEMS, persona=None, as_if=as_if)
        base_m, base_d = score(BFI_S_ITEMS, base_ans)
    else:
        base_m = {t: float('nan') for t in "OCEAN"}; base_d = base_m.copy()
    if args.run in ("induced","both"):
        ind_ans = administer(llm, BFI_S_ITEMS, persona=p2, as_if=as_if)
        ind_m, ind_d = score(BFI_S_ITEMS, ind_ans)
    else:
        ind_m = {t: float('nan') for t in "OCEAN"}; ind_d = ind_m.copy()
    df = compare_df(base_m, ind_m, base_d, ind_d)
    import datetime as dt
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(args.outdir, f"bfi_probe_{stamp}.csv")
    with open(os.path.join(args.outdir, f"p2_prompt_{stamp}.txt"), "w", encoding="utf-8") as f:
        f.write(p2)
    df.to_csv(csv_path, index=False)
    print("Results CSV:", csv_path)
    print(df.to_string(index=False))
if __name__ == "__main__":
    main()
