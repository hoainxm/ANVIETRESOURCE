import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.image_preprocessing import enhance_document_image


class ImagePreprocessingTests(unittest.TestCase):
    def test_enhancement_returns_upscaled_jpeg_for_small_card_image(self):
        image = np.full((120, 240, 3), 220, dtype=np.uint8)
        cv2.putText(
            image,
            "CCCD 012345678901",
            (8, 64),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (20, 20, 20),
            1,
        )
        success, encoded = cv2.imencode(".png", image)
        self.assertTrue(success)

        enhanced = enhance_document_image(encoded.tobytes())

        self.assertTrue(enhanced.startswith(b"\xff\xd8\xff"))
        decoded = cv2.imdecode(
            np.frombuffer(enhanced, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        self.assertEqual(decoded.shape[:2], (900, 1800))

    def test_enhancement_rejects_invalid_image_bytes(self):
        with self.assertRaisesRegex(ValueError, "Không thể giải mã"):
            enhance_document_image(b"not-an-image")


if __name__ == "__main__":
    unittest.main()
