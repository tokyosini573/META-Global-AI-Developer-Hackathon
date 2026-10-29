"""Muse Glimmer on Modal: download, QLoRA training and evaluation.

    .venv/bin/modal run --detach engine/distill/glimmer_modal.py::download
    .venv/bin/modal run --detach engine/distill/glimmer_modal.py::train --run r1
    .venv/bin/modal run --detach engine/distill/glimmer_modal.py::evaluate --run r1
    .venv/bin/modal run --detach engine/distill/glimmer_modal.py::decide_table --name kindred   # engine table

Weights live in the `glimmer-weights` volume; data, adapters and eval results in `glimmer-runs`.
"""

import modal

MODEL = "meta-models/Muse-Glimmer-30B"
REVISION = "cec94fcfd6512f2cfe708138c32533b346ea4f69"   # main on 2026-10-30
WEIGHTS = "/weights"
RUNS = "/runs"

app = modal.App("rehearsal-glimmer")
weights = modal.Volume.from_name("glimmer-weights", create_if_missing=True)
runs = modal.Volume.from_name("glimmer-runs", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.10.0", "torchvision==0.25.0", "transformers==5.22.0", "peft==0.21.2", "bitsandbytes==0.50.2",
                 "accelerate", "huggingface_hub[hf_xet]", "pillow", "numpy")
    .env({"HF_HOME": WEIGHTS + "/hf"})
)


@app.function(image=image, volumes={WEIGHTS: weights}, timeout=3 * 3600, cpu=4)
def download():
    from huggingface_hub import snapshot_download
    path = snapshot_download(MODEL, revision=REVISION, local_dir=f"{WEIGHTS}/glimmer")
    weights.commit()
    print("downloaded to", path)


# ---- shared helpers (run inside the GPU container) ----------------------------------

GPU = "H100"
TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj")


def load(adapter=None, train=False):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

    path = f"{WEIGHTS}/glimmer"
    processor = AutoProcessor.from_pretrained(path)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_use_double_quant=True, bnb_4bit_quant_storage=torch.bfloat16)
    model = AutoModelForImageTextToText.from_pretrained(path, quantization_config=bnb, dtype=torch.bfloat16,
                                                        device_map={"": 0})
    if train:
        from peft import LoraConfig, get_peft_model
        # Not prepare_model_for_kbit_training: it casts the norms to float32, and the vision
        # tower then fails on bfloat16 inputs. Everything stays bfloat16; only LoRA trains.
        for prm in model.parameters():
            prm.requires_grad = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
        names = sorted({n for n, _ in model.named_modules()
                        if n.split(".")[-1] in TARGETS and "vision" not in n and "visual" not in n})
        model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                                                 target_modules=names))
        model.print_trainable_parameters()
    elif adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    return processor, model


def read(split):
    import json
    return [json.loads(x) for x in open(f"{RUNS}/data/{split}.jsonl")]


def screen(name, cache={}):
    from PIL import Image
    if name not in cache:
        cache[name] = Image.open(f"{RUNS}/data/screens/{name}").convert("RGB")
    return cache[name]


def encode(processor, rec):
    """input_ids etc. for one training example, with labels only on the answer."""
    import torch
    full = processor.apply_chat_template(rec["messages"], tokenize=False)
    prompt = processor.apply_chat_template(rec["messages"][:-1], tokenize=False, add_generation_prompt=True)
    img = [screen(rec["image"])]
    enc = processor(text=[full], images=[img], return_tensors="pt")
    n_prompt = processor(text=[prompt], images=[img], return_tensors="pt")["input_ids"].shape[1]
    labels = enc["input_ids"].clone()
    labels[:, :n_prompt] = -100
    enc["labels"] = labels
    return {k: v[0] if k in ("input_ids", "attention_mask", "labels") else v for k, v in enc.items()}


