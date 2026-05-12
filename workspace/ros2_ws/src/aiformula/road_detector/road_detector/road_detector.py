from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
import onnxruntime as ort
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image


def resize_unscale(img: np.ndarray, new_shape: tuple[int, int], color: int = 114):
    shape = img.shape[:2]
    canvas = np.zeros((new_shape[0], new_shape[1], 3), dtype=np.float32)
    canvas.fill(color)
    ratio = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

    new_unpad_w = int(round(shape[1] * ratio))
    new_unpad_h = int(round(shape[0] * ratio))
    pad_w = new_shape[1] - new_unpad_w
    pad_h = new_shape[0] - new_unpad_h
    dw = pad_w // 2
    dh = pad_h // 2

    if shape[::-1] != (new_unpad_w, new_unpad_h):
        img = cv2.resize(img, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_AREA)

    canvas[dh : dh + new_unpad_h, dw : dw + new_unpad_w, :] = img
    return canvas, dw, dh, new_unpad_w, new_unpad_h


def provider_candidates(provider: str) -> list[list[str]]:
    provider = provider.strip().lower()
    if provider == "cpu":
        return [["CPUExecutionProvider"]]
    if provider == "cuda":
        return [["CUDAExecutionProvider", "CPUExecutionProvider"], ["CPUExecutionProvider"]]
    if provider == "tensorrt":
        return [
            ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
            ["CUDAExecutionProvider", "CPUExecutionProvider"],
            ["CPUExecutionProvider"],
        ]
    return [
        ["CUDAExecutionProvider", "CPUExecutionProvider"],
        ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        ["CPUExecutionProvider"],
    ]


def available_provider_sets(candidates: Iterable[list[str]]) -> Iterable[list[str]]:
    available = set(ort.get_available_providers())
    for providers in candidates:
        selected = [provider for provider in providers if provider in available]
        if selected:
            yield selected


class YolopA1Runner:
    def __init__(self, model_path: str, provider: str, logger) -> None:
        if not Path(model_path).is_file():
            raise FileNotFoundError(model_path)

        ort.set_default_logger_severity(3)
        errors: list[str] = []
        for providers in available_provider_sets(provider_candidates(provider)):
            try:
                self.session = ort.InferenceSession(model_path, providers=providers)
                logger.info(f"Loaded YOLOP_A1 ONNX with providers={self.session.get_providers()}")
                break
            except Exception as exc:
                errors.append(f"{providers}: {exc!r}")
        else:
            raise RuntimeError("Failed to create ONNX Runtime session: " + "; ".join(errors))

        self.input_name = self.session.get_inputs()[0].name
        output_names = [output.name for output in self.session.get_outputs()]
        self.output_name = "lane_line_seg" if "lane_line_seg" in output_names else None
        self.output_names = output_names
        logger.info(f"YOLOP_A1 input={self.input_name}, outputs={output_names}")

    def infer_lane(self, x: np.ndarray) -> np.ndarray:
        if self.output_name:
            return self.session.run([self.output_name], {self.input_name: x})[0]

        outputs = self.session.run(None, {self.input_name: x})
        for output in outputs:
            if output.ndim == 4 and output.shape[1] in (1, 2):
                return output
        raise RuntimeError(f"Could not identify lane output from shapes {[output.shape for output in outputs]}")


