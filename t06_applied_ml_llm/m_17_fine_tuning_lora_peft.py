# Fine-Tuning with LoRA and PEFT
"""
FINE-TUNING updates a model's weights on your examples. It is the LAST tool to reach for.

When to use what
- PROMPTING first: instructions, few-shot examples, structured output. Minutes to iterate.
- RAG (m_14) when the problem is KNOWLEDGE: private, changing, or citable facts. Fine-tuning is
  a poor way to inject facts (the model still hallucinates them, and updates need retraining).
- FINE-TUNING when the problem is BEHAVIOUR: consistent tone/format, a narrow task done
  reliably by a SMALL cheap model (distillation from a big one), lower latency/cost at volume,
  or a style prompts cannot pin down. You need hundreds-thousands of clean examples and evals
  (m_16) to prove it beat the prompt baseline.

Dataset formats (JSONL, one example per line)
- chat/SFT:     {"messages": [{"role": "system"|"user"|"assistant", "content": "..."}]}
- instruction:  {"instruction": "...", "input": "...", "output": "..."}      (Alpaca style)
- preference:   {"prompt": "...", "chosen": "...", "rejected": "..."}          (DPO/RLHF-style)
Quality beats quantity: duplicates, wrong labels and inconsistent style are learned faithfully.

LoRA (Low-Rank Adaptation) freezes the pretrained weight W (d_out x d_in) and learns a small
update  dW = (alpha / r) * B @ A  with B (d_out x r) and A (r x d_in), r << d.
- Trainable params per matrix: r * (d_in + d_out) instead of d_in * d_out (often < 1% overall).
- B starts at zero, so training starts from the unchanged base model.
- Adapters are small files (MBs); swap them per task/tenant or MERGE them into W for serving
  (W' = W + dW, zero extra latency). vLLM can serve many adapters on one base (m_12).
QLoRA = the frozen base is loaded in 4-bit (NF4) while LoRA adapters train in bf16: a 7-8B
model fine-tunes on a single 24 GB GPU.

PEFT (Hugging Face) implements this:
    cfg = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                     lora_dropout=0.05, task_type="CAUSAL_LM")
    model = get_peft_model(base_model, cfg); model.print_trainable_parameters()
then train with transformers `Trainer` (or TRL's `SFTTrainer`).

This lesson demonstrates the math with numpy and builds the PEFT config object. REAL training
only runs with `LORA_RUN=1` (needs `uv sync --group ml-torch`, downloads a small model).
Run: uv run python -m t06_applied_ml_llm.m_17_fine_tuning_lora_peft
"""

import importlib.util
import json
import os
import tempfile

import numpy as np

LORA_BASE_MODEL = os.getenv("LORA_BASE_MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")


# Example: parameter-count arithmetic
def lora_params(d_in: int, d_out: int, r: int) -> int:
    return r * (d_in + d_out)


def trainable_fraction(layer_shapes: list[tuple[int, int]], r: int) -> float:
    full = sum(d_in * d_out for d_in, d_out in layer_shapes)
    return sum(lora_params(i, o, r) for i, o in layer_shapes) / full


def qlora_memory_gb(
    params_billion: float, adapter_params_million: float, base_bits: int = 4
) -> float:
    base = params_billion * base_bits / 8  # frozen quantized weights
    # adapter: bf16 weights (2B) + grads (2B) + Adam moments in fp32 (8B) = 12 bytes per param
    adapter = adapter_params_million * 1e6 * 12 / 1024**3
    return base + adapter  # + activations/KV (depends on batch size and sequence length)


# Example: LoRA math in numpy
def lora_forward(
    x: np.ndarray, w: np.ndarray, a: np.ndarray, b: np.ndarray, alpha: float
) -> np.ndarray:
    r = a.shape[0]
    return x @ w.T + (alpha / r) * (x @ a.T) @ b.T  # base path + low-rank path


