import numpy as np
from collections import Counter
import re
from sentence_transformers import SentenceTransformer, util

semantic_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def semantic_similarity(text1, text2):
    emb1 = semantic_model.encode(text1, convert_to_tensor=True)
    emb2 = semantic_model.encode(text2, convert_to_tensor=True)
    return float(util.cos_sim(emb1, emb2))


#Return a penalty if text is highly repetitive
def repetition_score(text: str, max_ngram=4) -> float:
    words = text.strip().split()
    if len(words) < 4:
        return 0.0

    score = 0.0
    count = 1
    for i in range(1, len(words)):
        if words[i] == words[i-1]:
            count += 1
            if count > 2:
                score += 1.0 * (count-2)
        else:
            count = 1

    for n in range(2, max_ngram+1):
        ngrams = [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]
        counts = Counter(ngrams)
        for ng, c in counts.items():
            if c > 2:
                score += (c-2) * n
   
    return score


def word_diversity(text):
    words = text.strip().split()
    if not words: return 0
    return len(set(words)) / len(words)


def alpha_ratio(text):
    letters = len(re.findall(r"[a-zA-ZäöüßÄÖÜ]", text))
    return letters / max(1, len(text))


def looks_like_nonsense(text, repeat_thr=8):
    words = text.split()
    counts = Counter(words)
    return any(c > repeat_thr for c in counts.values())



#Remove excessive repetition at both word and phrase level.
#max_repeat: how many times a phrase can appear before being trimmed
#min_phrase_len: minimum length (words) for phrase-level deduplication
def cleanup_repetition(text, max_repeat=1, min_phrase_len=4):
    words = text.split()
    cleaned_words = []
    count = 1
    for i, w in enumerate(words):
        if i > 0 and w == words[i-1]:
            count += 1
            if count > max_repeat:
                continue
        else:
            count = 1
        cleaned_words.append(w)
    text = " ".join(cleaned_words)

    sentences = [s.strip() for s in text.split(".") if s.strip()]
    seen = {}
    final_sentences = []
    for s in sentences:
        word_count = len(s.split())
        if word_count >= min_phrase_len:
            seen[s] = seen.get(s, 0) + 1
            if seen[s] > max_repeat:
                continue
        final_sentences.append(s)
    
    return ". ".join(final_sentences) + "."


# ------------------------------
# Transcript scoring
# ------------------------------

# Scoring function to compare transcripts after every filter and pick the best one
def score_transcript(result, baseline_len=None):
    segs = result.get("segments", [])
    avg_logprob = float(np.mean([s.get("avg_logprob", -10.0) for s in segs])) if segs else result.get("avg_logprob", -10.0)
    compression_ratio = result.get("compression_ratio", 1.0)
    text = result.get("text", "").strip()

    text = cleanup_repetition(text)

    score = avg_logprob - 0.3 * compression_ratio

    if baseline_len and len(text.split()) < 0.5 * baseline_len:
        score -= 1.0

    rep_penalty = repetition_score(text)
    score -= rep_penalty * 4.0
    if rep_penalty > 8:
        score -= 20.0

    div = word_diversity(text)
    if div < 0.2:
        score -= 15.0  # reject low-diversity junk

    ar = alpha_ratio(text)
    if ar < 0.5:
        score -= 20.0  # reject mostly non-letters

    if looks_like_nonsense(text):
        score -= 50.0  # outright reject nonsense

    if compression_ratio < 0.25:
        score -= 5.0

    return score, text


# ------------------------------
# Transcript comparison
# ------------------------------

def compare_and_update(old_result, new_result, stage_name, semantic_weight=2.0):
    if old_result is None:
        return new_result

    old_text = old_result.get("text", "").strip()
    baseline_len = len(old_text.split())

    old_score, old_clean = score_transcript(old_result, baseline_len)
    new_score, new_clean = score_transcript(new_result, baseline_len)

    if looks_like_nonsense(new_clean):
            print(f"[COMPARE] {stage_name}: new transcript looks like nonsense, rejecting.\n")
            old_result["text"] = old_clean
            return old_result

    sim = semantic_similarity(new_clean, old_clean)

    # Only boost if new text is not repetitive
    if repetition_score(new_clean) < 3:
        combined_new = new_score + semantic_weight * sim
    else:
        combined_new = new_score

    combined_old = old_score + semantic_weight * 1.0

    print(f"[COMPARE] {stage_name}: old={combined_old:.3f}, new={combined_new:.3f}, sim={sim:.2f}")
    print(f"[OLD TEXT] {old_clean[:200]}...")
    print(f"[NEW TEXT] {new_clean[:200]}...")

    if combined_new > combined_old:
        print("→ New transcript is better, replacing old one.\n")
        new_result["text"] = new_clean
        return new_result
    else:
        print("→ Old transcript is better, keeping it.\n")
        old_result["text"] = old_clean
        return old_result