class RoadDetector(Node):
    def __init__(self) -> None:
        super().__init__("road_detector")
        self.bridge = CvBridge()

        self.declare_parameter("onnx_path", "")
        self.declare_parameter("provider", "cuda")
        self.declare_parameter("input_size", 640)
        self.declare_parameter("ll_threshold", 0.5)
        self.declare_parameter("drop_every_n", 2)
        self.declare_parameter("publish_annotated", True)

        self.input_size = int(self.get_parameter("input_size").value)
        self.ll_threshold = float(self.get_parameter("ll_threshold").value)
        self.drop_every_n = max(1, int(self.get_parameter("drop_every_n").value))
        self.publish_annotated = bool(self.get_parameter("publish_annotated").value)
        model_path = str(self.get_parameter("onnx_path").value)
        provider = str(self.get_parameter("provider").value)

        try:
            cv2.setNumThreads(1)
        except Exception:
            pass

        self.runner = YolopA1Runner(model_path, provider, self.get_logger())
        self.mask_pub = self.create_publisher(Image, "pub_mask_image", 10)
        self.mask_roi_pub = self.create_publisher(Image, "pub_mask_image_roi", 10)
        self.annotated_pub = self.create_publisher(Image, "pub_annotated_mask_image", 10)
        self.image_sub = self.create_subscription(Image, "sub_image", self.image_callback, 10)

        self.frame_count = 0
        self.last_log_time = time.monotonic()
        self.get_logger().info(
            f"YOLOP_A1 road detector ready: input_size={self.input_size}, "
            f"drop_every_n={self.drop_every_n}, publish_annotated={self.publish_annotated}"
        )

    def image_callback(self, msg: Image) -> None:
        self.frame_count += 1
        if self.frame_count % self.drop_every_n != 0:
            return

        start = time.monotonic()
        try:
            img_bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as exc:
            self.get_logger().error(f"CvBridgeError: {exc}")
            return

        height, width = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        canvas, dw, dh, new_unpad_w, new_unpad_h = resize_unscale(
            img_rgb, (self.input_size, self.input_size)
        )

        x = canvas.astype(np.float32) / 255.0
        x[:, :, 0] = (x[:, :, 0] - 0.485) / 0.229
        x[:, :, 1] = (x[:, :, 1] - 0.456) / 0.224
        x[:, :, 2] = (x[:, :, 2] - 0.406) / 0.225
        x = np.expand_dims(x.transpose(2, 0, 1), axis=0).astype(np.float32, copy=False)

        try:
            lane_logits = self.runner.infer_lane(x)
        except Exception as exc:
            self.get_logger().error(f"YOLOP_A1 inference failed: {exc!r}")
            return

        try:
            lane_mask = self.make_lane_mask(lane_logits, dw, dh, new_unpad_w, new_unpad_h, width, height)
        except Exception as exc:
            self.get_logger().error(f"YOLOP_A1 lane output decode failed: {exc!r}")
            return

        self.publish_mask(self.mask_pub, lane_mask, msg)
        self.publish_mask(self.mask_roi_pub, lane_mask, msg)
        if self.publish_annotated:
            self.publish_annotated_image(img_bgr, lane_mask, msg)

        now = time.monotonic()
        if now - self.last_log_time >= 2.0:
            self.last_log_time = now
            elapsed_ms = (now - start) * 1000.0
            self.get_logger().info(
                f"published mask {width}x{height}, lane_mean={lane_mask.mean() / 255.0:.4f}, "
                f"inference_frame_ms={elapsed_ms:.1f}"
            )

    def make_lane_mask(
        self,
        lane_logits: np.ndarray,
        dw: int,
        dh: int,
        new_unpad_w: int,
        new_unpad_h: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        if lane_logits.ndim != 4:
            raise ValueError(f"expected 4D lane output, got {lane_logits.shape}")

        if lane_logits.shape[1] == 2:
            mask = np.argmax(lane_logits, axis=1)[0].astype(np.uint8)
        elif lane_logits.shape[1] == 1:
            mask = (lane_logits[0, 0] >= self.ll_threshold).astype(np.uint8)
        else:
            raise ValueError(f"expected channel count 1 or 2, got {lane_logits.shape}")

        cropped = mask[dh : dh + new_unpad_h, dw : dw + new_unpad_w]
        resized = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_NEAREST)
        return (resized.astype(np.uint8) * 255)

    def publish_mask(self, publisher, lane_mask: np.ndarray, source_msg: Image) -> None:
        try:
            mask_msg = self.bridge.cv2_to_imgmsg(lane_mask, encoding="mono8")
            mask_msg.header = source_msg.header
            publisher.publish(mask_msg)
        except CvBridgeError as exc:
            self.get_logger().error(f"CvBridgeError publishing mask: {exc}")

    def publish_annotated_image(self, img_bgr: np.ndarray, lane_mask: np.ndarray, source_msg: Image) -> None:
        overlay = img_bgr.copy()
        lane_pixels = lane_mask > 0
        overlay[lane_pixels] = (0.4 * overlay[lane_pixels] + 0.6 * np.array([0, 255, 0])).astype(np.uint8)
        try:
            annotated_msg = self.bridge.cv2_to_imgmsg(overlay, encoding="bgr8")
            annotated_msg.header = source_msg.header
            self.annotated_pub.publish(annotated_msg)
        except CvBridgeError as exc:
            self.get_logger().error(f"CvBridgeError publishing annotated image: {exc}")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = RoadDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.destroy_node()
        except (KeyboardInterrupt, RCLError):
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