def collate(processor, batch):
    import torch
    pad = processor.tokenizer.pad_token_id
    n = max(b["input_ids"].shape[0] for b in batch)
    out = {"input_ids": torch.full((len(batch), n), pad), "attention_mask": torch.zeros(len(batch), n, dtype=torch.long),
           "labels": torch.full((len(batch), n), -100)}
    for i, b in enumerate(batch):                       # right padding for training
        k = b["input_ids"].shape[0]
        out["input_ids"][i, :k] = b["input_ids"]
        out["attention_mask"][i, :k] = b["attention_mask"]
        out["labels"][i, :k] = b["labels"]
    for key in batch[0]:
        if key not in out:
            out[key] = torch.cat([b[key] for b in batch])  # pixel values and image grid sizes stack per image
    return out


def to_dev(batch, model):
    import torch
    return {k: v.to(model.device, torch.bfloat16 if v.is_floating_point() else None) for k, v in batch.items()}


PREFIX = " to=user<|message|>"   # skip the reasoning channel: answer the user directly


def generate(processor, model, recs, batch=16, max_new=160):
    import json
    import time
    import torch
    processor.tokenizer.padding_side = "left"
    outs, t0, tokens = [], time.time(), 0
    for i in range(0, len(recs), batch):
        chunk = recs[i:i + batch]
        texts = [processor.apply_chat_template(r["messages"][:2], tokenize=False, add_generation_prompt=True) + PREFIX
                 for r in chunk]
        enc = to_dev(processor(text=texts, images=[[screen(r["image"])] for r in chunk], return_tensors="pt",
                               padding=True), model)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                                 eos_token_id=processor.tokenizer.convert_tokens_to_ids(["<|eot|>", "<|end_of_text|>"]))
        new = gen[:, enc["input_ids"].shape[1]:]
        for r, g in zip(chunk, new):
            text = processor.tokenizer.decode(g, skip_special_tokens=True).strip()
            tokens += int((g != processor.tokenizer.pad_token_id).sum())
            try:
                ans = json.loads(text[text.index("{"):text.rindex("}") + 1])
                probs = {o: float(ans["probabilities"][o]) for o in r["options"]}
            except (ValueError, KeyError, TypeError):
                probs = None
            outs.append({"id": r["id"], "text": text, "probs": probs})
        print(f"generated {min(i + batch, len(recs))}/{len(recs)}  {time.time() - t0:.0f}s", flush=True)
    return outs, {"seconds": time.time() - t0, "new_tokens": tokens}


# ---- entry points ---------------------------------------------------------------------

@app.function(image=image, gpu=GPU, volumes={WEIGHTS: weights, RUNS: runs}, timeout=3600)
def smoke():
    """Load, look at module names and one encoded example, one training step, one generation."""
    import collections
    import torch
    processor, model = load(train=True)
    kinds = collections.Counter(type(m).__name__ for _, m in model.named_modules())
    print("GB after load", torch.cuda.memory_allocated() / 1e9, {k: v for k, v in kinds.items() if "Linear" in k})
    print("children:", [n for n, _ in model.base_model.model.model.named_children()])
    recs = read("train")[:2]
    print(processor.apply_chat_template(recs[0]["messages"], tokenize=False)[-700:])
    enc = [encode(processor, r) for r in recs]
    print({k: tuple(v.shape) for k, v in enc[0].items()}, "answer tokens:", int((enc[0]["labels"] != -100).sum()))
    batch = to_dev(collate(processor, enc), model)
    loss = model(**batch).loss
    loss.backward()
    print("loss", float(loss), "peak GB", torch.cuda.max_memory_allocated() / 1e9)
    model.eval()
    outs, speed = generate(processor, model, read("test")[:4], batch=4)
    for o in outs:
        print(o)
    print(speed)


