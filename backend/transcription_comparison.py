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


#Remove excessive repetition at both word and phrase level.
#max_repeat: how many times a phrase can appear before being trimmed
#min_phrase_len: minimum length (words) for phrase-level deduplication

def cleanup_repetition(text, max_repeat=1, min_phrase_len=4):
    
    # First pass: consecutive word-level cleanup (like before)
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

    # Second pass: phrase-level cleanup
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    seen = {}
    final_sentences = []
    for s in sentences:
        word_count = len(s.split())
        if word_count >= min_phrase_len:
            seen[s] = seen.get(s, 0) + 1
            if seen[s] > max_repeat:
                continue  # skip repeated sentence
        final_sentences.append(s)
    return ". ".join(final_sentences) + "."


# Scoring function to compare transcripts after every filter and pick the best one
def score_transcript(result, baseline_len=None):
    segs = result.get("segments", [])
    avg_logprob = float(np.mean([s.get("avg_logprob", -10.0) for s in segs])) if segs else result.get("avg_logprob", -10.0)
    compression_ratio = result.get("compression_ratio", 1.0)
    text = result.get("text", "").strip()

    # Clean up repetition before scoring
    text = cleanup_repetition(text)

    # Base score
    score = avg_logprob - 0.3 * compression_ratio

    # Too short penalty
    if baseline_len and len(text.split()) < 0.5 * baseline_len:
        score -= 1.0

    # Strong repetition penalty
    rep_penalty = repetition_score(text)
    score -= rep_penalty * 4.0   #make this much stronger

    # Hard reject if extremely repetitive
    if rep_penalty > 8:
        score -= 20.0

    # Compression-ratio hard rejection
    if compression_ratio < 0.25:
        score -= 5.0

    return score, text  # return cleaned text too


def compare_and_update(old_result, new_result, stage_name, semantic_weight=0.5):
    if old_result is None:
        return new_result

    old_text = old_result.get("text", "").strip()
    baseline_len = len(old_text.split())

    old_score, old_clean = score_transcript(old_result, baseline_len)
    new_score, new_clean = score_transcript(new_result, baseline_len)

    # semantic similarity boost only if repetition is low
    sim = semantic_similarity(new_clean, old_clean)
    if repetition_score(new_clean) < 3:
        combined_new = new_score + semantic_weight * sim
    else:
        combined_new = new_score  # don’t boost repetitive junk

    combined_old = old_score + semantic_weight * 1.0

    print(f"[COMPARE] {stage_name}: old={combined_old:.3f}, new={combined_new:.3f}, sim={sim:.2f}")
    print(f"[OLD TEXT] {old_clean}")
    print(f"[NEW TEXT] {new_clean}")

    if combined_new > combined_old:
        print("→ New transcript is better, replacing old one.\n")
        new_result["text"] = new_clean
        return new_result
    else:
        print("→ Old transcript is better, keeping it.\n")
        old_result["text"] = old_clean
        return old_result