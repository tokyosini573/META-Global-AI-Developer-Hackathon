"""Publish the tuned Glimmer weights on Hugging Face, under Apache 2.0 like the base model.

    .venv/bin/python -m engine.distill.publish adapter                  # LoRA adapter from runs/glimmer_r1/r1
    .venv/bin/modal run engine/distill/publish_modal.py                 # merged bf16 checkpoint, from the Modal volume

Both read the owner's Hugging Face token: HF_TOKEN in .env here, the Modal secret `huggingface`
(HF_TOKEN) for the merged upload. The model card is written from the real prompt format and the
committed evaluation results.
"""

import json
import sys
from pathlib import Path

from engine.check_api import load_env

ROOT = Path(__file__).resolve().parent.parent.parent
ADAPTER = ROOT / "runs" / "glimmer_r1" / "r1"
BASE = "meta-models/Muse-Glimmer-30B"
BASE_REVISION = "cec94fcfd6512f2cfe708138c32533b346ea4f69"
NAME = "Rehearsal-Glimmer-30B-r1"
GITHUB = "https://github.com/tokyosini573/META-Global-AI-Developer-Hackathon"
PREFIX = " to=user<|message|>"


def repos(user):
    return {"merged": f"{user}/{NAME}", "adapter": f"{user}/{NAME}-LoRA"}


def example():
    rec = json.loads((ROOT / "data" / "distill" / "test.jsonl").read_text().splitlines()[0])
    return rec["image"], rec["messages"]