@app.function(image=image, gpu=GPU, volumes={WEIGHTS: weights, RUNS: runs}, timeout=4 * 3600)
def train(run: str = "r1", epochs: float = 2, lr: float = 2e-4, batch: int = 2, accum: int = 8):
    import json
    import random
    import time
    import torch
    processor, model = load(train=True)
    data = read("train")
    val = read("val")
    out = f"{RUNS}/{run}"
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=0.0)
    steps = int(len(data) * epochs / (batch * accum))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 20) * max(0.0, 1 - s / steps))
    rng, log, t0, step = random.Random(0), [], time.time(), 0

    def val_loss():
        model.eval()
        losses = []
        with torch.no_grad():
            for i in range(0, 120, batch):
                b = to_dev(collate(processor, [encode(processor, r) for r in val[i:i + batch]]), model)
                losses.append(float(model(**b).loss))
        model.train()
        return sum(losses) / len(losses)

    print("val loss before", val_loss(), flush=True)
    model.train()
    order = []
    while step < steps:
        if len(order) < batch:
            idx = list(range(len(data)))
            rng.shuffle(idx)
            order += idx
        total = 0.0
        for _ in range(accum):
            ids, order = order[:batch], order[batch:]
            b = to_dev(collate(processor, [encode(processor, data[i]) for i in ids]), model)
            loss = model(**b).loss / accum
            loss.backward()
            total += float(loss)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sched.step(); opt.zero_grad()
        step += 1
        log.append({"step": step, "loss": total, "s": time.time() - t0})
        if step % 10 == 0:
            print(f"step {step}/{steps} loss {total:.4f} {time.time() - t0:.0f}s", flush=True)
        if step % 100 == 0 or step == steps:
            v = val_loss()
            log.append({"step": step, "val_loss": v})
            print(f"step {step} val loss {v:.4f}", flush=True)
            model.save_pretrained(out)
            json.dump(log, open(f"{out}/train_log.json", "w"))
            runs.commit()
    print("saved", out, f"{time.time() - t0:.0f}s")


@app.function(image=image, gpu=GPU, volumes={WEIGHTS: weights, RUNS: runs}, timeout=3 * 3600)
def evaluate(run: str = "r1", n: int = 0):
    """Base Glimmer and tuned Glimmer on the held-out test set; scored on the Mac."""
    import json
    test = read("test")
    test = test[:n] if n else test
    processor, model = load(adapter=f"{RUNS}/{run}")
    model.eval()
    tuned, tuned_speed = generate(processor, model, test)
    with model.disable_adapter():
        base, base_speed = generate(processor, model, test)
    json.dump({"tuned": tuned, "base": base, "speed": {"tuned": tuned_speed, "base": base_speed}},
              open(f"{RUNS}/{run}/eval.json", "w"))
    runs.commit()
    print("wrote", f"{RUNS}/{run}/eval.json")


# ---- fast serving check with vLLM ---------------------------------------------------

vllm_image = (modal.Image.from_registry("vllm/vllm-openai:muse-glimmer")
              .entrypoint([])
              .run_commands("ln -sf $(command -v python3) /usr/local/bin/python && python --version")
              .env({"HF_HOME": WEIGHTS + "/hf"}))


@app.function(image=image, gpu=GPU, volumes={WEIGHTS: weights, RUNS: runs}, timeout=3600, memory=131072)
def merge(run: str = "r1"):
    """bf16 base + adapter -> one merged checkpoint (vLLM's LoRA path fails on this multimodal model)."""
    import shutil
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoProcessor
    base = f"{WEIGHTS}/glimmer"
    model = AutoModelForImageTextToText.from_pretrained(base, dtype=torch.bfloat16, device_map={"": 0})
    model = PeftModel.from_pretrained(model, f"{RUNS}/{run}").merge_and_unload()
    out = f"{WEIGHTS}/glimmer_{run}"
    model.save_pretrained(out, max_shard_size="10GB")
    AutoProcessor.from_pretrained(base).save_pretrained(out)
    for f in ("chat_template.jinja", "generation_config.json"):
        shutil.copy(f"{base}/{f}", f"{out}/{f}")
    weights.commit()
    print("merged to", out)


