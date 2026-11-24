# Hugging Face Transformers
"""
Hugging Face `transformers` is the standard library for downloading and running open-weight
models (Llama, Qwen, Gemma, Mistral, SmolLM, ...). Three objects matter:

- TOKENIZER: text <-> integer ids (`AutoTokenizer`). Models never see characters, only ids.
- MODEL: ids -> logits (`AutoModelForCausalLM`). A causal LM predicts the NEXT token.
- `model.generate(...)`: the decoding loop (pick a token, append it, repeat).
- `pipeline("text-generation", model=...)`: all three wrapped in one call. Great for demos.

Tokenization = subword units. Byte-pair encoding (BPE) starts from characters and repeatedly
merges the most frequent adjacent pair, so common words become one token and rare words split
into pieces. We build a tiny BPE below so the idea is concrete.

Decoding = choosing the next token from the model's probabilities:
- greedy: argmax (deterministic, repetitive)
- temperature: divide logits by T (T<1 sharper, T>1 flatter), then sample
- top-k: keep only the k most likely tokens
- top-p (nucleus): keep the smallest set whose probability mass reaches p

Picking a model from the Hub: filter by task, size (0.5B-8B runs on a laptop), license, and
whether it is an `-Instruct` / chat-tuned variant. Weights are cached under `HF_HOME`
(default `~/.cache/huggingface`). Prefer `safetensors` weights.

Devices: `cuda` (NVIDIA GPU), `mps` (Apple Silicon), else `cpu`. Use `dtype=torch.bfloat16`
on GPU to halve memory; CPU is fine for sub-1B models.

SAFE BY DEFAULT: this lesson downloads nothing. The real `pipeline(...)` call only runs if you
export `HF_RUN=1` (it downloads a ~270 MB model the first time).
    uv sync --group ml-torch         # optional: torch + transformers + peft + accelerate
    HF_RUN=1 uv run python -m t06_applied_ml_llm.m_10_huggingface_transformers

Run the offline demo: uv run python -m t06_applied_ml_llm.m_10_huggingface_transformers
"""

import importlib.metadata
import importlib.util
import os
from collections import Counter

import numpy as np

HF_MODEL = os.getenv("HF_MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")


def installed(pkg: str) -> str | None:
    """Return the version of an optional package, or None. Never imports it (imports are slow)."""
    if importlib.util.find_spec(pkg) is None:
        return None
    return importlib.metadata.version(pkg)


# Example: choose a device
def pick_device(cuda: bool, mps: bool) -> str:
    """Pure function so it is testable. Real code: torch.cuda.is_available() etc."""
    if cuda:
        return "cuda"
    return "mps" if mps else "cpu"


# Example: a toy byte-pair-encoding trainer
def train_bpe(corpus: list[str], num_merges: int) -> list[tuple[str, str]]:
    words: Counter[tuple[str, ...]] = Counter(tuple(w) for text in corpus for w in text.split())
    merges: list[tuple[str, str]] = []
    for _ in range(num_merges):
        pairs: Counter[tuple[str, str]] = Counter()
        for word, freq in words.items():
            for pair in zip(word, word[1:], strict=False):
                pairs[pair] += freq
        if not pairs:
            break
        best_count = max(pairs.values())
        best = min(p for p, c in pairs.items() if c == best_count)  # ties: smallest pair
        merges.append(best)
        words = Counter({_merge(word, best): freq for word, freq in words.items()})
    return merges


def _merge(symbols: tuple[str, ...], pair: tuple[str, str]) -> tuple[str, ...]:
    out: list[str] = []
    i = 0
    while i < len(symbols):
        if i + 1 < len(symbols) and (symbols[i], symbols[i + 1]) == pair:
            out.append(symbols[i] + symbols[i + 1])
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return tuple(out)


def bpe_encode(word: str, merges: list[tuple[str, str]]) -> list[str]:
    symbols = tuple(word)
    for pair in merges:  # apply merges in the order they were learned
        symbols = _merge(symbols, pair)
    return list(symbols)


