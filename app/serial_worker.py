"""Wątek odbierający linie z portu szeregowego."""
from __future__ import annotations

import threading

import serial
from PySide6.QtCore import QThread, Signal


class SerialReader(QThread):
    line_received = Signal(str)
    connection_opened = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, port: str, baud_rate: int) -> None:
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self._stop_event = threading.Event()

    def run(self) -> None:
        device = None
        try:
            device = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=0.15,
                write_timeout=0.5,
            )
            self.connection_opened.emit(self.port)
            while not self._stop_event.is_set():
                raw = device.readline()
                if raw:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        self.line_received.emit(line)
        except (serial.SerialException, OSError, ValueError) as exc:
            if not self._stop_event.is_set():
                self.error_occurred.emit(str(exc))
        finally:
            if device is not None:
                try:
                    device.close()
                except serial.SerialException:
                    pass

    def stop(self) -> None:
        self._stop_event.set()
        self.wait(1800)
