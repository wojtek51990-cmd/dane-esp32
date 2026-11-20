"""Główne okno ESP32 Data Monitor."""
from __future__ import annotations

import csv
from collections import deque
from datetime import datetime
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)
from serial.tools import list_ports

from app.data_parser import DataParser
from app.serial_worker import SerialReader


DARK_STYLE = """
QWidget { background: #111827; color: #e5e7eb; font-family: Segoe UI; font-size: 10pt; }
QMainWindow { background: #0b1220; }
QFrame#Panel { background: #172033; border: 1px solid #263449; border-radius: 10px; }
QLabel#Title { color: #f9fafb; font-size: 20pt; font-weight: 700; }
QLabel#Subtitle { color: #9ca3af; font-size: 9pt; }
QLabel#Section { color: #cbd5e1; font-size: 9pt; font-weight: 600; }
QLabel#MetricName { color: #9ca3af; font-size: 9pt; }
QLabel#MetricValue { color: #f9fafb; font-size: 18pt; font-weight: 700; }
QLabel#Status { color: #93c5fd; font-weight: 600; }
QPushButton {
  background: #263449; color: #f9fafb; border: 1px solid #3b4b63;
  border-radius: 7px; padding: 8px 14px; font-weight: 600;
}
QPushButton:hover { background: #344761; }
QPushButton:disabled { color: #64748b; background: #1f2937; }
QPushButton#Primary { background: #2563eb; border-color: #3b82f6; }
QPushButton#Primary:hover { background: #1d4ed8; }
QComboBox {
  background: #0f172a; border: 1px solid #3b4b63; border-radius: 7px;
  padding: 7px; min-width: 105px;
}
QComboBox QAbstractItemView { background: #172033; selection-background-color: #2563eb; }
"""