def card(kind, user):
    r = repos(user)
    image, messages = example()
    system = messages[0]["content"]
    question = messages[1]["content"][1]["text"]
    if kind == "adapter":
        meta = f"base_model: {BASE}\nbase_model_relation: adapter\nlibrary_name: peft"
        what = (f"LoRA adapter for [{BASE}](https://huggingface.co/{BASE}). The same weights merged into the "
                f"base, ready for vLLM: [{r['merged']}](https://huggingface.co/{r['merged']}).")
        load = (f'model = AutoModelForImageTextToText.from_pretrained("{BASE}", dtype=torch.bfloat16, '
                f'device_map="auto")\nmodel = PeftModel.from_pretrained(model, "{r["adapter"]}")\n'
                f'processor = AutoProcessor.from_pretrained("{BASE}")')
        imports = "from peft import PeftModel\n"
    else:
        meta = f"base_model: {BASE}\nbase_model_relation: finetune\nlibrary_name: transformers"
        what = (f"[{BASE}](https://huggingface.co/{BASE}) with the LoRA adapter "
                f"[{r['adapter']}](https://huggingface.co/{r['adapter']}) merged in, in bf16. vLLM's LoRA path "
                "fails on this multimodal model, so this is the checkpoint that serves the decisions.")
        load = (f'model = AutoModelForImageTextToText.from_pretrained("{r["merged"]}", dtype=torch.bfloat16, '
                f'device_map="auto")\nprocessor = AutoProcessor.from_pretrained("{r["merged"]}")')
        imports = ""
    return f"""---
license: apache-2.0
{meta}
pipeline_tag: image-text-to-text
language: [en]
tags: [distillation, simulation, agent-based-model, lora]
---

# {NAME}{"-LoRA" if kind == "adapter" else ""}

Muse Glimmer 30B fine-tuned to make the decisions Muse Spark makes for one simulated person looking at
one app screen: install the app from an ad, or pay, come back tomorrow or delete the app at a paywall.
It answers with probabilities for each option, what the person noticed, and why.

{what}

Built for **Rehearsal**, a launch world model that plays two launch plans out in a simulated US market
for 90 days ([code and method]({GITHUB})). Every simulated person decides with this model.

## Results

408 held-out fictional people (never seen in training), compared with Muse Spark's answer:

| Model | Same top choice | Mean abs. difference |
|---|---|---|
| Spark asked a second time | 86% | 0.078 |
| Glimmer before training | 74% | 0.151 |
| **Glimmer after training (adapter on the 4-bit base)** | **85%** | **0.079** |
| Glimmer after training (this merged bf16 checkpoint, vLLM) | 84% | 0.083 |

The tuned model agrees with Spark about as often as Spark agrees with itself. On 300 decisions from a
different population (people designed by Muse Wonder), it gives the same top choice as Spark 90% of
the time (mean absolute difference 0.065). With vLLM on one H100, a decision takes 0.064 s.

## Training

- **Data:** 4,000 fictional people, each with their own age, work, place, money, dating history and
  mood, looking at the screens of a made-up dating app. Muse Spark (contributor, reasoning medium)
  answered each one. Split 3,201 / 391 / 408 by person. The data is in the repository
  ([`data/distill/`]({GITHUB}/tree/main/data/distill)), and so are the screens it shows
  ([`engine/screens/out/`]({GITHUB}/tree/main/engine/screens/out)).
- **Target:** Spark's final JSON only, sent straight to the user channel. There is no reasoning text.
- **Method:** QLoRA on one H100. The base is 4-bit NF4 with bf16 compute. LoRA r = 16, alpha 32,
  dropout 0.05 on the q, k, v and o projections of the language model; the vision tower is frozen.
  400 steps of 16 examples (2 epochs), lr 2e-4, 56 minutes. Validation loss fell from 0.958 to 0.257.
- **Base revision:** `{BASE_REVISION}`.

## Prompt format

The prompt is the system prompt with the person, the screen image, the question with a one-line JSON
instruction, and then the assistant turn opened straight to the user channel (`{PREFIX.strip()}`).

```python
import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor
{imports}
{load}

messages = [
    {{"role": "system", "content": {json.dumps(system)}}},
    {{"role": "user", "content": [{{"type": "image"}}, {{"type": "text", "text": {json.dumps(question)}}}]}},
]
text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True) + "{PREFIX}"
screen = Image.open("{image}").convert("RGB")   # from engine/screens/out in the repository
inputs = {{k: v.to(model.device, torch.bfloat16 if v.is_floating_point() else None)
          for k, v in processor(text=[text], images=[[screen]], return_tensors="pt").items()}}
out = model.generate(**inputs, max_new_tokens=160)
print(processor.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))
# {{"noticed": "...", "probabilities": {{"pay": ..., "come_back_tomorrow": ..., "delete_app": ...}}, "reason": "..."}}
```

The exact code used for training, evaluation and vLLM serving is in
[`engine/distill/glimmer_modal.py`]({GITHUB}/blob/main/engine/distill/glimmer_modal.py).

## Limits

- **Same generator.** The held-out people come from the same generator as the training people. This
  shows that the model reproduces Spark on new people of the same kind, not that either model
  matches real users.
- **Spark's biases.** It learns Spark's answers, including Spark's biases.
- **One app.** It was trained on one made-up app's ad, store and paywall screens, in English, for a
  US market.
- **Simulation only.** It is meant for simulating fictional people, not for decisions about real
  ones.

## License

Apache 2.0, like the base model. This is a modified version of [{BASE}](https://huggingface.co/{BASE}):
fine-tuned as described above{" and merged into the base weights" if kind == "merged" else ""}. The
base model's LICENSE is included.
"""


def adapter():
    from huggingface_hub import CommitOperationAdd, HfApi
    env = load_env()
    api = HfApi(token=env["HF_TOKEN"])
    user = api.whoami()["name"]
    repo = repos(user)["adapter"]
    config = json.loads((ADAPTER / "adapter_config.json").read_text())
    config.update(base_model_name_or_path=BASE, revision=BASE_REVISION)
    api.create_repo(repo, exist_ok=True)
    base_license = api.hf_hub_download(BASE, "LICENSE", revision=BASE_REVISION)
    files = {"README.md": card("adapter", user).encode(), "adapter_config.json": json.dumps(config, indent=2).encode(),
             "LICENSE": base_license, "adapter_model.safetensors": str(ADAPTER / "adapter_model.safetensors"),
             "train_log.json": str(ADAPTER / "train_log.json")}
    api.create_commit(repo, [CommitOperationAdd(name, data) for name, data in files.items()],
                      commit_message="Rehearsal Glimmer r1: LoRA adapter")
    print(f"https://huggingface.co/{repo}")


if __name__ == "__main__":
    {"adapter": adapter}[sys.argv[1]]()
