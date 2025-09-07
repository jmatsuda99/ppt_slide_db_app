
from typing import List, Tuple
import re

def basic_candidates(text: str, top_k: int = 8) -> List[str]:
    # very simple fallback: split words, count frequencies
    words = re.findall(r"[\w\-一-龥ぁ-んァ-ン]+", text or "")
    freq = {}
    for w in words:
        w = w.lower()
        if len(w) <= 1:
            continue
        freq[w] = freq.get(w, 0) + 1
    # sort by frequency
    return [w for w,_ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_k]]

def yake_candidates(text: str, top_k: int = 8) -> List[str]:
    try:
        import yake
        kw_extractor = yake.KeywordExtractor(lan="multilingual", n=1, top=top_k)
        kws = kw_extractor.extract_keywords(text or "")
        # kws: list of (keyword, score) lower score better
        kws_sorted = sorted(kws, key=lambda kv: kv[1])
        out = []
        for kw, score in kws_sorted:
            cleaned = kw.strip()
            if cleaned and cleaned not in out:
                out.append(cleaned)
        return out[:top_k]
    except Exception:
        return basic_candidates(text, top_k)

def suggest_keywords(text: str, top_k: int = 8) -> List[str]:
    cands = yake_candidates(text, top_k)
    if not cands:
        cands = basic_candidates(text, top_k)
    return cands
