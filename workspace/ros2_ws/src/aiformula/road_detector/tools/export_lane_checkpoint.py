#!/usr/bin/env python3
"""Export a YOLOP_A1 lane-only PyTorch checkpoint to ONNX.

This script is intentionally self-contained. The ROSMASTER Jetson has PyTorch
and ONNX installed, but not every training-time dependency from YOLOP_A1.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path

import onnx
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn import Upsample


def autopad(k, p=None):
    if p is None:
        p = k // 2 if isinstance(k, int) else [x // 2 for x in k]
    return p


class Hardswish(nn.Module):
    @staticmethod
    def forward(x):
        return x * F.hardtanh(x + 3, 0.0, 6.0) / 6.0


class Conv(nn.Module):
    def __init__(self, c1, c2, k=1, s=1, p=None, g=1, act=True):
        super().__init__()
        self.conv = nn.Conv2d(c1, c2, k, s, autopad(k, p), groups=g, bias=False)
        self.bn = nn.BatchNorm2d(c2)
        self.act = Hardswish() if act else nn.Identity()

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))


class Bottleneck(nn.Module):
    def __init__(self, c1, c2, shortcut=True, g=1, e=0.5):
        super().__init__()
        c_ = int(c2 * e)
        self.cv1 = Conv(c1, c_, 1, 1)
        self.cv2 = Conv(c_, c2, 3, 1, g=g)
        self.add = shortcut and c1 == c2

    def forward(self, x):
        return x + self.cv2(self.cv1(x)) if self.add else self.cv2(self.cv1(x))


class BottleneckCSP(nn.Module):
    def __init__(self, c1, c2, n=1, shortcut=True, g=1, e=0.5):
        super().__init__()
        c_ = int(c2 * e)
        self.cv1 = Conv(c1, c_, 1, 1)
        self.cv2 = nn.Conv2d(c1, c_, 1, 1, bias=False)
        self.cv3 = nn.Conv2d(c_, c_, 1, 1, bias=False)
        self.cv4 = Conv(2 * c_, c2, 1, 1)
        self.bn = nn.BatchNorm2d(2 * c_)
        self.act = nn.LeakyReLU(0.1, inplace=True)
        self.m = nn.Sequential(*[Bottleneck(c_, c_, shortcut, g, e=1.0) for _ in range(n)])

    def forward(self, x):
        y1 = self.cv3(self.m(self.cv1(x)))
        y2 = self.cv2(x)
        return self.cv4(self.act(self.bn(torch.cat((y1, y2), dim=1))))


class SPP(nn.Module):
    def __init__(self, c1, c2, k=(5, 9, 13)):
        super().__init__()
        c_ = c1 // 2
        self.cv1 = Conv(c1, c_, 1, 1)
        self.cv2 = Conv(c_ * (len(k) + 1), c2, 1, 1)
        self.m = nn.ModuleList([nn.MaxPool2d(kernel_size=x, stride=1, padding=x // 2) for x in k])

    def forward(self, x):
        x = self.cv1(x)
        return self.cv2(torch.cat([x] + [m(x) for m in self.m], 1))


class Focus(nn.Module):
    def __init__(self, c1, c2, k=1, s=1, p=None, g=1, act=True):
        super().__init__()
        self.conv = Conv(c1 * 4, c2, k, s, p, g, act)

    def forward(self, x):
        return self.conv(
            torch.cat(
                [x[..., ::2, ::2], x[..., 1::2, ::2], x[..., ::2, 1::2], x[..., 1::2, 1::2]],
                1,
            )
        )


class Concat(nn.Module):
    def __init__(self, dimension=1):
        super().__init__()
        self.d = dimension

    def forward(self, x):
        return torch.cat(x, self.d)


LANE_ONLY = [
    [25],
    [-1, Focus, [3, 32, 3]],
    [-1, Conv, [32, 64, 3, 2]],
    [-1, BottleneckCSP, [64, 64, 1]],
    [-1, Conv, [64, 128, 3, 2]],
    [-1, BottleneckCSP, [128, 128, 3]],
    [-1, Conv, [128, 256, 3, 2]],
    [-1, BottleneckCSP, [256, 256, 3]],
    [-1, Conv, [256, 512, 3, 2]],
    [-1, SPP, [512, 512, [5, 9, 13]]],
    [-1, BottleneckCSP, [512, 512, 1, False]],
    [-1, Conv, [512, 256, 1, 1]],
    [-1, Upsample, [None, 2, "nearest"]],
    [[-1, 6], Concat, [1]],
    [-1, BottleneckCSP, [512, 256, 1, False]],
    [-1, Conv, [256, 128, 1, 1]],
    [-1, Upsample, [None, 2, "nearest"]],
    [[-1, 4], Concat, [1]],
    [16, Conv, [256, 128, 3, 1]],
    [-1, Upsample, [None, 2, "nearest"]],
    [-1, BottleneckCSP, [128, 64, 1, False]],
    [-1, Conv, [64, 32, 3, 1]],
    [-1, Upsample, [None, 2, "nearest"]],
    [-1, Conv, [32, 16, 3, 1]],
    [-1, BottleneckCSP, [16, 8, 1, False]],
    [-1, Upsample, [None, 2, "nearest"]],
    [-1, nn.Conv2d, [8, 2, 3, 1, 1]],
]

LEGACY_LAYER_MAP = {
    **{idx: idx for idx in range(17)},
    **{src: dst for src, dst in zip(range(34, 43), range(17, 26))},
}


def initialize_weights(model):
    for module in model.modules():
        module_type = type(module)
        if module_type is nn.BatchNorm2d:
            module.eps = 1e-3
            module.momentum = 0.03
        elif module_type in [nn.Hardswish, nn.LeakyReLU, nn.ReLU, nn.ReLU6]:
            module.inplace = True


class LaneOnlyModel(nn.Module):
    def __init__(self, block_cfg):
        super().__init__()
        layers, save = [], []
        self.seg_out_idx = block_cfg[0][0]

        for i, (from_, block, args) in enumerate(block_cfg[1:]):
            module = block(*args)
            module.index, module.from_ = i, from_
            layers.append(module)
            save.extend(x % i for x in ([from_] if isinstance(from_, int) else from_) if x != -1)

        self.model = nn.Sequential(*layers)
        self.save = sorted(save)
        self.names = ["background", "lane"]
        initialize_weights(self)

    def forward(self, x):
        cache = []
        lane_logits = None

        for i, block in enumerate(self.model):
            if block.from_ != -1:
                x = (
                    cache[block.from_]
                    if isinstance(block.from_, int)
                    else [x if j == -1 else cache[j] for j in block.from_]
                )
            x = block(x)
            if i == self.seg_out_idx:
                lane_logits = x
            cache.append(x if block.index in self.save else None)

        return lane_logits


def _strip_module_prefix(state_dict):
    clean_state = OrderedDict()
    for key, value in state_dict.items():
        clean_key = key[7:] if key.startswith("module.") else key
        clean_state[clean_key] = value
    return clean_state


def _remap_legacy_key(key):
    if not key.startswith("model."):
        return None

    key_parts = key.split(".")
    if len(key_parts) < 3:
        return None

    try:
        layer_idx = int(key_parts[1])
    except ValueError:
        return None

    if layer_idx not in LEGACY_LAYER_MAP:
        return None

    key_parts[1] = str(LEGACY_LAYER_MAP[layer_idx])
    return ".".join(key_parts)


def get_lane_state_dict(model, checkpoint_or_state_dict):
    state_dict = checkpoint_or_state_dict.get("state_dict", checkpoint_or_state_dict)
    state_dict = _strip_module_prefix(state_dict)
    model_state = model.state_dict()
    loadable_state = OrderedDict()

    for key, value in state_dict.items():
        if key in model_state and model_state[key].shape == value.shape:
            loadable_state[key] = value
            continue

        remapped_key = _remap_legacy_key(key)
        if remapped_key and remapped_key in model_state and model_state[remapped_key].shape == value.shape:
            loadable_state[remapped_key] = value

    return loadable_state


def load_lane_only_weights(model, checkpoint_or_state_dict, strict=False):
    loadable_state = get_lane_state_dict(model, checkpoint_or_state_dict)
    incompatible = model.load_state_dict(loadable_state, strict=strict)
    return {
        "loaded_keys": sorted(loadable_state.keys()),
        "missing_keys": list(incompatible.missing_keys),
        "unexpected_keys": list(incompatible.unexpected_keys),
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True, help="Path to a YOLOP_A1 lane checkpoint .pth file.")
    parser.add_argument("--output", required=True, help="Output ONNX path.")
    parser.add_argument("--height", type=int, default=640)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--opset", type=int, default=12)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="PyTorch export device.")
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    device = "cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    model = LaneOnlyModel(LANE_ONLY).to(device)
    try:
        checkpoint = torch.load(args.weights, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(args.weights, map_location=device)
    load_info = load_lane_only_weights(model, checkpoint)
    if not load_info["loaded_keys"]:
        raise RuntimeError(f"No compatible keys were loaded from {args.weights}")

    model.eval()
    inputs = torch.randn(1, 3, args.height, args.width, device=device)
    with torch.no_grad():
        output = model(inputs)

    print(f"Loaded {len(load_info['loaded_keys'])} checkpoint tensors")
    print(f"Missing tensors after partial load: {len(load_info['missing_keys'])}")
    print(f"Export output shape: {tuple(output.shape)}")

    torch.onnx.export(
        model,
        inputs,
        str(output_path),
        verbose=False,
        opset_version=args.opset,
        input_names=["images"],
        output_names=["lane_line_seg"],
    )
    onnx.checker.check_model(onnx.load(str(output_path)))
    print(f"Exported {output_path}")


if __name__ == "__main__":
    main()
