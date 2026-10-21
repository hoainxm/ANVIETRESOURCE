import cv2
import numpy as np


def enhance_document_image(image_bytes: bytes) -> bytes:
    """Create a mildly sharpened, contrast-balanced copy without altering the source."""
    if not image_bytes:
        raise ValueError("Dữ liệu ảnh CCCD đang rỗng.")

    image = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    if image is None:
        raise ValueError("Không thể giải mã ảnh CCCD để tăng độ rõ.")

    height, width = image.shape[:2]
    shortest_side = min(height, width)
    longest_side = max(height, width)
    scale = max(1.0, min(900 / shortest_side, 3000 / longest_side))
    if scale > 1:
        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    luminance, channel_a, channel_b = cv2.split(lab)
    luminance = cv2.createCLAHE(
        clipLimit=1.5,
        tileGridSize=(8, 8),
    ).apply(luminance)
    balanced = cv2.cvtColor(
        cv2.merge((luminance, channel_a, channel_b)),
        cv2.COLOR_LAB2BGR,
    )

    blurred = cv2.GaussianBlur(balanced, (0, 0), 1.0)
    sharpened = cv2.addWeighted(balanced, 1.35, blurred, -0.35, 0)
    success, encoded = cv2.imencode(
        ".jpg",
        sharpened,
        [cv2.IMWRITE_JPEG_QUALITY, 95],
    )
    if not success:
        raise ValueError("Không thể mã hóa ảnh CCCD đã tăng độ rõ.")
    return encoded.tobytes()
