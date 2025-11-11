from __future__ import annotations

import queue
import numpy as np
import sounddevice as sound_device
from PyQt6.QtWidgets import QMessageBox

from .i18n import t


class Mic:
    def __init__(self) -> None:
        self._rms_queue: "queue.Queue[float]" = queue.Queue()
        self.stream = None
        try:
            self.stream = sound_device.InputStream(channels=1, callback=self._stream_callback)
            self.stream.start()
        except Exception as exception_instance:
            QMessageBox.critical(
                None,
                t("audio.error.title"),
                t("audio.error.open_stream", error=exception_instance),
            )
            raise

    def _stream_callback(self, input_data, frames: int, timestamp, status) -> None:
        del frames, timestamp, status
        if input_data is None or not len(input_data):
            return
        root_mean_square = float(np.sqrt(np.mean(np.square(input_data))) + 1e-6)
        self._rms_queue.put(root_mean_square)

    def read(self) -> float:
        latest_value = 0.0
        try:
            while True:
                latest_value = self._rms_queue.get_nowait()
        except queue.Empty:
            pass
        return latest_value
