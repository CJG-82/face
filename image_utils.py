"""이미지 전처리 유틸리티 (API 없이 테스트 가능)."""

import base64
import hashlib
import io

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_PIXELS = 40_000_000  # 약 4000만 화소 (최신 휴대폰 사진보다 넉넉함)
MAX_SIDE = 1024
JPEG_QUALITY = 85


class ImageProcessingError(Exception):
    """이미지를 열거나 변환할 수 없을 때 발생한다."""


class ImageTooLargeError(ImageProcessingError):
    """해상도(픽셀 수)가 너무 클 때 발생한다. 압축 폭탄 이미지 방어용."""


def is_size_ok(num_bytes: int, limit: int = MAX_FILE_BYTES) -> bool:
    """파일 크기가 제한 이하인지 확인한다."""
    return 0 < num_bytes <= limit


def preprocess_image(image_bytes: bytes, max_side: int = MAX_SIDE, max_pixels: int = MAX_PIXELS) -> bytes:
    """EXIF 회전 보정, RGB 변환, 긴 변 max_side 이하로 축소한 뒤 JPEG 바이트로 반환한다."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Image.open은 헤더만 읽으므로, 픽셀을 디코딩하기 전에 해상도를 검사한다.
            if img.width * img.height > max_pixels:
                raise ImageTooLargeError("이미지 해상도가 너무 큽니다.")
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                # 투명 배경은 흰색으로 채운다.
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    rgba = img.convert("RGBA")
                    background = Image.new("RGB", rgba.size, (255, 255, 255))
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    img = background
                else:
                    img = img.convert("RGB")
            img.thumbnail((max_side, max_side), Image.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=JPEG_QUALITY)
            return out.getvalue()
    except ImageProcessingError:
        raise
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError("이미지 해상도가 너무 큽니다.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise ImageProcessingError("이미지를 열 수 없습니다.") from exc


def to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def image_hash(data: bytes) -> str:
    """같은 이미지인지 판별하기 위한 해시 (이미지 자체는 저장하지 않음)."""
    return hashlib.sha256(data).hexdigest()
