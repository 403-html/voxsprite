from __future__ import annotations

import io
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    qt_image = QImage.fromData(buffer.getvalue(), "PNG")
    return QPixmap.fromImage(qt_image)


def load_scaled(path: str, width: int) -> QPixmap:
    pil_image = Image.open(path).convert("RGBA")
    height = int(pil_image.height * (width / pil_image.width))
    resized_image = pil_image.resize((width, height), Image.Resampling.LANCZOS)
    return pil_to_qpixmap(resized_image)