# Example: decoding strategies on a fake next-token distribution
def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    z = logits / temperature
    z = z - z.max()  # numerical stability
    e = np.exp(z)
    return e / e.sum()


def top_k_top_p(
    probs: np.ndarray, top_k: int | None = None, top_p: float | None = None
) -> np.ndarray:
    """Top-k first, renormalize, then nucleus (top-p), renormalize again."""
    p = probs.astype(float).copy()
    if top_k is not None and top_k < len(p):
        p[np.argsort(-p, kind="stable")[top_k:]] = 0.0
        p /= p.sum()
    if top_p is not None:
        order = np.argsort(-p, kind="stable")
        cum = np.cumsum(p[order])
        cutoff = int(np.searchsorted(cum, top_p - 1e-9)) + 1  # smallest set reaching mass p
        p[order[cutoff:]] = 0.0
        p /= p.sum()
    return p


def sample(probs: np.ndarray, rng: np.random.Generator) -> int:
    return int(rng.choice(len(probs), p=probs))


# Example: the real thing, guarded
def run_real_pipeline(prompt: str) -> str:
    """Downloads HF_MODEL on first use. Only called when HF_RUN=1."""
    from transformers import pipeline  # imported lazily: slow and optional

    generator = pipeline("text-generation", model=HF_MODEL)  # device_map="auto" with accelerate
    out = generator(prompt, max_new_tokens=40, do_sample=False)
    return out[0]["generated_text"]


"""
Common mistakes
- Forgetting the chat template: instruct models expect `tokenizer.apply_chat_template(messages,
  add_generation_prompt=True)`, not raw text. Wrong template = noticeably worse answers.
- Mixing tokenizer and model from different checkpoints (ids will not line up).
- Loading a 7B model in float32 on a laptop: ~28 GB. Use bfloat16 or a smaller/quantized model.
- Calling `generate` in training mode or without `torch.no_grad()` / `model.eval()`.
- Using `max_length` (prompt + output) when you meant `max_new_tokens`.
- Assuming one word = one token: budget ~1.3 tokens per English word, more for code and
  non-English text.

Production notes
- Pin the model revision (`revision="<commit sha>"`) so upstream changes cannot alter behaviour.
- In CI and containers set `HF_HUB_OFFLINE=1` and bake the weights into the image.
- transformers is great for prototyping and fine-tuning; for serving traffic prefer a purpose-
  built engine (m_11 Ollama locally, m_12 vLLM on GPUs) which batches requests for you.
- Always check the model license before shipping (Llama, Gemma and Qwen licenses differ).
"""

if __name__ == "__main__":
    print("transformers:", installed("transformers") or "not installed (uv sync --group ml-torch)")
    print("torch:", installed("torch") or "not installed")
    print("device pick (no gpu, no mps):", pick_device(cuda=False, mps=False))

    # BPE: frequent pairs become single tokens
    corpus = ["low low low lower lowest", "new newer newest"]
    merges = train_bpe(corpus, num_merges=6)
    print("learned merges:", merges)
    print("encode 'lowest' ->", bpe_encode("lowest", merges))
    print("encode 'slower' ->", bpe_encode("slower", merges), "(unseen word falls back to pieces)")

    # Decoding on a fake 6-token vocabulary
    vocab = ["the", "cat", "sat", "mat", "dog", "ran"]
    logits = np.array([3.0, 2.0, 1.5, 1.0, 0.5, 0.1])
    rng = np.random.default_rng(0)
    probs = softmax(logits, temperature=0.7)
    print("probs T=0.7:", np.round(probs, 3))
    filtered = top_k_top_p(probs, top_k=4, top_p=0.9)
    print("after top_k=4, top_p=0.9:", np.round(filtered, 3))
    print("greedy token:", vocab[int(np.argmax(probs))])
    print("sampled tokens:", [vocab[sample(filtered, rng)] for _ in range(5)])

    if os.getenv("HF_RUN") == "1" and installed("transformers"):
        print(run_real_pipeline("The capital of France is"))
    else:
        print("HF_RUN != 1: skipping real model download. Set HF_RUN=1 to try pipeline().")
