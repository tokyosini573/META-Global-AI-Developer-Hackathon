# Glimmer distillation: run r1

Held-out test people: 408 (never seen in training). Reference: Spark's first answer.

| Compared with Spark's answer | People | Valid JSON | Same top choice | Mean abs. difference |
|---|---|---|---|---|
| Spark asked again | 408 | 100% | 86% | 0.078 |
| Type table (engine today) | 408 | 100% | 74% | 0.144 |
| Glimmer before training | 408 | 100% | 74% | 0.151 |
| Glimmer after training | 408 | 100% | 85% | 0.079 |

## Install decisions

| Compared with Spark's answer | People | Valid JSON | Same top choice | Mean abs. difference |
|---|---|---|---|---|
| Spark asked again | 159 | 100% | 92% | 0.070 |
| Type table (engine today) | 159 | 100% | 70% | 0.208 |
| Glimmer before training | 159 | 100% | 74% | 0.182 |
| Glimmer after training | 159 | 100% | 91% | 0.071 |

## Paywall decisions

| Compared with Spark's answer | People | Valid JSON | Same top choice | Mean abs. difference |
|---|---|---|---|---|
| Spark asked again | 249 | 100% | 83% | 0.083 |
| Type table (engine today) | 249 | 100% | 76% | 0.103 |
| Glimmer before training | 249 | 100% | 73% | 0.132 |
| Glimmer after training | 249 | 100% | 82% | 0.084 |

## Speed (one H100, 4-bit, batches of 16)

| Model | Seconds per decision |
|---|---|
| Glimmer after training | 0.62 |
| Glimmer before training | 0.55 |

