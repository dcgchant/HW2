import hashlib
import io
import json
import os
from pathlib import Path
import warnings

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps, UnidentifiedImageError

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_SHA256 = "d746a150317b670ed308c243b4aba46f1c0e69c5d1da68e7713b8aca72097c0b"
Image.MAX_IMAGE_PIXELS = 20_000_000
KO_NAMES = ["아프리칸 바이올렛", "알로에 베라", "안스리움", "아레카야자", "아스파라거스 고사리",
            "베고니아", "극락조화", "파초일엽", "보스턴고사리", "칼라테아", "엽란", "필레아 페페로미오이데스",
            "아글라오네마", "게발선인장", "국화", "크테난테", "수선화", "드라세나", "디펜바키아", "알로카시아",
            "아이비", "히아신스", "아이언크로스 베고니아", "염좌", "칼랑코에", "백합류 (모델 라벨)", "은방울꽃",
            "파키라", "몬스테라", "난초", "테이블야자", "스파티필룸", "포인세티아", "무늬쥐꼬리망초",
            "덕구리난", "스킨답서스", "마란타", "칼라테아 란시폴리아", "고무나무", "소철", "홍콩야자",
            "산세베리아", "트라데스칸티아", "튤립", "파리지옥", "유카", "금전수"]


class InvalidImage(ValueError):
    pass


class Classifier:
    def __init__(self):
        model_path = MODEL_DIR / "model_quantized.onnx"
        with model_path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != MODEL_SHA256:
                raise ValueError("Model checksum mismatch. Run python prepare_model.py again.")
        self.config = json.loads((MODEL_DIR / "config.json").read_text(encoding="utf-8"))
        self.preprocessor = json.loads((MODEL_DIR / "preprocessor_config.json").read_text(encoding="utf-8"))
        options = ort.SessionOptions()
        options.intra_op_num_threads = min(4, os.cpu_count() or 1)
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model_path), sess_options=options,
                                            providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        if len(self.config["id2label"]) != len(KO_NAMES):
            raise ValueError("Unexpected model labels")

    def classify(self, data):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as source:
                    if source.format not in {"JPEG", "PNG", "WEBP"}:
                        raise InvalidImage("JPG, PNG, WebP 이미지만 지원합니다.")
                    if source.width * source.height > Image.MAX_IMAGE_PIXELS:
                        raise InvalidImage("이미지는 2,000만 화소 이하여야 합니다.")
                    if getattr(source, "is_animated", False):
                        raise InvalidImage("움직이는 이미지 대신 정지 이미지를 선택해 주세요.")
                    source.load()
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    original_size = list(image.size)
                    size = self.preprocessor["size"]
                    image = image.resize((size["width"], size["height"]), Image.Resampling.BILINEAR)
        except InvalidImage:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as error:
            raise InvalidImage("이미지를 읽을 수 없습니다. 손상되지 않은 JPG, PNG, WebP 파일을 선택해 주세요.") from error
        pixels = np.asarray(image, dtype=np.float32) * self.preprocessor["rescale_factor"]
        pixels = (pixels - np.array(self.preprocessor["image_mean"], dtype=np.float32)) / np.array(self.preprocessor["image_std"], dtype=np.float32)
        tensor = np.ascontiguousarray(pixels.transpose(2, 0, 1)[None], dtype=np.float32)
        logits = self.session.run(None, {self.input_name: tensor})[0][0]
        if logits.shape != (47,) or not np.isfinite(logits).all():
            raise RuntimeError("Invalid model output")
        scores = np.exp(logits - logits.max())
        scores /= scores.sum()
        predictions = [{"label": self.config["id2label"][str(int(i))], "name_ko": KO_NAMES[int(i)],
                        "score": round(float(scores[i]), 6)} for i in scores.argsort()[-3:][::-1]]
        return {"predictions": predictions, "image_size": original_size,
                "uncertain": predictions[0]["score"] < 0.6,
                "notice": "47개 학습 범주 안에서 계산한 추정치입니다. 점수는 정답 확률이나 정확도가 아닙니다. 식물이 아닌 사진과 미지원 식물도 후보가 나올 수 있습니다."}
