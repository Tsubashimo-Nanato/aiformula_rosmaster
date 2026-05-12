# YOLOP_A1 Mirror

This package uses the lane-only ONNX runtime path from the local special YOLOP version:

```text
E:\Mess\Projects\Programming\aiformula\YOLOP\YOLOP_A1
```

Mirrored runtime artifact:

- `weights/yolop-640-640.onnx`

The ROS node follows the preprocessing convention from `YOLOP_A1/test_onnx.py`:

- letterbox to `640x640`
- RGB ImageNet normalization
- ONNX input name `images`
- lane output name `lane_line_seg` when present
