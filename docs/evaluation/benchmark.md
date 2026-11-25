# Inference latency

Generated 2026-11-25 00:39 UTC by `ai/scripts/benchmark_inference.py`.

YOLOv8n public checkpoint, not the fine-tuned beach weights. Random frames, so this is latency only, not accuracy.

- Model: `yolov8n.pt`
- Device: `cpu`
- Torch: `2.15.0+cpu`
- Machine: `Linux-6.12.113+-x86_64-with-glibc2.39`
- Frame: 1280x720 random uint8, 16 timed frames after one warmup

## One frame at a time

| imgsz | ms/frame | FPS | FPS if the old 100 ms waitKey is added |
|---:|---:|---:|---:|
| 640 | 18.2 | 54.90 | 8.46 |
| 416 | 10.0 | 99.98 | 9.09 |

## Batched predict

Batch 4 at imgsz 640: 30.0 ms/frame (33.37 FPS).

## ONNX

Exported `yolov8n.onnx` and timed imgsz 640: 56.0 ms/frame (17.87 FPS) against 18.2 ms/frame for the PyTorch checkpoint at the same size.

On this CPU, batch 4 was slower than one frame at a time (30.0 ms vs 18.2 ms), and ONNX Runtime was slower than PyTorch (56.0 ms vs 18.2 ms). The runtime default stays single-frame PyTorch at imgsz 640. imgsz 416 is the measured way to go faster, with an accuracy tradeoff that was not measured because the beach validation set is not in the repo.

The upload pipeline now skips `cv2.waitKey` unless `SHOW_WINDOW=true`, posts ingest off the frame loop, and leaves pose estimation off unless `ENABLE_POSE=true`. Those changes are not all inside the millisecond column above. The last column is the model time plus the 100 ms pause the old loop added on every processed frame.

Half precision needs CUDA and was not timed on this CPU.
