# Distilling Muse Spark into Muse Glimmer

Rehearsal's simulated people decide what to do in front of app screens (install from an ad,
pay at the paywall, come back tomorrow, delete the app). Muse Spark makes these decisions
well, but it is slow (about 20 seconds a call with reasoning) and rate-limited (150 calls a
minute). So the engine asks Spark once per *person type* and every person of that type shares
the answer.

Distillation teaches Muse Glimmer (open weights, 30B) to give Spark's answer for *each
person*, so a simulation can have thousands of different people instead of six types.

## Pipeline

| Step | Code | What happens |
|---|---|---|
| 1. Data | `engine/distill/make_data.py` | 4,000 fictional people, each with their own persona (age, job, place, money, dating history, mood), look at the same Kindred screens in the same situations as the demo. Spark (contributor, reasoning medium) answers each once; the 408 test people twice. Cost $1.82. |
| 2. Format | `engine/distill/format.py` | Chat examples with the screen image. The target is Spark's final JSON only (the API returns no reasoning text), sent straight to the user channel. Split 3,201 / 391 / 408 by person. |
| 3. Train | `engine/distill/glimmer_modal.py::train` | QLoRA on one Modal H100: 4-bit NF4 base (bf16 compute and storage), LoRA r=16 / alpha 32 on q, k, v, o of the language model, vision tower frozen. 400 steps of 16 examples (2 epochs), lr 2e-4. 56 minutes. |
| 4. Evaluate | `::evaluate`, `engine/distill/score.py` | Glimmer before and after training on the 408 held-out people, against Spark's first answer. |
| 5. Serve | `::merge`, `::evaluate_vllm` | The adapter merged into the bf16 weights and served with vLLM (its LoRA path fails on this multimodal model). |

Everything sent to Spark is fictional: the contributor model's inputs may be used by Meta for training.

## Result (run r1)

Reference: Spark's first answer for each held-out person.

| Compared with Spark | Same top choice | Mean abs. difference |
|---|---|---|
| Spark asked again | 86% | 0.078 |
| Type table (engine today) | 74% | 0.144 |
| Glimmer before training | 74% | 0.151 |
| **Glimmer after training** | **85%** | **0.079** |

- The trained Glimmer agrees with Spark about as often as Spark agrees with itself. Spark is
  not deterministic, so no student can beat the "Spark asked again" row.
- The type table that the engine uses today is clearly worse (74%): a person's own details
  change Spark's answer, which is why per-person decisions are worth having.
- Served from the merged bf16 checkpoint in vLLM, the agreement is nearly the same (84%,
  0.083; the adapter was trained on the 4-bit base) and the test set takes 26 seconds.
- Validation loss fell from 0.958 to 0.257 (`data/distill/r1_train_log.json`).
- Full tables, by decision kind: `data/distill/r1_report.md`.

## Speed and cost per decision

| | Spark (contributor API) | Glimmer, transformers 4-bit | Glimmer, vLLM bf16 merged |
|---|---|---|---|
| Seconds per decision | ~20 (latency), 150 a minute at most | 0.62 | 0.064 |
| Decisions a minute | 150 (rate limit) | ~100 | ~940 |
| Cost per decision | ~$0.0004 | ~$0.0007 | ~$0.00007 |

Glimmer numbers are from one Modal H100 (about $3.95 an hour) on the 408 test people in one
batch. Training and evaluation of run r1 cost about $6 on Modal, data $1.82 on the Meta API.

## Limits

- The test people come from the same generator as the training people. This shows Glimmer
  reproduces Spark on new people of the same kind, not that either model matches real users.
- Glimmer learns Spark's answers, including Spark's biases.
- Glimmer answers without its reasoning channel (the prompt starts the answer directly).
