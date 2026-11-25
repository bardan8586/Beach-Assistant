# Detection evaluation

Generated 2026-11-25 00:39 UTC by `ai/scripts/evaluate.py`.

## What was measured this run

Dataset mAP was **not** measured. The fine-tuned `best.pt` weights and the Roboflow images are gitignored and were not present for this run.

Previously recorded validation numbers (5 epochs, CPU, 7 duplicate class names, from the project report and `args.yaml`, not remeasured here):

| Metric | Recorded value |
|---|---:|
| Precision | 0.642 |
| Recall | 0.572 |
| mAP50 | 0.614 |
| mAP50-95 | 0.321 |

## Local matcher fixture

The table below is the built-in fixture inside `evaluate.py`. It checks the confusion-matrix code. It is not beach-model accuracy.

| Class | Precision | Recall | F1 | Support | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| drowning | 1.000 | 1.000 | 1.000 | 1 | 1 | 0 | 0 |
| out_of_water | 0.000 | 0.000 | 0.000 | 1 | 0 | 0 | 1 |
| swimming | 0.500 | 1.000 | 0.667 | 1 | 1 | 1 | 0 |
| person | 0.000 | 0.000 | 0.000 | 1 | 0 | 0 | 1 |

| | drowning | out_of_water | swimming | person | background |
|---|---:|---:|---:|---:|---:|
| drowning | 1 | 0 | 0 | 0 | 0 |
| out_of_water | 0 | 0 | 0 | 0 | 1 |
| swimming | 0 | 0 | 1 | 0 | 0 |
| person | 0 | 0 | 1 | 0 | 0 |
| background | 0 | 0 | 0 | 0 | 0 |

Fixture micro precision 0.667, recall 0.500.

## Notes

- Canonical classes are drowning, out_of_water, swimming, person. Duplicate Roboflow names should be remapped with `ai/scripts/prepare_dataset.py` before a new training run.
- IoU threshold for the local matcher is 0.5.
- No --weights/--data flags, so Ultralytics validation was skipped.
