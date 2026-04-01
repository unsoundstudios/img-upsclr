#!/usr/bin/env python3
"""
Desktop UI for the upscaler script.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from upscaler_core import JobResult, UpscaleConfig, normalize_mode, run_batch


class UpscaleWorker(QObject):
    progress_changed = Signal(int)
    row_ready = Signal(object)
    log = Signal(str)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, config: UpscaleConfig) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:
        try:
            def on_result(index: int, total: int, result: JobResult) -> None:
                percent = int((index / max(total, 1)) * 100)
                self.progress_changed.emit(percent)
                self.row_ready.emit(result)
                line = f"[{result.status.upper()}] {Path(result.source).name}"
                if result.reason:
                    line += f" | {result.reason}"
                self.log.emit(line)

            results = run_batch(self.config, on_result=on_result)
            self.finished.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    ORG = "UnsoundStudios"
    APP = "IMG_UPSCLR"
    VERSION = "0.0.1"
    MAX_IMAGES = 12
    MODE_OPTIONS = [
        ("Smart (Recommended)", "smart"),
        ("Crisp Assets (Logos/UI/Text)", "crisp"),
        ("Photo & Renders (AI)", "photo"),
        ("Classic Script (Original)", "classic"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings(self.ORG, self.APP)
        self.thread: QThread | None = None
        self.worker: UpscaleWorker | None = None
        self.selected_files: list[Path] = []

        self.setWindowTitle("IMG-UPSCLR")
        self.resize(1360, 900)
        self.setMinimumSize(1200, 760)
        self._build_ui()
        self._apply_style()
        self._load_settings()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("rootWidget")
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        hero_box = QGroupBox("IMG-UPSCLR")
        hero_layout = QHBoxLayout(hero_box)
        hero_layout.setContentsMargins(10, 8, 10, 8)
        hero_layout.setSpacing(8)
        hero_label = QLabel(
            "Fast single/batch image upscaling for product assets, photos, and marketing visuals. "
            f"Supports 1 to {self.MAX_IMAGES} images per run."
        )
        hero_label.setWordWrap(True)
        self.selection_label = QLabel("Ready.")
        self.selection_label.setObjectName("selectionLabel")
        hero_layout.addWidget(hero_label, 1)
        hero_layout.addWidget(self.selection_label, 0)
        main_layout.addWidget(hero_box)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)
        main_layout.addLayout(body_layout, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_panel.setMinimumWidth(500)
        body_layout.addWidget(left_panel, 5)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        body_layout.addWidget(right_panel, 7)

        folders_box = QGroupBox("Folders")
        folders_layout = QGridLayout(folders_box)
        folders_layout.setHorizontalSpacing(6)
        folders_layout.setVerticalSpacing(6)

        self.input_edit = QLineEdit(str(Path.cwd()))
        self.output_edit = QLineEdit(str((Path.cwd() / "upscaled_10x").resolve()))
        input_btn = QPushButton("Browse Folder…")
        files_btn = QPushButton("Select Images…")
        output_btn = QPushButton("Browse…")
        input_btn.setMinimumWidth(120)
        files_btn.setMinimumWidth(120)
        output_btn.setMinimumWidth(105)
        input_btn.clicked.connect(self._browse_input)
        files_btn.clicked.connect(self._browse_files)
        output_btn.clicked.connect(self._browse_output)

        folders_layout.addWidget(QLabel("Input"), 0, 0)
        folders_layout.addWidget(self.input_edit, 0, 1)
        folders_layout.addWidget(input_btn, 0, 2)
        folders_layout.addWidget(files_btn, 0, 3)
        folders_layout.addWidget(QLabel("Output"), 1, 0)
        folders_layout.addWidget(self.output_edit, 1, 1, 1, 2)
        folders_layout.addWidget(output_btn, 1, 3)
        folders_layout.addWidget(
            QLabel(f"Input supports single or multiple images (max {self.MAX_IMAGES} per run)."),
            2,
            0,
            1,
            4,
        )
        folders_layout.setColumnStretch(1, 1)
        left_layout.addWidget(folders_box)

        settings_box = QGroupBox("Settings")
        settings_layout = QGridLayout(settings_box)
        settings_layout.setHorizontalSpacing(10)
        settings_layout.setVerticalSpacing(8)

        self.mode_combo = QComboBox()
        for label, value in self.MODE_OPTIONS:
            self.mode_combo.addItem(label, value)
        self.mode_combo.currentIndexChanged.connect(self._update_mode_hint)

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(1.0, 30.0)
        self.scale_spin.setDecimals(2)
        self.scale_spin.setValue(10.0)

        self.max_mp_spin = QDoubleSpinBox()
        self.max_mp_spin.setRange(1.0, 3000.0)
        self.max_mp_spin.setDecimals(1)
        self.max_mp_spin.setValue(600.0)

        self.suffix_edit = QLineEdit("_UPSCALED")

        self.force_large_cb = QCheckBox("Allow extra-large outputs")
        self.include_upscaled_cb = QCheckBox("Include *_UPSCALED files")
        self.overwrite_cb = QCheckBox("Overwrite existing outputs")
        self.dry_run_cb = QCheckBox("Dry-run (plan only)")
        self.artwork_ai_cb = QCheckBox(
            "Enable AI enhancement for photo/render assets (Real-ESRGAN up to 16x)"
        )
        self.artwork_ai_cb.setChecked(True)
        self.artwork_ai_cb.toggled.connect(self._update_mode_hint)

        settings_layout.addWidget(QLabel("Mode"), 0, 0)
        settings_layout.addWidget(self.mode_combo, 0, 1)
        settings_layout.addWidget(QLabel("Scale"), 0, 2)
        settings_layout.addWidget(self.scale_spin, 0, 3)

        settings_layout.addWidget(QLabel("Max Output MP"), 1, 0)
        settings_layout.addWidget(self.max_mp_spin, 1, 1)
        settings_layout.addWidget(QLabel("Suffix"), 1, 2)
        settings_layout.addWidget(self.suffix_edit, 1, 3)

        settings_layout.setColumnStretch(1, 1)
        settings_layout.setColumnStretch(3, 1)

        checks_layout = QGridLayout()
        checks_layout.setHorizontalSpacing(10)
        checks_layout.setVerticalSpacing(6)
        checks_layout.addWidget(self.force_large_cb, 0, 0)
        checks_layout.addWidget(self.include_upscaled_cb, 0, 1)
        checks_layout.addWidget(self.overwrite_cb, 1, 0)
        checks_layout.addWidget(self.dry_run_cb, 1, 1)
        checks_layout.addWidget(self.artwork_ai_cb, 2, 0, 1, 2)
        checks_layout.setColumnStretch(0, 1)
        checks_layout.setColumnStretch(1, 1)
        settings_layout.addLayout(checks_layout, 3, 0, 1, 4)
        self.mode_hint = QLabel("")
        self.mode_hint.setWordWrap(True)
        settings_layout.addWidget(self.mode_hint, 4, 0, 1, 4)
        self._update_mode_hint()

        left_layout.addWidget(settings_box)
        left_layout.addStretch(1)

        controls_box = QGroupBox("Run Job")
        controls_layout = QGridLayout(controls_box)
        controls_layout.setHorizontalSpacing(10)
        controls_layout.setVerticalSpacing(6)
        self.run_button = QPushButton("Start Upscaling")
        self.run_button.clicked.connect(self._start_job)
        self.open_output_button = QPushButton("Open Location")
        self.open_output_button.clicked.connect(self._open_location)
        self.open_legal_button = QPushButton("About")
        self.open_legal_button.clicked.connect(self._show_about_dialog)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        controls_layout.addWidget(self.run_button, 0, 0)
        controls_layout.addWidget(self.open_output_button, 0, 1)
        controls_layout.addWidget(self.open_legal_button, 0, 2)
        controls_layout.addWidget(self.progress, 1, 0, 1, 3)
        right_layout.addWidget(controls_box)

        results_box = QGroupBox("Results")
        results_layout = QVBoxLayout(results_box)
        results_layout.setContentsMargins(8, 8, 8, 8)
        results_layout.setSpacing(8)
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(
            ["Source", "Status", "Profile", "Output", "Reason"]
        )
        self.results_table.setAlternatingRowColors(True)
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        results_layout.addWidget(self.results_table, 1)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Run logs will appear here…")
        self.log_output.setFixedHeight(130)
        results_layout.addWidget(self.log_output)
        right_layout.addWidget(results_box, 1)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget#rootWidget {
                font-family: "Avenir Next", "Segoe UI", sans-serif;
                font-size: 12px;
                background: #08101d;
            }
            QWidget {
                color: #e7eefc;
            }
            QLabel {
                background: transparent;
                color: #dbe6fa;
            }
            QGroupBox {
                font-weight: 600;
                border: 1px solid #263a57;
                border-radius: 10px;
                margin-top: 8px;
                background: #101b2e;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #9ec5ff;
            }
            QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QTableWidget {
                border: 1px solid #304865;
                border-radius: 8px;
                padding: 5px;
                background: #0c1525;
                color: #e9f1ff;
                min-height: 30px;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QTableWidget:focus {
                border: 1px solid #4d7bb3;
            }
            QPushButton {
                border: 0;
                border-radius: 8px;
                padding: 7px 12px;
                background: #2f90ff;
                color: #f7fbff;
                font-weight: 600;
                min-height: 30px;
            }
            QPushButton:hover { background: #2584ef; }
            QPushButton:pressed { background: #1f72d1; }
            QPushButton:disabled { background: #274564; color: #aac2de; }
            QCheckBox {
                spacing: 8px;
                color: #cddaf2;
                padding: 1px 0;
            }
            QProgressBar {
                border: 1px solid #304865;
                border-radius: 8px;
                text-align: center;
                background: #0c1525;
                color: #dce9ff;
            }
            QProgressBar::chunk { border-radius: 7px; background: #36c7a7; }
            QHeaderView::section {
                background: #0f1d32;
                color: #a9c7f2;
                border: 1px solid #304865;
                padding: 6px;
                font-weight: 600;
            }
            QTableWidget {
                gridline-color: #1f314c;
                alternate-background-color: #0f1b2e;
                selection-background-color: #173252;
                selection-color: #e9f3ff;
            }
            QLabel#selectionLabel {
                background: #10233d;
                border: 1px solid #2f5d90;
                border-radius: 7px;
                color: #a8d0ff;
                font-weight: 600;
                padding: 5px 9px;
            }
            """
        )

    def _browse_input(self) -> None:
        current = self.input_edit.text().strip() or str(Path.cwd())
        path = QFileDialog.getExistingDirectory(self, "Select Input Folder", current)
        if path:
            self.selected_files = []
            self.input_edit.setText(path)
            self.selection_label.setText("Folder selected")

    def _browse_files(self) -> None:
        current = str(Path.cwd())
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            f"Select 1 to {self.MAX_IMAGES} images",
            current,
            "Images (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.bmp)",
        )
        if not filenames:
            return
        if len(filenames) > self.MAX_IMAGES:
            QMessageBox.warning(
                self,
                "Too Many Images",
                f"Please select at most {self.MAX_IMAGES} images.",
            )
            return

        self.selected_files = [Path(item) for item in filenames]
        self.input_edit.setText(f"{len(self.selected_files)} selected file(s)")
        self.selection_label.setText(f"{len(self.selected_files)} file(s) selected")

    def _browse_output(self) -> None:
        current = self.output_edit.text().strip() or str(Path.cwd())
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder", current)
        if path:
            self.output_edit.setText(path)

    def _build_config(self) -> UpscaleConfig:
        selected_files = self.selected_files or None
        input_dir = (
            selected_files[0].parent
            if selected_files
            else Path(self.input_edit.text().strip())
        )
        return UpscaleConfig(
            input_dir=input_dir,
            output_dir=Path(self.output_edit.text().strip()),
            selected_files=selected_files,
            scale=self.scale_spin.value(),
            suffix=self.suffix_edit.text().strip() or "_UPSCALED",
            mode=self._mode_value(),
            max_images=self.MAX_IMAGES,
            max_output_megapixels=self.max_mp_spin.value(),
            force_large=self.force_large_cb.isChecked(),
            include_already_upscaled=self.include_upscaled_cb.isChecked(),
            overwrite=self.overwrite_cb.isChecked(),
            dry_run=self.dry_run_cb.isChecked(),
            artwork_ai_enabled=self.artwork_ai_cb.isChecked(),
            artwork_ai_target_scale=16.0,
            auto_install_backend=True,
            esrgan_model_artwork="realesrgan-x4plus",
        )

    def _mode_value(self) -> str:
        value = self.mode_combo.currentData()
        if isinstance(value, str) and value:
            return value
        return normalize_mode(self.mode_combo.currentText())

    def _update_mode_hint(self) -> None:
        mode = self._mode_value()
        ai_on = self.artwork_ai_cb.isChecked()

        mode_text = {
            "smart": "Smart automatically protects crisp assets (logos/UI/text) and uses AI for photo-like assets.",
            "crisp": "Crisp keeps detail-safe upscaling for product graphics, screenshots, labels, and typography.",
            "photo": "Photo applies AI-first upscaling for natural photos, renders, and gradient-heavy assets.",
            "classic": "Classic preserves the original script behavior for deterministic non-AI resizing.",
        }.get(mode, "Smart adaptive mode is active.")

        ai_text = (
            "AI path is enabled: photo/render assets can upscale up to 16x."
            if ai_on
            else "AI path is disabled: all images stay on the original non-AI upscale flow."
        )
        self.mode_hint.setText(f"{mode_text} {ai_text}")

    @staticmethod
    def _kind_label(kind: str | None) -> str:
        mapping = {
            "detail": "crisp-detail",
            "creative": "ai-photo",
            "ui": "ui-legacy",
            "artwork": "artwork-legacy",
        }
        if not kind:
            return ""
        return mapping.get(kind, kind)

    def _open_location(self) -> None:
        output_root = Path(self.output_edit.text().strip()).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)

        selected = self.results_table.selectionModel().selectedRows()
        if selected:
            row = selected[0].row()
            output_item = self.results_table.item(row, 3)
            if output_item and output_item.text().strip():
                candidate = output_root / output_item.text().strip()
                if candidate.exists():
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(candidate.parent)))
                    return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_root)))

    def _show_about_dialog(self) -> None:
        about = QDialog(self)
        about.setWindowTitle("About IMG-UPSCLR")
        about.setModal(True)
        about.resize(640, 360)

        layout = QVBoxLayout(about)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"IMG-UPSCLR v{self.VERSION}")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #eaf2ff;")
        layout.addWidget(title)

        message = QLabel(
            "IMG-UPSCLR is built for production image assets: product shots, UI captures, logos, artwork, and marketing visuals."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        details = QLabel(
            f"Run size: 1 to {self.MAX_IMAGES} images per job\n"
            "Modes: Smart, Crisp, Photo, Classic (legacy mode values are still accepted)\n"
            "Engine: detail-safe upscale + optional Real-ESRGAN AI path for photo/render assets\n"
            "AI target: up to 16x when AI path is enabled\n"
            "Formats: PNG, JPG, JPEG, WEBP, TIFF, BMP"
        )
        details.setWordWrap(True)
        layout.addWidget(details)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(about.accept)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        about.exec()

    def _start_job(self) -> None:
        if self.thread and self.thread.isRunning():
            return
        if self.selected_files and len(self.selected_files) > self.MAX_IMAGES:
            QMessageBox.warning(
                self, "Too Many Images", f"Please select at most {self.MAX_IMAGES} images."
            )
            return

        self._save_settings()
        self.results_table.setRowCount(0)
        self.log_output.clear()
        self.progress.setValue(0)
        self.run_button.setEnabled(False)

        config = self._build_config()
        if config.selected_files:
            self.log_output.append(f"Selected files: {len(config.selected_files)}")
        self.selection_label.setText("Processing…")
        self.worker = UpscaleWorker(config)
        self.thread = QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress_changed.connect(self.progress.setValue)
        self.worker.row_ready.connect(self._append_result_row)
        self.worker.log.connect(self.log_output.append)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_worker)
        self.thread.start()

    def _append_result_row(self, result: JobResult) -> None:
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(Path(result.source).name))
        self.results_table.setItem(row, 1, QTableWidgetItem(result.status))
        self.results_table.setItem(row, 2, QTableWidgetItem(self._kind_label(result.kind)))
        self.results_table.setItem(
            row, 3, QTableWidgetItem(Path(result.output).name if result.output else "")
        )
        self.results_table.setItem(row, 4, QTableWidgetItem(result.reason or ""))

    def _on_finished(self, results: list[JobResult]) -> None:
        self.progress.setValue(100)
        self.run_button.setEnabled(True)
        failed = sum(1 for item in results if item.status == "failed")
        processed = sum(1 for item in results if item.status == "processed")
        skipped = sum(1 for item in results if item.status == "skipped")
        summary = f"Processed {processed} file(s), skipped {skipped}, failed {failed}."
        if failed:
            first_error = next((item.reason for item in results if item.status == "failed"), None)
            if first_error:
                summary = f"{summary}\nFirst error: {first_error}"
        elif processed == 0 and skipped > 0:
            summary = f"{summary}\nNo new files were processed. Check skip reasons in Results."
        self.log_output.append(summary)
        self.selection_label.setText("Done")
        QMessageBox.information(self, "Upscaler Complete", summary)

    def _on_failed(self, message: str) -> None:
        self.run_button.setEnabled(True)
        self.log_output.append(f"[ERROR] {message}")
        self.selection_label.setText("Failed")
        QMessageBox.critical(self, "Upscaler Failed", message)

    def _cleanup_worker(self) -> None:
        if self.worker:
            self.worker.deleteLater()
        if self.thread:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None

    def _load_settings(self) -> None:
        self.selected_files = []
        self.input_edit.setText(self.settings.value("input", self.input_edit.text()))
        self.output_edit.setText(self.settings.value("output", self.output_edit.text()))
        saved_mode = normalize_mode(str(self.settings.value("mode", "smart")))
        mode_index = self.mode_combo.findData(saved_mode)
        if mode_index < 0:
            mode_index = self.mode_combo.findData("smart")
        self.mode_combo.setCurrentIndex(mode_index)
        self.scale_spin.setValue(float(self.settings.value("scale", 10.0)))
        self.max_mp_spin.setValue(float(self.settings.value("max_mp", 600.0)))
        self.suffix_edit.setText(self.settings.value("suffix", "_UPSCALED"))
        self.force_large_cb.setChecked(self.settings.value("force_large", False, type=bool))
        self.include_upscaled_cb.setChecked(
            self.settings.value("include_upscaled", False, type=bool)
        )
        self.overwrite_cb.setChecked(self.settings.value("overwrite", False, type=bool))
        self.dry_run_cb.setChecked(self.settings.value("dry_run", False, type=bool))
        self.artwork_ai_cb.setChecked(self.settings.value("artwork_ai", True, type=bool))
        self._update_mode_hint()
        self.selection_label.setText("Ready.")

    def _save_settings(self) -> None:
        if not self.selected_files:
            self.settings.setValue("input", self.input_edit.text().strip())
        self.settings.setValue("output", self.output_edit.text().strip())
        self.settings.setValue("mode", self._mode_value())
        self.settings.setValue("scale", self.scale_spin.value())
        self.settings.setValue("max_mp", self.max_mp_spin.value())
        self.settings.setValue("suffix", self.suffix_edit.text().strip())
        self.settings.setValue("force_large", self.force_large_cb.isChecked())
        self.settings.setValue("include_upscaled", self.include_upscaled_cb.isChecked())
        self.settings.setValue("overwrite", self.overwrite_cb.isChecked())
        self.settings.setValue("dry_run", self.dry_run_cb.isChecked())
        self.settings.setValue("artwork_ai", self.artwork_ai_cb.isChecked())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_settings()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("IMG-UPSCLR")
    app.setOrganizationName(MainWindow.ORG)
    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
