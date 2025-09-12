import numpy as np
from collections import Counter
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

    #Consecutive repetition
    count = 1
    for i in range(1, len(words)):
        if words[i] == words[i-1]:
            count += 1
            if count > 2:
                score += 1.0 * (count-2)
        else:
            count = 1

    #n-gram repetition
    for n in range(2, max_ngram+1):
        ngrams = [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]
        counts = Counter(ngrams)
        for ng, c in counts.items():
            if c > 2:
                score += (c-2) * n  #longer n-grams penalized harder

    return score


# Scoring function to compare transcripts after every filter and pick the best one
def score_transcript(result, baseline_len=None):
    segs = result.get("segments", [])
    avg_logprob = float(np.mean([s.get("avg_logprob", -10.0) for s in segs])) if segs else result.get("avg_logprob", -10.0)
    compression_ratio = result.get("compression_ratio", 1.0)
    text = result.get("text", "").strip()

    # Base score
    score = avg_logprob - 0.3 * compression_ratio

    # Too short penalty
    if baseline_len and len(text.split()) < 0.5 * baseline_len:
        score -= 1.0

    rep_penalty = repetition_score(text)
    score -= rep_penalty * 2.0

    # Compression-ratio hard rejection
    if compression_ratio < 0.25:
        score -= 4.0   #very heavy penalty

    return score


def compare_and_update(old_result, new_result, stage_name, semantic_weight=0.5):
    if old_result is None:
        return new_result

    old_text = old_result.get("text", "").strip()
    new_text = new_result.get("text", "").strip()
    baseline_len = len(old_text.split())

    old_score = score_transcript(old_result, baseline_len)
    new_score = score_transcript(new_result, baseline_len)

    # semantic similarity boost
    sim = semantic_similarity(new_text, old_text)

    combined_new = new_score + semantic_weight * sim
    combined_old = old_score + semantic_weight * 1.0 

    print(f"[COMPARE] {stage_name}: old={combined_old:.3f}, new={combined_new:.3f}, sim={sim:.2f}")
    print(f"[OLD TEXT] {old_text}")
    print(f"[NEW TEXT] {new_text}")

    if combined_new > combined_old:
        print("→ New transcript is better, replacing old one.\n")
        return new_result
    else:
        print("→ Old transcript is better, keeping it.\n")
        return old_result


def cleanup_repetition(text, max_repeat=3):
    words = text.split()
    cleaned = []
    count = 1
    for i, w in enumerate(words):
        if i > 0 and w == words[i-1]:
            count += 1
            if count > max_repeat:
                continue
        else:
            count = 1
        cleaned.append(w)
    return " ".join(cleaned)