class MetricCard(QFrame):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)
        self.name_label = QLabel(name)
        self.name_label.setObjectName("MetricName")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("MetricValue")
        self.value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.name_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: float) -> None:
        self.value_label.setText(f"{value:.3f}".rstrip("0").rstrip("."))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ESP32 Data Monitor")
        self.resize(1180, 760)
        self.setMinimumSize(850, 580)
        self.setStyleSheet(DARK_STYLE)

        self.parser = DataParser()
        self.reader: SerialReader | None = None
        self.paused = False
        self.sample_index = 0
        self.series: dict[str, deque[tuple[int, float]]] = {}
        self.curves: dict[str, pg.PlotDataItem] = {}
        self.metrics: dict[str, MetricCard] = {}
        self.history: list[tuple[str, dict[str, float]]] = []
        self.max_history = 50000

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(13)

        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("ESP32 Data Monitor")
        title.setObjectName("Title")
        subtitle = QLabel("Odczyt USB • wykresy na żywo • eksport danych")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading.addLayout(title_box)
        heading.addStretch()
        self.status_label = QLabel("Nie połączono")
        self.status_label.setObjectName("Status")
        heading.addWidget(self.status_label, alignment=Qt.AlignVCenter)
        root.addLayout(heading)

        controls = QFrame()
        controls.setObjectName("Panel")
        control_layout = QHBoxLayout(controls)
        control_layout.setContentsMargins(14, 12, 14, 12)
        control_layout.setSpacing(9)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        self.refresh_button = QPushButton("Odśwież")
        self.baud_combo = QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems([
            "9600", "19200", "38400", "57600", "115200",
            "230400", "460800", "921600"
        ])
        self.baud_combo.setCurrentText("115200")
        self.connect_button = QPushButton("Połącz")
        self.connect_button.setObjectName("Primary")
        self.disconnect_button = QPushButton("Rozłącz")
        self.disconnect_button.setEnabled(False)
        self.pause_button = QPushButton("Pauza")
        self.pause_button.setEnabled(False)
        self.clear_button = QPushButton("Wyczyść")
        self.export_button = QPushButton("Zapisz CSV")

        control_layout.addWidget(self._captioned("Port COM", self.port_combo))
        control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self._captioned("Prędkość", self.baud_combo))
        control_layout.addWidget(self.connect_button)
        control_layout.addWidget(self.disconnect_button)
        control_layout.addStretch(1)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.clear_button)
        control_layout.addWidget(self.export_button)
        root.addWidget(controls)

        self.metrics_frame = QFrame()
        self.metrics_layout = QHBoxLayout(self.metrics_frame)
        self.metrics_layout.setContentsMargins(0, 0, 0, 0)
        self.metrics_layout.setSpacing(10)
        self.metrics_layout.addStretch()
        root.addWidget(self.metrics_frame)

        plot_panel = QFrame()
        plot_panel.setObjectName("Panel")
        plot_layout = QVBoxLayout(plot_panel)
        plot_layout.setContentsMargins(12, 10, 12, 12)
        plot_header = QHBoxLayout()
        plot_title = QLabel("Przebieg sygnałów")
        plot_title.setObjectName("Section")
        self.samples_label = QLabel("Odebrane próbki: 0")
        self.samples_label.setObjectName("Subtitle")
        plot_header.addWidget(plot_title)
        plot_header.addStretch()
        plot_header.addWidget(self.samples_label)
        plot_layout.addLayout(plot_header)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("#0f172a")
        self.plot.showGrid(x=True, y=True, alpha=0.22)
        self.plot.setLabel("bottom", "Numer próbki")
        self.plot.setLabel("left", "Wartość")
        self.plot.getAxis("left").setTextPen("#cbd5e1")
        self.plot.getAxis("bottom").setTextPen("#cbd5e1")
        self.plot.getAxis("left").setPen("#475569")
        self.plot.getAxis("bottom").setPen("#475569")
        self.plot.addLegend(offset=(10, 10), labelTextColor="#e5e7eb")
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_layout.addWidget(self.plot)
        root.addWidget(plot_panel, 1)

        self.refresh_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.connect_serial)
        self.disconnect_button.clicked.connect(self.disconnect_serial)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.clear_button.clicked.connect(self.clear_data)
        self.export_button.clicked.connect(self.export_csv)

        self.plot_timer = QTimer(self)
        self.plot_timer.setInterval(100)
        self.plot_timer.timeout.connect(self.refresh_plot)
        self.plot_timer.start()

        self.refresh_ports()

    @staticmethod
    def _captioned(caption: str, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        label = QLabel(caption)
        label.setObjectName("Section")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def refresh_ports(self) -> None:
        current = self.port_combo.currentData() or self.port_combo.currentText()
        self.port_combo.clear()
        ports = sorted(list_ports.comports(), key=lambda item: item.device)
        for port in ports:
            description = f"{port.device} — {port.description}"
            self.port_combo.addItem(description, port.device)
        if current:
            index = self.port_combo.findData(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
        if not ports:
            self.port_combo.addItem("Nie wykryto portu", "")
            self.port_combo.setEnabled(False)
        else:
            self.port_combo.setEnabled(True)

    def connect_serial(self) -> None:
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.warning(
                self, "Brak portu",
                "Nie wykryto portu COM. Podłącz ESP32 i kliknij Odśwież."
            )
            return
        try:
            baud_rate = int(self.baud_combo.currentText().strip())
            if baud_rate <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(
                self, "Błędna prędkość",
                "Wpisz poprawną dodatnią prędkość transmisji."
            )
            return

        self.reader = SerialReader(port, baud_rate)
        self.reader.connection_opened.connect(self.on_connected)
        self.reader.line_received.connect(self.on_line_received)
        self.reader.error_occurred.connect(self.on_serial_error)
        self.reader.finished.connect(self.on_reader_finished)
        self.reader.start()
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.pause_button.setEnabled(True)
        self.refresh_button.setEnabled(False)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.status_label.setText(f"Łączenie z {port}…")

    def on_connected(self, port: str) -> None:
        self.status_label.setText(f"Połączono: {port}")

    def disconnect_serial(self) -> None:
        reader = self.reader
        if reader is not None:
            reader.stop()
            self.reader = None
        self._set_disconnected()

    def on_reader_finished(self) -> None:
        if self.reader is not None and not self.reader.isRunning():
            self.reader = None
            self._set_disconnected()

    def on_serial_error(self, message: str) -> None:
        self.status_label.setText("Błąd połączenia")
        QMessageBox.warning(
            self, "Błąd portu szeregowego",
            "Nie można odczytać danych z portu COM.\n\n"
            f"{message}\n\nSprawdź przewód, port i czy inny program nie używa COM."
        )

    def _set_disconnected(self) -> None:
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pauza")
        self.refresh_button.setEnabled(True)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.paused = False
        self.status_label.setText("Nie połączono")

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.setText("Wznów" if self.paused else "Pauza")
        self.status_label.setText(
            "Wstrzymano zapis" if self.paused else "Odbieranie danych"
        )

    def on_line_received(self, line: str) -> None:
        if self.paused:
            return
        values = self.parser.parse(line)
        if not values:
            return

        self.sample_index += 1
        timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
        self.history.append((timestamp, values.copy()))
        if len(self.history) > self.max_history:
            del self.history[:len(self.history) - self.max_history]

        for name, value in values.items():
            if name not in self.series:
                self.series[name] = deque(maxlen=2500)
                curve = self.plot.plot(
                    [], [], name=name,
                    pen=pg.mkPen(
                        pg.intColor(len(self.curves), hues=12, values=1, maxValue=220),
                        width=2,
                    ),
                )
                self.curves[name] = curve
                card = MetricCard(name)
                self.metrics[name] = card
                self.metrics_layout.insertWidget(
                    self.metrics_layout.count() - 1, card, 1
                )
            self.series[name].append((self.sample_index, value))
            self.metrics[name].set_value(value)

        self.samples_label.setText(f"Odebrane próbki: {self.sample_index}")

    def refresh_plot(self) -> None:
        for name, points in self.series.items():
            if points:
                x_values, y_values = zip(*points)
                self.curves[name].setData(x_values, y_values)

    def clear_data(self) -> None:
        self.sample_index = 0
        self.history.clear()
        for points in self.series.values():
            points.clear()
        for curve in self.curves.values():
            curve.setData([], [])
        for card in self.metrics.values():
            card.set_value(0.0)
        self.samples_label.setText("Odebrane próbki: 0")

    def export_csv(self) -> None:
        if not self.history:
            QMessageBox.information(
                self, "Brak danych", "Nie ma jeszcze danych do zapisania."
            )
            return
        default_name = f"esp32_dane_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz dane", str(Path.home() / default_name),
            "Pliki CSV (*.csv)"
        )
        if not path:
            return

        channel_names = sorted({key for _, row in self.history for key in row})
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.DictWriter(
                    output, fieldnames=["czas", *channel_names], delimiter=";"
                )
                writer.writeheader()
                for timestamp, row in self.history:
                    record = {"czas": timestamp}
                    record.update(row)
                    writer.writerow(record)
        except OSError as exc:
            QMessageBox.critical(
                self, "Błąd zapisu", f"Nie udało się zapisać pliku:\n{exc}"
            )
            return

        self.status_label.setText(f"Zapisano: {Path(path).name}")
        QMessageBox.information(self, "Zapisano", f"Dane zapisano do pliku:\n{path}")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.reader is not None:
            self.reader.stop()
            self.reader = None
        event.accept()