def merge(w: np.ndarray, a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    return w + (alpha / a.shape[0]) * b @ a


def low_rank_error(delta: np.ndarray, rank: int) -> float:
    """Relative error of the best rank-`rank` approximation of a weight update (via SVD)."""
    u, s, vt = np.linalg.svd(delta, full_matrices=False)
    approx = (u[:, :rank] * s[:rank]) @ vt[:rank]
    return float(np.linalg.norm(delta - approx) / np.linalg.norm(delta))


# Example: dataset validation
def validate_chat_example(example: dict) -> list[str]:
    errors: list[str] = []
    messages = example.get("messages")
    if not isinstance(messages, list) or not messages:
        return ["missing non-empty 'messages' list"]
    for i, m in enumerate(messages):
        if m.get("role") not in {"system", "user", "assistant"}:
            errors.append(f"message {i}: bad role {m.get('role')!r}")
        if not str(m.get("content", "")).strip():
            errors.append(f"message {i}: empty content")
    if messages[-1].get("role") != "assistant":
        errors.append("last message must be from the assistant (the target to learn)")
    return errors


# Example: PEFT config (imported lazily; peft pulls in torch and is optional)
def make_peft_config(r: int = 16, alpha: int = 32):
    if importlib.util.find_spec("peft") is None:
        return None
    from peft import LoraConfig

    return LoraConfig(
        r=r,
        lora_alpha=alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        task_type="CAUSAL_LM",
    )


def fine_tune(model, encode, rows: list[dict], out_dir: str) -> None:
    """Wrap `model` with LoRA adapters and train on `rows` (needs torch + transformers + peft)."""
    import torch
    from peft import get_peft_model
    from transformers import Trainer, TrainingArguments

    class Examples(torch.utils.data.Dataset):
        def __len__(self) -> int:
            return len(rows)

        def __getitem__(self, i: int) -> dict:
            ids = torch.tensor(encode(rows[i]))
            return {"input_ids": ids, "labels": ids.clone()}  # next-token loss on the full text

    def collate(
        batch: list[dict],
    ) -> dict:  # pad to the longest example; -100 = ignored by the loss
        n = max(len(b["input_ids"]) for b in batch)
        ids = torch.stack(
            [torch.nn.functional.pad(b["input_ids"], (0, n - len(b["input_ids"]))) for b in batch]
        )
        labels = torch.stack(
            [
                torch.nn.functional.pad(b["labels"], (0, n - len(b["labels"])), value=-100)
                for b in batch
            ]
        )
        return {"input_ids": ids, "labels": labels}

    peft_model = get_peft_model(model, make_peft_config())
    peft_model.print_trainable_parameters()
    args = TrainingArguments(
        out_dir,
        per_device_train_batch_size=2,
        num_train_epochs=1,
        learning_rate=2e-4,
        report_to="none",
    )
    Trainer(model=peft_model, args=args, train_dataset=Examples(), data_collator=collate).train()
    peft_model.save_pretrained(out_dir)  # saves only the adapter (a few MB)
    # Later: PeftModel.from_pretrained(base, out_dir).merge_and_unload() for serving


def train_lora(rows: list[dict], out_dir: str) -> None:
    """Real fine-tuning of LORA_BASE_MODEL. Only called when LORA_RUN=1 (downloads the model)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(LORA_BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(LORA_BASE_MODEL, dtype=torch.bfloat16)

    def encode(ex: dict) -> list[int]:
        return tok.apply_chat_template(ex["messages"], tokenize=True, return_dict=True)["input_ids"]

    fine_tune(model, encode, rows, out_dir)


"""
Common mistakes
- Fine-tuning to teach facts. Use RAG; fine-tune for behaviour.
- No baseline: always compare against a well-prompted base model on a held-out eval set (m_16).
- Training on the test set, or on duplicated/near-duplicate examples.
- Too high a learning rate or too many epochs: the model memorizes and forgets general skills
  (catastrophic forgetting). LoRA lr ~1e-4 to 2e-4 is a common start, 1-3 epochs.
- Forgetting the chat template: train with the SAME template you will serve with.
- Tiny rank for a hard task (r=4) or huge rank for a simple one; start at r=8-16 and measure.

Production notes
- Version datasets and adapters together; record base model revision, hyperparameters, and eval scores.
- Merge for single-purpose serving; keep adapters separate for multi-tenant serving.
- Re-run the whole eval suite after every base-model upgrade: adapters are tied to their base.
- Check licences and data rights for both the base model and the training data.
"""

if __name__ == "__main__":
    rng = np.random.default_rng(0)

    # A 7B-like model: hidden 4096, 32 layers, adapters on q,k,v,o (all 4096 x 4096)
    shapes = [(4096, 4096)] * 4 * 32
    total = sum(lora_params(i, o, 16) for i, o in shapes)
    print(
        f"r=16 LoRA on a 7B-like model: {total / 1e6:.1f}M trainable params "
        f"({trainable_fraction(shapes, 16):.2%} of the targeted weights, {total / 7e9:.2%} of the whole model)"
    )
    print(
        f"QLoRA memory estimate (7B, 4-bit base): {qlora_memory_gb(7, total / 1e6):.1f} GB + activations"
    )

    # LoRA update on tiny tensors: B starts at zero, so the model is unchanged at step 0
    d, r, alpha = 32, 4, 8
    w = rng.normal(size=(d, d))
    a, b = rng.normal(scale=0.1, size=(r, d)), np.zeros((d, r))
    x = rng.normal(size=(3, d))
    print(
        "step 0: LoRA output equals base output:",
        np.allclose(lora_forward(x, w, a, b, alpha), x @ w.T),
    )
    b = rng.normal(scale=0.1, size=(d, r))  # pretend training moved B
    print(
        "after 'training': merged weights match the two-path forward:",
        np.allclose(x @ merge(w, a, b, alpha).T, lora_forward(x, w, a, b, alpha)),
    )

    # Why low rank works: real weight updates are approximately low-rank
    delta = rng.normal(size=(64, 4)) @ rng.normal(size=(4, 64)) + 0.05 * rng.normal(size=(64, 64))
    print("relative error of the best rank-r approximation of a weight update:")
    for rank in (1, 2, 4, 8, 16):
        print(
            f"  r={rank:>2}: error {low_rank_error(delta, rank):.3f}, params {lora_params(64, 64, rank)} vs full {64 * 64}"
        )

    good = {
        "messages": [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]
    }
    bad = {"messages": [{"role": "robot", "content": " "}]}
    print("validate good:", validate_chat_example(good))
    print("validate bad :", validate_chat_example(bad))
    print("one training line:", json.dumps(good))

    cfg = make_peft_config()
    if cfg is None:
        print("peft not installed (uv sync --group ml-torch): skipping LoraConfig demo")
    else:
        print(
            f"peft LoraConfig: r={cfg.r}, alpha={cfg.lora_alpha}, scaling={cfg.lora_alpha / cfg.r}, "
            f"targets={sorted(cfg.target_modules)}"
        )
    if os.getenv("LORA_RUN") == "1" and cfg is not None:
        with tempfile.TemporaryDirectory() as out:
            train_lora([good] * 4, out)  # 4 identical toy examples: just proves the plumbing
    else:
        print("LORA_RUN != 1: not training (set LORA_RUN=1 to fine-tune a small model for real).")