def vllm_load(run):
    from vllm import LLM, SamplingParams
    llm = LLM(model=f"{WEIGHTS}/glimmer_{run}", max_model_len=4096, gpu_memory_utilization=0.92,
              limit_mm_per_prompt={"image": 1})
    stop = llm.get_tokenizer().convert_tokens_to_ids(["<|eot|>", "<|end_of_text|>"])
    return llm, lambda temperature: SamplingParams(temperature=temperature, max_tokens=160, stop_token_ids=stop)


def vllm_answers(llm, params, recs):
    """One parsed answer per chat record ({id, text, probs, noticed, reason}); probs is None if not valid JSON."""
    import json
    from PIL import Image
    tok = llm.get_tokenizer()
    imgs, prompts = {}, []
    for r in recs:
        if r["image"] not in imgs:
            imgs[r["image"]] = Image.open(f"{RUNS}/data/screens/{r['image']}").convert("RGB")
        text = tok.apply_chat_template(r["messages"][:2], tokenize=False, add_generation_prompt=True) + PREFIX
        prompts.append({"prompt": text, "multi_modal_data": {"image": imgs[r["image"]]}})
    rows = []
    for r, g in zip(recs, llm.generate(prompts, params)):
        text = g.outputs[0].text.strip()
        try:
            ans = json.loads(text[text.index("{"):text.rindex("}") + 1])
            probs = {o: float(ans["probabilities"][o]) for o in r["options"]}
            noticed, reason = str(ans.get("noticed", "")), str(ans.get("reason", ""))
        except (ValueError, KeyError, TypeError):
            probs, noticed, reason = None, "", ""
        rows.append({"id": r["id"], "text": text, "probs": probs, "noticed": noticed, "reason": reason,
                     "new_tokens": len(g.outputs[0].token_ids)})
    return rows


@app.function(image=vllm_image, gpu=GPU, volumes={WEIGHTS: weights, RUNS: runs}, timeout=3600)
def evaluate_vllm(run: str = "r1"):
    """The test set through vLLM on the merged checkpoint, to see real serving speed."""
    import json
    import time
    test = [json.loads(x) for x in open(f"{RUNS}/data/test.jsonl")]
    llm, params = vllm_load(run)
    t0 = time.time()
    rows = vllm_answers(llm, params(0), test)
    secs = time.time() - t0
    out = {"tuned": rows, "speed": {"tuned": {"seconds": secs, "new_tokens": sum(r["new_tokens"] for r in rows)}}}
    print("tuned", f"{secs:.1f}s for {len(test)} decisions", flush=True)
    json.dump(out, open(f"{RUNS}/{run}/eval_vllm.json", "w"))
    runs.commit()
    print("wrote", f"{RUNS}/{run}/eval_vllm.json")


@app.function(image=vllm_image, gpu=GPU, volumes={WEIGHTS: weights, RUNS: runs}, timeout=3 * 3600)
def decide_table(name: str = "kindred", run: str = "r1"):
    """Answer every prompt in /runs/jobs/{name}.jsonl (engine/world/glimmer.py) -> {name}_out.jsonl.

    Greedy first, like the evaluation; answers without valid JSON are asked again with sampling.
    """
    import json
    import time
    recs = [json.loads(x) for x in open(f"{RUNS}/jobs/{name}.jsonl")]
    llm, params = vllm_load(run)
    t0 = time.time()
    rows = {r["id"]: r for r in vllm_answers(llm, params(0), recs)}
    for attempt in range(3):
        bad = [r for r in recs if rows[r["id"]]["probs"] is None]
        print(f"pass {attempt}: {len(recs) - len(bad)}/{len(recs)} valid, {time.time() - t0:.0f}s", flush=True)
        if not bad:
            break
        rows.update({r["id"]: r for r in vllm_answers(llm, params(0.7), bad)})
    with open(f"{RUNS}/jobs/{name}_out.jsonl", "w") as f:
        for r in recs:
            f.write(json.dumps(rows[r["id"]]) + "\n")
    runs.commit()
    print("wrote", f"{RUNS}/jobs/{name}_out.jsonl", f"{time.time() - t0:.0f}s")
