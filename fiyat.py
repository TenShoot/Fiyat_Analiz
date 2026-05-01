import sys
import random
import json
import os
import csv
import math
import uuid
import hashlib
import ast
from datetime import datetime

# -------------------- Qt Imports (TEK BLOK) --------------------
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QPoint
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QPainterPath,
    QPageSize,
    QRegion,
    QFontMetricsF,
    QPixmap,
    QImage,
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLineEdit,
    QMessageBox,
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QCheckBox,
    QFileDialog,
    QSizePolicy,
    QListWidget,
    QComboBox,
    QInputDialog,
    QRadioButton,
    QButtonGroup,
)


from PyQt6.QtPrintSupport import QPrinter

# -------------------------------------------------
#  MAKİNE ID + LİSANS KONTROLÜ
# -------------------------------------------------

# Bu tuz sadece sende kalacak (lisans_uret.py ile aynı olmalı)
SECRET_SALT = "TenShoot-2026"


def get_machine_id() -> str:
    """
    Bu bilgisayar için benzersiz bir makine ID üret.
    uuid.getnode() MAC tabanlı bir integer döndürür.
    """
    try:
        mac_int = uuid.getnode()
        mac_hex = f"{mac_int:012X}"
        mac_str = ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
        return mac_str
    except Exception:
        return "UNKNOWN"


def get_app_base_dir() -> str:
    """
    - Normal .py çalışırken: fiyat.py'nin olduğu klasör
    - PyInstaller EXE iken: exe'nin durduğu klasör
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_license_path() -> str:
    """Platform'a göre lisans dosyası yolu: Mac → license_mac.ten, diğer → license.ten"""
    fname = "license_mac.ten" if sys.platform == "darwin" else "license.ten"
    return os.path.join(get_app_base_dir(), fname)


def verify_license() -> bool:
    """
    - Mac: license_mac.ten  |  Windows/diğer: license.ten
    - Dosya yoksa: Makine ID göster, False dön
    - varsa: SHA256 ile karşılaştır
    """
    machine_id = get_machine_id()
    lic_path = get_license_path()
    lic_fname = os.path.basename(lic_path)

    if not os.path.exists(lic_path):
        QMessageBox.critical(
            None,
            "Lisans bulunamadı",
            (
                f"Bu bilgisayar için lisans dosyası bulunamadı ({lic_fname}).\n\n"
                f"Makine ID:\n{machine_id}\n\n"
                "Bu ID'yi Uğur'a gönderin."
            ),
        )
        return False

    try:
        with open(lic_path, "r", encoding="utf-8") as f:
            stored = f.read().strip()
    except Exception as e:
        QMessageBox.critical(None, "Lisans okunamadı", f"Lisans dosyası açılamadı:\n{e}")
        return False

    expected = hashlib.sha256((machine_id + SECRET_SALT).encode("utf-8")).hexdigest()
    if stored.lower() != expected.lower():
        QMessageBox.critical(
            None,
            "Lisans geçersiz",
            (
                f"Bu lisans bu bilgisayar için geçerli değil ({lic_fname}).\n\n"
                f"Bu bilgisayarın Makine ID'si:\n{machine_id}\n\n"
                f"Bu ID ile yeni bir {lic_fname} oluşturup tekrar deneyin."
            ),
        )
        return False

    return True


class SketchConfirmDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kategoriyi sil")
        self.setModal(True)

        # Genel görünüm – beyaz arka plan, koyu çizgili çerçeve
        self.setStyleSheet("""
        QDialog {
            background-color: white;
            border: 2px solid #444444;
            color: #000000;  /* Varsayılan metin rengi */
        }

        QLabel, QLineEdit, QPushButton {
            font-family: "DIN Alternate", "Noteworthy", "Bradley Hand", "Segoe Print", "Comic Sans MS", sans-serif;
        }

        QLabel {
            font-size: 14pt;
            color: #222222;
        }

        QLineEdit {
            font-size: 12pt;
            padding: 4px 8px;
            border: 2px solid #444444;
            border-radius: 8px;
            background-color: white;
            color: #222222;
        }

        QPushButton {
            font-size: 12pt;
            padding: 8px 18px;
            border: 2px solid #444444;
            border-radius: 16px;
            background-color: white;
            color: #222222;   /* Buton yazısı da koyu olsun */
        }

        QPushButton#okButton {
            color: #b00000;
            border-color: #b00000;
        }

        QPushButton#cancelButton {
            color: #004488;
            border-color: #004488;
        }

        QPushButton:hover {
            background-color: #f5f5f5;
        }
        """)


        label = QLabel(text)
        label.setWordWrap(True)

        ok_btn = QPushButton("Onay")
        ok_btn.setObjectName("okButton")
        cancel_btn = QPushButton("Vazgeç")
        cancel_btn.setObjectName("cancelButton")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addSpacing(10)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.resize(380, 150)


class SketchCategoryDialog(QDialog):
    """
    Yeni kategori ekleme / düzenleme diyaloğu.
    - Malzeme: Ad, Birim, Fiyat + Plaka ebatı, Ortalama ölçü, Tahmini fire, R-90°
    - İşçilik: Ad, Birim, Fiyat
    """

    def __init__(self, parent=None, group: str = "material"):
        super().__init__(parent)
        self.group = group  # "material" veya "labor"

        self.setWindowTitle("Yeni Kategori")
        self.setModal(True)

        self.setStyleSheet("""
        QDialog {
            background-color: white;
            border: 2px solid #444444;
            color: #000000;
        }

        QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox {
            font-family: "DIN Alternate", "Noteworthy", "Bradley Hand", "Segoe Print", "Comic Sans MS", sans-serif;
        }

        QLabel {
            font-size: 13pt;
            color: #222222;
        }

        QLineEdit {
            font-size: 12pt;
            padding: 6px 10px;
            border: 2px solid #444444;
            border-radius: 8px;
            background-color: white;
            color: #222222;
        }

        
        QComboBox {
            font-size: 12pt;
            padding: 6px 10px;
            border: 2px solid #444444;
            border-radius: 8px;
            background-color: white;
            color: #222222;
        }

        QComboBox QAbstractItemView {
            background-color: white;
            color: #111111;
            selection-background-color: #eaf2ff;
            selection-color: #111111;
        }

QPushButton {
            font-size: 12pt;
            padding: 8px 18px;
            border: 2px solid #444444;
            border-radius: 16px;
            background-color: white;
            color: #222222;
        }

        QPushButton#okButton {
            color: #b00000;
            border-color: #b00000;
        }

        QPushButton#cancelButton {
            color: #004488;
            border-color: #004488;
        }

        QPushButton#rotateButton {
            padding: 4px 10px;
            border-radius: 14px;
        }

        QPushButton#rotateButton:checked {
            background-color: #e0e0e0;
        }

        QPushButton:hover {
            background-color: #f5f5f5;
        }
        """)

        main_layout = QVBoxLayout(self)

        # Başlık
        title = QLabel(
            "Yeni MALZEME kategorisi ekle"
            if self.group == "material"
            else "Yeni İŞÇİLİK kategorisi ekle"
        )
        title.setWordWrap(True)
        main_layout.addWidget(title)
        main_layout.addSpacing(8)

        # Ortak alanlar (Ad / Birim / Fiyat)
        name_label = QLabel("Ad:")
        unit_label = QLabel("Birim:")
        price_label = QLabel("Birim fiyat:")
        currency_label = QLabel("Para birimi:")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(
            "Örneğin: Amasya Bej 3 cm" if self.group == "material" else "Örneğin: Özel İşçilik"
        )

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("m², mt, saat...")

        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText("örn: 100,00")

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["TL", "USD", "EUR"])
        self.currency_combo.setCurrentText("USD")

        row1 = QHBoxLayout()
        row1.addWidget(name_label)
        row1.addWidget(self.name_edit)

        row2 = QHBoxLayout()
        row2.addWidget(unit_label)
        row2.addWidget(self.unit_edit)

        row3 = QHBoxLayout()
        row3.addWidget(price_label)
        row3.addWidget(self.price_edit)

        row3b = QHBoxLayout()
        row3b.addWidget(currency_label)
        row3b.addWidget(self.currency_combo)

        main_layout.addLayout(row1)
        main_layout.addLayout(row2)
        main_layout.addLayout(row3)
        main_layout.addLayout(row3b)

        # --- Malzeme için ek alanlar ---
        self.plate_w_edit = None
        self.plate_h_edit = None
        self.avg_w_edit = None
        self.avg_h_edit = None
        self.waste_edit = None
        self.fire_button = None
        self.rotate_button = None  # toggle buton

        if self.group == "material":
            self.plate_w_edit = QLineEdit()
            self.plate_h_edit = QLineEdit()
            self.avg_w_edit = QLineEdit()
            self.avg_h_edit = QLineEdit()
            self.waste_edit = QLineEdit()
            self.fire_button = QPushButton("Fire hesapla")

            # R-90° için küçük toggle buton
            self.rotate_button = QPushButton("R-90°")
            self.rotate_button.setObjectName("rotateButton")
            self.rotate_button.setCheckable(True)
            self.rotate_button.setChecked(True)   # varsayılan: döndürme açık
            self.rotate_button.setMinimumWidth(60)

            self.plate_w_edit.setPlaceholderText("örn: 120")
            self.plate_h_edit.setPlaceholderText("örn: 240")
            self.avg_w_edit.setPlaceholderText("örn: 60")
            self.avg_h_edit.setPlaceholderText("örn: 60")
            self.waste_edit.setPlaceholderText("örn: 15,0")

            # Plaka satırı
            plate_label = QLabel("Plaka ebatı (En x Boy):")
            row4 = QHBoxLayout()
            row4.addWidget(plate_label)
            row4.addWidget(self.plate_w_edit)
            row4.addWidget(self.plate_h_edit)

            # Ortalama ölçü satırı
            avg_label = QLabel("Ort. ölçü (En x Boy):")
            row5 = QHBoxLayout()
            row5.addWidget(avg_label)
            row5.addWidget(self.avg_w_edit)
            row5.addWidget(self.avg_h_edit)

            # Fire satırı + R-90° butonu
            waste_label = QLabel("Tahmini fire %:")
            row6 = QHBoxLayout()
            row6.addWidget(waste_label)
            row6.addWidget(self.waste_edit)
            row6.addWidget(self.fire_button)
            row6.addWidget(self.rotate_button)
            row6.addStretch()

            self.fire_button.clicked.connect(self.calculate_waste)

            main_layout.addSpacing(6)
            main_layout.addLayout(row4)
            main_layout.addLayout(row5)
            main_layout.addLayout(row6)

        # OK / Vazgeç
        ok_btn = QPushButton("Onay")
        ok_btn.setObjectName("okButton")
        cancel_btn = QPushButton("Vazgeç")
        cancel_btn.setObjectName("cancelButton")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        main_layout.addSpacing(10)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.adjustSize()
        if self.group == "material":
            self.setMinimumWidth(650)
            self.setMinimumHeight(320)
        else:
            self.setMinimumWidth(500)

    # ---------- Yardımcı parse / format ----------

    def _parse_decimal(self, text: str, default: float = 0.0) -> float:
        txt = (text or "").strip()
        if not txt:
            return default
        txt = txt.replace(".", "").replace(",", ".")
        try:
            return float(txt)
        except ValueError:
            return default

    def _format_decimal(self, value: float) -> str:
        try:
            return f"{float(value):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return "0,00"

    # ---------- Fire hesapla ----------

    def calculate_waste(self):
        if self.group != "material":
            return

        if not all([self.plate_w_edit, self.plate_h_edit, self.avg_w_edit, self.avg_h_edit, self.waste_edit]):
            return

        pw = self._parse_decimal(self.plate_w_edit.text(), 0.0)
        ph = self._parse_decimal(self.plate_h_edit.text(), 0.0)
        aw = self._parse_decimal(self.avg_w_edit.text(), 0.0)
        ah = self._parse_decimal(self.avg_h_edit.text(), 0.0)

        if pw <= 0 or ph <= 0 or aw <= 0 or ah <= 0:
            QMessageBox.warning(self, "Hatalı veri", "Plaka ve ortalama ölçüleri pozitif sayı olarak gir.")
            return

        plate_area = pw * ph
        part_area = aw * ah
        if part_area <= 0:
            QMessageBox.warning(self, "Hatalı veri", "Ortalama parça alanı sıfır olamaz.")
            return

        # 1) Düz yerleşim
        fit_x1 = max(0, math.floor(pw / aw))
        fit_y1 = max(0, math.floor(ph / ah))
        usable_pieces1 = fit_x1 * fit_y1
        usable_area1 = usable_pieces1 * part_area
        usable_area = usable_area1

        # 2) R-90° aktifse 90° çevrilmiş hali de dene
        if self.rotate_button is not None and self.rotate_button.isChecked():
            fit_x2 = max(0, math.floor(pw / ah))
            fit_y2 = max(0, math.floor(ph / aw))
            usable_pieces2 = fit_x2 * fit_y2
            usable_area2 = usable_pieces2 * part_area
            usable_area = max(usable_area1, usable_area2)

        if usable_area <= 0 or usable_area > plate_area:
            QMessageBox.warning(self, "Hesaplanamadı", "Bu ölçülerle plaka üzerine parça yerleşimi hesaplanamadı.")
            return

        waste_ratio = 1.0 - (usable_area / plate_area)
        waste_percent = max(0.0, min(100.0, waste_ratio * 100.0))
        self.waste_edit.setText(f"{waste_percent:.1f}".replace(".", ","))

    # ---------- Düzenleme için başlangıç değerleri ----------

    def set_initial_values(self, data: dict):
        """Varolan bir kategoriyi düzenlerken alanları doldurmak için."""
        self.name_edit.setText(str(data.get("name", "")))
        self.unit_edit.setText(str(data.get("unit", "")))

        try:
            price_val = float(data.get("price", 0.0))
        except (TypeError, ValueError):
            price_val = 0.0
        self.price_edit.setText(self._format_decimal(price_val))
        curr = str(data.get("currency", "USD") or "USD").upper()
        self.currency_combo.setCurrentText(curr if curr in ("TL", "USD", "EUR") else "USD")

        if self.group == "material":
            if self.plate_w_edit is not None:
                self.plate_w_edit.setText(self._format_decimal(data.get("plate_width", 0.0)))
            if self.plate_h_edit is not None:
                self.plate_h_edit.setText(self._format_decimal(data.get("plate_height", 0.0)))
            if self.avg_w_edit is not None:
                self.avg_w_edit.setText(self._format_decimal(data.get("avg_width", 0.0)))
            if self.avg_h_edit is not None:
                self.avg_h_edit.setText(self._format_decimal(data.get("avg_height", 0.0)))
            if self.waste_edit is not None:
                self.waste_edit.setText(self._format_decimal(data.get("waste_percent", 0.0)))
            if self.rotate_button is not None:
                self.rotate_button.setChecked(bool(data.get("rotate_allowed", True)))

    # ---------- Sonuç ----------

    def get_values(self):
        name = self.name_edit.text().strip()
        unit = self.unit_edit.text().strip()
        price = self._parse_decimal(self.price_edit.text(), 0.0)
        currency = str(self.currency_combo.currentText() or "USD").upper()
        if currency not in ("TL", "USD", "EUR"):
            currency = "USD"

        data = {"name": name, "unit": unit, "price": price, "currency": currency}

        if self.group == "material":
            pw = ph = aw = ah = waste = 0.0
            rotate = True

            if self.plate_w_edit is not None:
                pw = self._parse_decimal(self.plate_w_edit.text(), 0.0)
            if self.plate_h_edit is not None:
                ph = self._parse_decimal(self.plate_h_edit.text(), 0.0)
            if self.avg_w_edit is not None:
                aw = self._parse_decimal(self.avg_w_edit.text(), 0.0)
            if self.avg_h_edit is not None:
                ah = self._parse_decimal(self.avg_h_edit.text(), 0.0)
            if self.waste_edit is not None:
                waste = self._parse_decimal(self.waste_edit.text(), 0.0)
            if self.rotate_button is not None:
                rotate = self.rotate_button.isChecked()

            data.update(
                {
                    "plate_width": pw,
                    "plate_height": ph,
                    "avg_width": aw,
                    "avg_height": ah,
                    "waste_percent": waste,
                    "rotate_allowed": rotate,
                }
            )

        return data


class SketchFreeWasteDialog(QDialog):
    """
    SERBEST FIRE HESAPLA
    - Plaka ölçüsü (en x boy)
    - Kesim payı (mm)
    - R-90° (döndürme serbest)
    - Çok satırlı parça listesi: en, boy, adet  (+ ile satır ekle, - ile satır sil)
    - Hesapla: kaç plaka gerekli + fire %
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serbest Fire Hesapla")
        self.setModal(True)

        self.setStyleSheet("""
        QDialog {
            background-color: white;
            color: #000000;
        }
        QLabel, QLineEdit, QPushButton, QCheckBox, QRadioButton {
            font-family: "Segoe UI", "Calibri", "DIN Alternate", Arial, sans-serif;
            font-size: 11pt;
            color: #222222;
        }
        QLabel { font-size: 11pt; color: #222222; }
        QLineEdit {
            font-size: 12pt;
            padding: 6px 10px;
            border: 2px solid #444444;
            border-radius: 8px;
            background-color: white;
            color: #222222;
        }
        QPushButton {
            font-size: 12pt;
            padding: 8px 18px;
            border: 2px solid #444444;
            border-radius: 16px;
            background-color: white;
            color: #222222;
        }
        QPushButton:hover { background-color: #f5f5f5; }
        QPushButton#calcButton { color:#b00000; border-color:#b00000; }
        QPushButton#closeButton { color:#004488; border-color:#004488; }
        QPushButton#pdfButton  { color:#222222; border-color:#444444; }
        QPushButton#miniButton {
            padding: 2px 10px;
            border-radius: 14px;
            min-width: 36px;
        }
        QPushButton#miniButton:hover { background-color:#f2f2f2; }
        QPushButton#rotateButton {
            padding: 4px 10px;
            border-radius: 14px;
        }
        QPushButton#rotateButton:checked { background-color: #e0e0e0; }
        QRadioButton {
            font-size: 11pt;
            color: #222222;
            background-color: white;
            spacing: 8px;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 8px;
        }
        QRadioButton::indicator:unchecked {
            border: 2px solid #888888;
            background-color: white;
            border-radius: 8px;
        }
        QRadioButton::indicator:checked {
            border: 2px solid #004488;
            background-color: #004488;
            border-radius: 8px;
        }
        """)

        self.rows = []

        main = QVBoxLayout(self)

        title = QLabel("SERBEST FIRE HESAPLA")
        title.setWordWrap(True)
        main.addWidget(title)
        main.addSpacing(6)

        # Üst ayarlar
        self.plate_w = QLineEdit()
        self.plate_h = QLineEdit()
        self.plate_w.setPlaceholderText("Plaka en (örn: 120)")
        self.plate_h.setPlaceholderText("Plaka boy (örn: 240)")

        self.kerf_mm = QLineEdit()
        self.kerf_mm.setPlaceholderText("Kesim payı mm (örn: 5)")

        self.rotate_btn = QPushButton("R-90°")
        self.rotate_btn.setObjectName("rotateButton")
        self.rotate_btn.setCheckable(True)
        self.rotate_btn.setChecked(True)

        rowA = QHBoxLayout()
        rowA.addWidget(QLabel("Plaka (en x boy):"))
        rowA.addWidget(self.plate_w)
        rowA.addWidget(self.plate_h)
        main.addLayout(rowA)

        rowB = QHBoxLayout()
        rowB.addWidget(QLabel("Kesim payı (mm):"))
        rowB.addWidget(self.kerf_mm)
        rowB.addWidget(self.rotate_btn)
        rowB.addStretch()
        main.addLayout(rowB)

        rowC = QHBoxLayout()
        rowC.addWidget(QLabel("Kesim yönü:"))
        self.cut_mode_grp = QButtonGroup(self)
        self._cut_mode_buttons = {}
        for mode in ("Yatay", "Dikey", "Hibrit"):
            rb = QRadioButton(mode)
            self.cut_mode_grp.addButton(rb)
            self._cut_mode_buttons[mode] = rb
            rowC.addWidget(rb)
        self._cut_mode_buttons["Hibrit"].setChecked(True)
        rowC.addStretch()
        main.addLayout(rowC)

        main.addSpacing(6)

        # Ölçüler başlık
        header = QHBoxLayout()
        header.addWidget(QLabel("Ölçüler:"))
        header.addStretch()
        main.addLayout(header)

        # Ölçü satırları scroll
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.rows_container)
        scroll.setMinimumHeight(220)
        main.addWidget(scroll)

        self.add_measure_row()

        add_row = QHBoxLayout()
        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("miniButton")
        self.add_btn.clicked.connect(self.add_measure_row)
        add_row.addWidget(self.add_btn)
        add_row.addWidget(QLabel("Yeni ölçü satırı ekle"))
        add_row.addStretch()
        main.addLayout(add_row)

        main.addSpacing(8)

        # Sonuç
        self.result_needed = QLabel("Gerekli plaka: -")
        self.result_waste = QLabel("Fire: -")
        self.result_needed.setStyleSheet("color:#222222;")
        self.result_waste.setStyleSheet("color:#222222;")
        main.addWidget(self.result_needed)
        main.addWidget(self.result_waste)

        main.addSpacing(8)

        # Butonlar
        btns = QHBoxLayout()

        self.calc_btn = QPushButton("Hesapla")
        self.calc_btn.setObjectName("calcButton")

        self.pdf_btn = QPushButton("PDF Kaydet")
        self.pdf_btn.setObjectName("pdfButton")

        self.close_btn = QPushButton("Kapat")
        self.close_btn.setObjectName("closeButton")

        self.calc_btn.clicked.connect(self.calculate)
        self.pdf_btn.clicked.connect(self.export_pdf)
        self.close_btn.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(self.calc_btn)
        btns.addWidget(self.pdf_btn)
        btns.addWidget(self.close_btn)

        main.addLayout(btns)
        main.addSpacing(8)

        # Önizleme
        self.preview_title = QLabel("Yerleşim önizleme: -")
        self.preview_title.setStyleSheet("color:#222222;")
        main.addWidget(self.preview_title)

        self.preview_widget = _PlateGalleryWidget()

        self.preview_scroll = QScrollArea()

        # 🔥 scroll'un çalışması için kritik
        self.preview_scroll.setWidgetResizable(False)
        self.preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.preview_scroll.setWidget(self.preview_widget)
        self.preview_scroll.setMinimumHeight(280)
        main.addWidget(self.preview_scroll)

        self.setLayout(main)
        self.adjustSize()
        self.setMinimumWidth(720)

    # ---------- satır ekle / sil ----------

    def add_measure_row(self):
        roww = QWidget()
        lay = QHBoxLayout(roww)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        w = QLineEdit()
        h = QLineEdit()
        q = QLineEdit()

        w.setPlaceholderText("en")
        h.setPlaceholderText("boy")
        q.setPlaceholderText("adet")

        del_btn = QPushButton("-")
        del_btn.setObjectName("miniButton")

        lay.addWidget(QLabel("Ölçü:"))
        lay.addWidget(w)
        lay.addWidget(h)
        lay.addWidget(q)
        lay.addWidget(del_btn)
        lay.addStretch()

        item = {"w": w, "h": h, "q": q, "btn": del_btn, "row": roww}
        del_btn.clicked.connect(lambda _=False, it=item: self.remove_measure_row(it))

        self.rows.append(item)
        self.rows_layout.addWidget(roww)

    def remove_measure_row(self, item):
        if len(self.rows) <= 1:
            item["w"].setText("")
            item["h"].setText("")
            item["q"].setText("")
            return

        self.rows.remove(item)
        item["row"].setParent(None)
        item["row"].deleteLater()

    # ---------- parse helpers ----------

    def _parse_decimal(self, text: str, default: float = 0.0) -> float:
        txt = (text or "").strip()
        if not txt:
            return default
        txt = txt.replace(".", "").replace(",", ".")
        try:
            return float(txt)
        except ValueError:
            return default

    # ---------- hesapla ----------

    def calculate(self):
        W = self._parse_decimal(self.plate_w.text(), 0.0)
        H = self._parse_decimal(self.plate_h.text(), 0.0)
        kerf_mm = self._parse_decimal(self.kerf_mm.text(), 0.0)
        kerf = max(0.0, kerf_mm / 10.0)  # mm -> cm varsayımı

        allow_rotate = bool(self.rotate_btn.isChecked()) if self.rotate_btn is not None else True

        if W <= 0 or H <= 0:
            QMessageBox.warning(self, "Hatalı veri", "Plaka ölçülerini doğru gir (pozitif sayı).")
            return

        parts = []  # (iw, ih, rw, rh)
        for it in self.rows:
            rw = self._parse_decimal(it["w"].text(), 0.0)
            rh = self._parse_decimal(it["h"].text(), 0.0)
            try:
                q = int(self._parse_decimal(it["q"].text(), 0.0))
            except Exception:
                q = 0

            if rw <= 0 or rh <= 0 or q <= 0:
                continue

            iw = rw + kerf
            ih = rh + kerf
            for _ in range(q):
                parts.append((iw, ih, rw, rh))

        if not parts:
            QMessageBox.warning(self, "Eksik veri", "En az 1 ölçü satırında en/boy/adet gir.")
            return

        for (iw, ih, rw, rh) in parts:
            fits = (rw <= W and rh <= H) or (allow_rotate and rw <= H and rh <= W)
            if not fits:
                QMessageBox.warning(
                    self,
                    "Sığmıyor",
                    f"Bir parça plaka içine sığmıyor: {rw} x {rh} (plaka {W} x {H}).",
                )
                return

        plate_area = W * H
        total_real_area = sum(rw * rh for (_, _, rw, rh) in parts)

        # Seçilen kesim yönüne göre guillotine packer seç
        if self._cut_mode_buttons["Yatay"].isChecked():
            pack_fn = _guillotine_horizontal
        elif self._cut_mode_buttons["Dikey"].isChecked():
            pack_fn = _guillotine_vertical
        else:
            pack_fn = _guillotine_hybrid

        import random as _rnd

        candidates = []
        candidates.append(sorted(parts, key=lambda p: max(p[0], p[1]), reverse=True))
        candidates.append(sorted(parts, key=lambda p: p[0] * p[1], reverse=True))
        for _ in range(8):
            tmp = parts[:]
            _rnd.shuffle(tmp)
            candidates.append(tmp)

        best = None
        best_bins = []
        for cand in candidates:
            bins = pack_fn(cand, W, H, allow_rotate)
            plates = len(bins)
            if plates == 0:
                continue
            placed_area = sum(rw * rh for b in bins for (_, _, _, _, rw, rh) in b.used)
            waste = max(0.0, 1.0 - placed_area / (plates * plate_area))
            if best is None or (plates < best[0]) or (plates == best[0] and waste < best[1]):
                best = (plates, waste)
                best_bins = bins

        if best is None:
            QMessageBox.warning(self, "Hesap hatası", "Parçalar yerleştirilemedi.")
            return

        plates, waste = best
        waste_pct = max(0.0, min(100.0, waste * 100.0))

        self.result_needed.setText(f"Gerekli plaka: {plates}")
        self.result_waste.setText(f"Fire: {waste_pct:.1f}%".replace(".", ","))

        # Önizleme güncelle
        self.preview_title.setText(f"Yerleşim önizleme: × {plates} plaka")
        self.preview_widget.set_layout(best_bins, W, H)

    # ---------- PDF ----------

    def _calc_cut_length(self, b, plate_W, plate_H):
        """
        Bir plakadaki toplam kesim yolu uzunluğunu hesaplar.
        Aynı hizadaki kesimler (ortak kesimler) tek sefer sayılır.
        Birim: plaka birimiyle aynı (cm veya mm).
        """
        eps = 0.01
        x_cuts = set()
        y_cuts = set()
        for (x, y, pw, ph, drw, drh) in b.used:
            for xi in (x, x + pw):
                if eps < xi < plate_W - eps:
                    x_cuts.add(round(xi, 4))
            for yi in (y, y + ph):
                if eps < yi < plate_H - eps:
                    y_cuts.add(round(yi, 4))
        return len(x_cuts) * plate_H + len(y_cuts) * plate_W

    def export_pdf(self):
        if not getattr(self.preview_widget, "bins", None):
            QMessageBox.information(self, "PDF", "Önce hesapla, sonra PDF al.")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "PDF olarak kaydet", "serbest_fire.pdf", "PDF Dosyası (*.pdf)",
        )
        if not out_path:
            return

        from PyQt6.QtGui import QPdfWriter
        writer = QPdfWriter(out_path)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setResolution(144)

        painter = QPainter()
        if not painter.begin(writer):
            QMessageBox.warning(self, "PDF", "PDF oluşturulamadı.")
            return

        try:
            pw = float(painter.viewport().width())
            ph = float(painter.viewport().height())

            bins    = self.preview_widget.bins
            plate_W = self.preview_widget.plate_W
            plate_H = self.preview_widget.plate_H
            n_plates = len(bins)

            # Fire oranı
            waste_txt = self.result_waste.text()   # "Fire: 31,7%"
            try:
                waste_val = float(
                    waste_txt.replace("Fire:", "").replace("%", "")
                    .replace(",", ".").strip()
                )
            except Exception:
                waste_val = 0.0

            # Kerf
            try:
                kerf_mm = float(self.kerf_mm.text().replace(",", ".").strip() or "0")
            except Exception:
                kerf_mm = 0.0

            # Toplam kesim uzunluğu (tüm plakalar)
            total_cut = sum(self._calc_cut_length(b, plate_W, plate_H) for b in bins)

            # ── Sayfa 1: Özet ──
            from PyQt6.QtGui import QPageLayout
            margin = 50.0
            x = margin
            y = margin
            uw = pw - 2 * margin

            ff = "Calibri" if sys.platform != "darwin" else "Helvetica Neue"
            title_f = QFont(ff, 18); title_f.setBold(True)
            sub_f   = QFont(ff, 11); sub_f.setBold(True)
            body_f  = QFont(ff, 11)
            small_f = QFont(ff, 9)

            # Mac'te QFontMetricsF.height() tutarsız dönebiliyor → DPI tabanlı hesap
            dev_dpi = float(painter.device().logicalDpiX() or 144.0)
            def font_line_h(font: QFont) -> float:
                fm_h = QFontMetricsF(font).height()
                dpi_h = float(font.pointSizeF()) * (dev_dpi / 72.0) * 1.3
                return max(fm_h, dpi_h)

            def draw_text(font, color, text, y_pos, align=None, x_off=None, w_off=None):
                painter.setFont(font)
                painter.setPen(color)
                rh = font_line_h(font) + 4
                rx = x if x_off is None else x_off
                rw = uw if w_off is None else w_off
                af = align or int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                painter.drawText(QRectF(rx, y_pos, rw, rh), af, text)
                return rh

            # Başlık
            y += draw_text(title_f, QColor(20, 20, 20), "SERBEST FİRE HESAP RAPORU", y)
            y += 4
            painter.setPen(QPen(QColor(60, 60, 60), 1.2))
            painter.drawLine(QPointF(x, y), QPointF(x + uw, y))
            y += 16

            # Tarih
            y += draw_text(small_f, QColor(100, 100, 100),
                           f"Tarih: {datetime.now().strftime('%d.%m.%Y  %H:%M')}", y)
            y += 20

            # Özet tablo
            rows = [
                ("Plaka Boyutu",       f"{plate_W:.0f}  ×  {plate_H:.0f}  cm"),
                ("Kesim Payı",         f"{kerf_mm:.0f} mm"),
                ("Gerekli Plaka Sayısı", f"{n_plates}  adet"),
                ("Fire Oranı",         f"{waste_val:.1f}%"),
                ("Toplam Kesim Uzunluğu",
                 f"{total_cut:.1f} cm   ({total_cut/100:.2f} m)"),
            ]

            col1_w = uw * 0.45
            col2_w = uw * 0.55
            rh = font_line_h(body_f) + 22

            for i, (lbl, val) in enumerate(rows):
                bg = QColor(245, 247, 250) if i % 2 == 0 else QColor(255, 255, 255)
                painter.fillRect(QRectF(x, y, uw, rh), bg)
                # label
                painter.setFont(sub_f); painter.setPen(QColor(40, 40, 40))
                painter.drawText(QRectF(x + 8, y, col1_w - 16, rh),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), lbl)
                # value
                painter.setFont(body_f); painter.setPen(QColor(0, 0, 150))
                painter.drawText(QRectF(x + col1_w + 8, y, col2_w - 16, rh),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), val)
                y += rh

            # Çerçeve
            painter.setPen(QPen(QColor(150, 150, 150), 0.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(x, y - rh * len(rows), uw, rh * len(rows)))

            y += 24

            # Per-plate kesim özeti
            draw_text(sub_f, QColor(20, 20, 20), "Plaka Başı Kesim Detayı", y)
            y += font_line_h(sub_f) + 8
            painter.setPen(QPen(QColor(180, 180, 180), 0.6))
            painter.drawLine(QPointF(x, y), QPointF(x + uw, y))
            y += 8

            for bi, b in enumerate(bins):
                cut_len = self._calc_cut_length(b, plate_W, plate_H)
                n_pieces = len(b.used)
                painter.setFont(body_f); painter.setPen(QColor(20, 20, 100))
                line = (f"Plaka {bi+1}/{n_plates}  —  "
                        f"{n_pieces} parça  —  "
                        f"Kesim: {cut_len:.1f} cm  ({cut_len/100:.2f} m)")
                lh = font_line_h(body_f) + 16
                painter.drawText(QRectF(x, y, uw, lh),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), line)
                y += lh
                # Parça listesi
                painter.setFont(small_f); painter.setPen(QColor(80, 80, 80))
                pieces_str = "    " + ",   ".join(
                    f"{drw:.1f}×{drh:.1f}" for (_, _, _, _, drw, drh) in b.used
                )
                ph_line = font_line_h(small_f) + 12
                painter.drawText(QRectF(x, y, uw, ph_line),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                                 pieces_str)
                y += ph_line + 6

            # ── Sayfa 2+: Plaka yerleşim diyagramları ──
            writer.newPage()
            self.preview_widget.draw_to_painter(painter, pw, ph, plates_per_page=2, margin=30.0)

        except Exception as e:
            import traceback
            QMessageBox.critical(self, "PDF", f"PDF çizimi hata verdi:\n{e}\n\n{traceback.format_exc()}")
            return
        finally:
            painter.end()

        QMessageBox.information(self, "PDF", f"PDF kaydedildi:\n{out_path}")
    

# ---------- Guillotine Strip Packing ----------

class _GuillotineBin:
    """Guillotine kesim plakası. used: (x,y,iw,ih,rw,rh); cuts: (x1,y1,x2,y2) plaka koordinatı."""
    def __init__(self, W: float, H: float):
        self.W = float(W)
        self.H = float(H)
        self.used = []   # (x, y, iw, ih, rw, rh)
        self.cuts = []   # guillotine cut lines (x1,y1,x2,y2) in plate coords


def _guillotine_horizontal(parts, W, H, allow_rotate):
    """
    2-aşamalı guillotine: önce yatay şeritler (tam genişlik), sonra dikey kesimler.
    parts: [(iw, ih, rw, rh), ...] — iw/ih kerf dahil, rw/rh görsel ölçü.
    Döner: _GuillotineBin listesi.
    """
    bins = []
    remaining = list(parts)

    while remaining:
        b = _GuillotineBin(W, H)
        placed_mask = [False] * len(remaining)
        strip_y = 0.0

        while True:
            avail_h = H - strip_y
            if avail_h < 1e-9:
                break

            # Her parça için bu şerit bağlamında en iyi yönelimi bul
            fit = []  # (pih, piw, prw, prh, orig_idx, rotated)
            for i, (iw, ih, rw, rh) in enumerate(remaining):
                if placed_mask[i]:
                    continue
                if ih <= avail_h + 1e-9:
                    fit.append((ih, iw, rw, rh, i, False))
                if allow_rotate and abs(iw - ih) > 1e-9 and iw <= avail_h + 1e-9:
                    fit.append((iw, ih, rh, rw, i, True))

            if not fit:
                break

            # Şeridi en yüksek parçanın yüksekliği olarak belirle
            fit.sort(key=lambda c: (-c[0], -c[1]))
            strip_h = fit[0][0]

            # Şeridi soldan sağa doldur
            strip_x = 0.0
            placed_this = False
            cut_xs = []
            seen = set()

            for (pih, piw, prw, prh, orig_idx, _rotated) in fit:
                if orig_idx in seen:
                    continue
                if pih > strip_h + 1e-9:
                    continue
                if piw <= W - strip_x + 1e-9:
                    b.used.append((strip_x, strip_y, piw, pih, prw, prh))
                    strip_x += piw
                    placed_mask[orig_idx] = True
                    seen.add(orig_idx)
                    placed_this = True
                    if strip_x < W - 1e-9:
                        cut_xs.append(strip_x)

            if not placed_this:
                break

            # Yatay guillotine kesimi (şerit altı)
            if strip_y + strip_h < H - 1e-9:
                b.cuts.append((0.0, strip_y + strip_h, W, strip_y + strip_h))
            # Dikey kesimler şerit içinde
            for cx in cut_xs:
                b.cuts.append((cx, strip_y, cx, strip_y + strip_h))

            strip_y += strip_h
            remaining = [p for j, p in enumerate(remaining) if not placed_mask[j]]
            placed_mask = [False] * len(remaining)

        if not b.used:
            break
        bins.append(b)

    return bins


def _guillotine_vertical(parts, W, H, allow_rotate):
    """
    2-aşamalı guillotine: önce dikey sütunlar (tam yükseklik), sonra yatay kesimler.
    Yatay algoritmanın W↔H transpozesidir.
    """
    # Boyutları transpoz et
    transposed = [(ih, iw, rh, rw) for (iw, ih, rw, rh) in parts]
    bins_t = _guillotine_horizontal(transposed, H, W, allow_rotate)

    # Transpoz geri al: (x,y,iw,ih,rw,rh) → (y,x,ih,iw,rh,rw)
    bins = []
    for bt in bins_t:
        b = _GuillotineBin(W, H)
        b.used = [(y, x, ih, iw, rh, rw) for (x, y, iw, ih, rw, rh) in bt.used]
        # Kesim çizgilerini transpoz et: yatay ↔ dikey
        b.cuts = [(y1, x1, y2, x2) for (x1, y1, x2, y2) in bt.cuts]
        bins.append(b)
    return bins


def _guillotine_hybrid(parts, W, H, allow_rotate):
    """Yatay ve dikey guillotine'i dener, daha az plaka gerektireni döner."""
    bins_h = _guillotine_horizontal(parts, W, H, allow_rotate)
    bins_v = _guillotine_vertical(parts, W, H, allow_rotate)
    return bins_h if len(bins_h) <= len(bins_v) else bins_v


# ---------- Packing (MaxRects) ----------

class _MaxRectsBin:
    def __init__(self, W: float, H: float):
        self.W = float(W)
        self.H = float(H)
        self.free = [(0.0, 0.0, self.W, self.H)]  # x,y,w,h
        self.used = []  # (x,y,iw,ih,rw,rh) yerleştirilenler

    @staticmethod
    def _contains(a, b) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return (bx >= ax and by >= ay and bx + bw <= ax + aw and by + bh <= ay + ah)

    @staticmethod
    def _intersects(a, b) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return not (bx >= ax + aw or bx + bw <= ax or by >= ay + ah or by + bh <= ay)

    def _prune(self):
        pruned = []
        for i, r in enumerate(self.free):
            contained = False
            for j, o in enumerate(self.free):
                if i == j:
                    continue
                if self._contains(o, r):
                    contained = True
                    break
            if not contained and r[2] > 0 and r[3] > 0:
                pruned.append(r)
        self.free = pruned

    def _split_free_rect(self, free_rect, used_rect):
        fx, fy, fw, fh = free_rect
        ux, uy, uw, uh = used_rect

        # used_rect free_rect ile kesişmiyorsa split yok
        if not self._intersects(free_rect, used_rect):
            return [free_rect]

        new_rects = []

        # üst parça
        if uy > fy:
            new_rects.append((fx, fy, fw, uy - fy))
        # alt parça
        if uy + uh < fy + fh:
            new_rects.append((fx, uy + uh, fw, (fy + fh) - (uy + uh)))
        # sol parça
        if ux > fx:
            new_rects.append((fx, fy, ux - fx, fh))
        # sağ parça
        if ux + uw < fx + fw:
            new_rects.append((ux + uw, fy, (fx + fw) - (ux + uw), fh))

        return [r for r in new_rects if r[2] > 0 and r[3] > 0]

    def insert(self, rw: float, rh: float, allow_rotate: bool):
        best_score = None
        best_node = None  # (x,y,w,h)

        # Best Short Side Fit + tie break Long Side
        for (fx, fy, fw, fh) in self.free:
            # normal
            if rw <= fw and rh <= fh:
                leftover_h = fh - rh
                leftover_w = fw - rw
                score = (min(leftover_w, leftover_h), max(leftover_w, leftover_h))
                if best_score is None or score < best_score:
                    best_score = score
                    best_node = (fx, fy, rw, rh)

            # rotated
            if allow_rotate and rh <= fw and rw <= fh:
                leftover_h = fh - rw
                leftover_w = fw - rh
                score = (min(leftover_w, leftover_h), max(leftover_w, leftover_h))
                if best_score is None or score < best_score:
                    best_score = score
                    best_node = (fx, fy, rh, rw)

        if best_node is None:
            return None

        # free list’i, kullanılan rect’e göre split et
        used = best_node
        new_free = []
        for fr in self.free:
            new_free.extend(self._split_free_rect(fr, used))
        self.free = new_free
        self._prune()

        return used

class _PlateGalleryWidget(QWidget):
    """
    Serbest fire hesabı sonrası tüm plakaları alt alta çizer.
    Her plaka: dış çerçeve + yerleşen parçalar (kerf dahil ölçülerle).
    Parça ortasında sadece ölçü yazısı gösterir (çizgi yok).

    Ek: draw_to_painter() ile PDF'e çok sayfalı basar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bins = []
        self.plate_W = 1.0
        self.plate_H = 1.0

        self.margin = 14
        self.caption_h = 22
        self.gap = 18
        self.target_w = 520  # ekranda her plaka için çizim genişliği (px)

        # ScrollArea sağlıklı çalışsın
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(self.target_w + self.margin * 2)

        # PDF'te sorun çıkarmayan font kullan (Mac: Helvetica, Win: Segoe UI)
        self.font_family = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
        # PDF okunabilirlik ayarları (pt = yazı büyüklüğü)
        self.pdf_caption_h_mm = 12.0      # "Plaka 1/5" satırının yüksekliği (mm)
        self.pdf_gap_mm = 8.0             # plakalar arası boşluk (mm)
        self.pdf_caption_font_pt = 14.0   # "Plaka 1/5" fontu
        self.pdf_dim_font_pt = 11.0       # taş ölçüsü fontu (parça içi)
        self.pdf_dim_font_min_pt = 8.0    # çok küçük parçada düşebileceği min font


    def set_layout(self, bins, W: float, H: float):
        self.bins = list(bins) if bins else []
        self.plate_W = float(W) if W and W > 0 else 1.0
        self.plate_H = float(H) if H and H > 0 else 1.0

        hint = self.sizeHint()
        self.setMinimumSize(hint)
        self.resize(hint)

        self.updateGeometry()
        self.update()

    def sizeHint(self):
        plate_w_px = float(self.target_w)
        plate_h_px = float(plate_w_px * (self.plate_H / max(1e-9, self.plate_W)))
        per_plate = self.caption_h + plate_h_px + self.gap
        h = self.margin * 2 + max(1, len(self.bins)) * per_plate
        w = self.margin * 2 + plate_w_px
        return QSize(int(w), int(h))

    def minimumSizeHint(self):
        return self.sizeHint()

    # --------- küçük yardımcılar ---------

    def _fmt(self, v: float) -> str:
        try:
            iv = int(round(v))
            if abs(v - iv) < 1e-6:
                return str(iv)
            return f"{v:.1f}".replace(".", ",")
        except Exception:
            return str(v)
        
    def _font_pt(self, pt: float) -> QFont:
        """Point-size font helper (PDF’de tutarlı font boyu için)."""
        f = QFont(self.font_family)
        f.setPointSizeF(float(pt))
        return f

    def _build_color_map(self, bins) -> dict:
        """Her benzersiz parça ölçüsüne pastel renk atar. Anahtar: (min_dim, max_dim)."""
        sizes = set()
        for b in (bins or []):
            for (_, _, _, _, rw, rh) in (getattr(b, "used", None) or []):
                sizes.add((min(rw, rh), max(rw, rh)))
        color_map = {}
        sorted_sizes = sorted(sizes)
        n = max(1, len(sorted_sizes))
        golden = 0.618033988749895
        for i, key in enumerate(sorted_sizes):
            hue = (i * golden * 360.0) % 360.0
            c = QColor.fromHslF(hue / 360.0, 0.65, 0.78)
            c.setAlpha(110)
            color_map[key] = c
        return color_map

    def _draw_one_plate(
        self,
        painter: QPainter,
        x0: float,
        y0: float,
        plate_w_px: float,
        scale: float,
        bin_obj,
        idx: int,
        total: int,
        *,
        caption_h_px: float | None = None,
        caption_font_pt: float | None = None,
        dim_font_pt: float | None = None,
        dim_font_min_pt: float | None = None,
        gap_px: float | None = None,
        pdf_mode: bool = False,
        color_map: dict | None = None,
    ):
        """
        painter üstünde tek plaka çizer.
        Dönüş: (consumed_height_px)
        """
        plate_h_px = float(self.plate_H) * scale

        # --- PDF için override edilebilir ölçüler / fontlar ---
        cap_h = float(caption_h_px) if caption_h_px is not None else float(self.caption_h)
        cap_font = float(caption_font_pt) if caption_font_pt is not None else 9.0
        dim_font = float(dim_font_pt) if dim_font_pt is not None else 7.0
        dim_min = float(dim_font_min_pt) if dim_font_min_pt is not None else 5.0

        # dış ve iç çizgi kalınlıkları
        pen_outer = QPen(QColor(30, 30, 30))
        is_pdf = isinstance(painter.device(), QPrinter)
        pen_outer.setWidth(3)   # hem PDF hem önizleme aynı kalınlık


        pen_inner = QPen(QColor(90, 90, 90))
        pen_inner.setWidth(1)

        # Başlık: Plaka X/Y
        painter.setPen(QColor(20, 20, 20))
        if pdf_mode:
            painter.setFont(self._font_pt(cap_font))
        else:
            painter.setFont(QFont(self.font_family, int(round(cap_font))))
        painter.drawText(
            QRectF(x0, y0, plate_w_px, cap_h),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            f"Plaka {idx}/{total}",
        )

        y = y0 + cap_h

        # Plaka çerçevesi
        plate_rect = QRectF(x0, y, plate_w_px, plate_h_px)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(plate_rect)

        # Parçalar
        painter.setPen(pen_inner)
        used_list = getattr(bin_obj, "used", []) or []

        for (rx, ry, iw, ih, rw, rh) in used_list:
            r = QRectF(x0 + rx * scale, y + ry * scale, iw * scale, ih * scale)
            # Aynı ölçüdeki parçaları aynı pastel renge boya
            if color_map:
                key = (min(rw, rh), max(rw, rh))
                fill_color = color_map.get(key)
                if fill_color:
                    painter.setBrush(QBrush(fill_color))
                    painter.setPen(pen_inner)
                    painter.drawRect(r)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                else:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(r)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(r)

            # Parça ortasına ölçü yazısı (PDF’de × bazen bozuluyor -> "x" kullan)
            if r.width() >= 18 and r.height() >= 12:
                dim_text = f"{self._fmt(rw)}x{self._fmt(rh)}"

                painter.save()
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

                # --- dik ve ince parçalar için yazıyı döndür (önizleme + PDF) ---
                rotate_text = r.height() > r.width() * 1.35

                if rotate_text:
                    # Koordinat sistemini dik parça merkezine al ve 90° döndür
                    cx, cy = r.center().x(), r.center().y()
                    painter.translate(cx, cy)
                    painter.rotate(-90)          # yazı dik dursun
                    box_w = r.height()           # yerel kutu genişliği
                    box_h = r.width()            # yerel kutu yüksekliği
                else:
                    box_w = r.width()
                    box_h = r.height()

                # --- FONTU kutuya göre ölçekle (ekran+PDF aynı mantık) ---
                max_pt = dim_font_pt if dim_font_pt is not None else 14.0
                min_pt = dim_min

                font = QFont(self.font_family)
                font.setPointSizeF(max_pt)
                painter.setFont(font)

                fm = QFontMetricsF(font)
                br = fm.tightBoundingRect(dim_text)

                if br.width() > 0 and br.height() > 0:
                    sx = (box_w * 0.85) / br.width()
                    sy = (box_h * 0.60) / br.height()
                    s = min(1.0, sx, sy)
                else:
                    s = 1.0

                pt = max(min_pt, max_pt * s)
                font.setPointSizeF(pt)
                painter.setFont(font)

                fm = QFontMetricsF(font)
                tw = fm.horizontalAdvance(dim_text)
                # tightBoundingRect gerçek glyph yüksekliğini verir, Mac'te daha güvenilir
                th = max(fm.ascent() + fm.descent(), abs(fm.tightBoundingRect(dim_text).height()))

                # --- beyaz yastık: textin hemen etrafında, küçük taşma payı ---
                pad_w = max(16.0, tw + 12.0)
                pad_h = max(12.0, th + 14.0)

                if rotate_text:
                    # artık koordinat sistemi parça merkezinde, bu yüzden 0 etrafında çiziyoruz
                    pad = QRectF(-pad_w / 2.0, -pad_h / 2.0, pad_w, pad_h)
                else:
                    pad = QRectF(
                        r.center().x() - pad_w / 2.0,
                        r.center().y() - pad_h / 2.0,
                        pad_w,
                        pad_h,
                    )

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, 220))
                painter.drawRoundedRect(pad, 4, 4)

                # Yazıyı nokta konumuyla çiz (rect clipping Mac'te metni kırpıyor)
                painter.setPen(QColor(30, 30, 30))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                baseline_y = pad.center().y() + (fm.ascent() - fm.descent()) / 2.0
                text_x = pad.center().x() - tw / 2.0
                painter.drawText(QPointF(text_x, baseline_y), dim_text)

                painter.restore()

            # ── Kenar ölçü etiketleri (orijinal koordinat sisteminde) ──
            edge_pt = max(dim_min, min(max_pt * 0.90, 10.0))
            edge_f = QFont(self.font_family)
            edge_f.setPointSizeF(edge_pt)
            efm = QFontMetricsF(edge_f)
            e_color = QColor(40, 40, 130)

            w_label = self._fmt(rw)   # üst kenara yazılacak yatay ölçü
            h_label = self._fmt(rh)   # sol kenara yazılacak dikey ölçü

            wl_adv = efm.horizontalAdvance(w_label)
            hl_adv = efm.horizontalAdvance(h_label)
            e_asc  = efm.ascent()
            e_h    = e_asc + efm.descent()

            # Üst kenar 1/5 noktasına yatay ölçü (çakışmayı önlemek için merkezden uzak)
            if r.width() >= wl_adv + 10 and r.height() >= e_h + 12:
                painter.save()
                painter.setFont(edge_f)
                painter.setPen(e_color)
                tx = r.left() + r.width() * 0.2 - wl_adv / 2.0
                ty = r.top() + 10.0 + e_asc
                painter.drawText(QPointF(tx, ty), w_label)
                painter.restore()

            # Sol kenar 1/5 noktasına dikey ölçü (çakışmayı önlemek için merkezden uzak)
            if r.height() >= hl_adv + 10 and r.width() >= e_h + 12:
                painter.save()
                painter.translate(r.left() + 8.0, r.top() + r.height() * 0.2)
                painter.rotate(90)
                painter.setFont(edge_f)
                painter.setPen(e_color)
                painter.drawText(QPointF(-hl_adv / 2.0, e_asc / 2.0), h_label)
                painter.restore()

        # Guillotine kesim çizgileri (kırmızı kesik çizgi)
        cuts = getattr(bin_obj, "cuts", None)
        if cuts:
            pen_cut = QPen(QColor(200, 0, 0))
            pen_cut.setWidth(2)
            pen_cut.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen_cut)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for (x1, y1, x2, y2) in cuts:
                painter.drawLine(
                    QPointF(x0 + x1 * scale, y + y1 * scale),
                    QPointF(x0 + x2 * scale, y + y2 * scale),
                )

        return cap_h + plate_h_px  # bu plakanın kapladığı yükseklik (gap hariç)

    
    # --------- ekranda çizim ---------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        plate_w_px = float(self.target_w)
        scale = plate_w_px / max(1e-9, float(self.plate_W))

        x0 = float(self.margin)
        y = float(self.margin)

        bins = self.bins if self.bins else []

        if not bins:
            painter.setFont(QFont(self.font_family, 9))
            painter.setPen(QColor(120, 120, 120))
            painter.drawText(
                QRectF(x0, y, plate_w_px, self.caption_h),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                "Önizleme için önce hesapla.",
            )
            return

        color_map = self._build_color_map(bins)
        for i, b in enumerate(bins, start=1):
            used_h = self._draw_one_plate(painter, x0, y, plate_w_px, scale, b, i, len(bins),
                                          color_map=color_map)
            y += used_h + self.gap

    def _mm_to_px(self, painter, mm_value: float) -> float:
        """
        PDF çıktı ölçeklemesinde mm değerini aktif painter'ın DPI'ına göre piksele çevirir.
        """
        try:
            # Her inçte 25.4 mm var, QPrinter PDF çıktısı genelde 96 veya 300 DPI çalışır
            dpi = painter.device().logicalDpiX()
        except Exception:
            dpi = 96  # varsayılan fallback
        return (mm_value / 25.4) * dpi




# --------- PDF / dış painter'a çizim ---------

    def draw_to_painter(
        self,
        painter: QPainter,
        page_w: float,
        page_h: float,
        plates_per_page: int = 2,
        margin: float = 12.0,
    ):
        """
        QPrinter üzerinde çalışan painter'a çok sayfalı çizim yapar.
        plates_per_page: bir sayfaya kaç plaka sığsın.

        Not:
        - margin parametresi PDF'de mm gibi davranır (yüksek DPI -> mm->px).
        """
        bins = self.bins if self.bins else []
        if not bins:
            painter.setFont(self._font_pt(12.0))
            painter.setPen(QColor(120, 120, 120))
            painter.drawText(QRectF(30, 30, max(10.0, page_w - 60), 40), "Önce hesapla.")
            return

        # QPrinter device px / mm dönüşümü
        # Yüksek DPI (printer) ise margin'i mm kabul edip px'e çevir.
        dev = painter.device()
        try:
            dpi = float(getattr(dev, "logicalDpiX")())
        except Exception:
            dpi = 72.0

        is_printer_like = dpi >= 72.0

        if is_printer_like:
            margin_px = self._mm_to_px(painter, float(margin))
            caption_h_px = self._mm_to_px(painter, self.pdf_caption_h_mm)
            gap_px = self._mm_to_px(painter, self.pdf_gap_mm)
            caption_font_pt = self.pdf_caption_font_pt
            dim_font_pt = self.pdf_dim_font_pt
            dim_font_min_pt = self.pdf_dim_font_min_pt
        else:
            # fallback (beklenmedik cihaz): px gibi davran
            margin_px = float(margin)
            caption_h_px = float(self.caption_h)
            gap_px = float(self.gap)
            caption_font_pt = 12.0
            dim_font_pt = 9.0
            dim_font_min_pt = 7.0

        usable_w = max(10.0, page_w - 2.0 * margin_px)
        usable_h = max(10.0, page_h - 2.0 * margin_px)

        # PDF’de sayfa genişliğine sığdır
        plate_w_px = float(usable_w)
        scale = plate_w_px / max(1e-9, float(self.plate_W))

        x0 = float(margin_px)
        y = float(margin_px)

        count_on_page = 0
        total = len(bins)
        color_map = self._build_color_map(bins)

        for i, b in enumerate(bins, start=1):
            plate_h_px = float(self.plate_H) * scale
            need_h = caption_h_px + plate_h_px

            # yeni sayfaya geç (yükseklik yetmiyorsa ya da plates_per_page dolduysa)
            if count_on_page > 0:
                if (count_on_page >= max(1, int(plates_per_page))) or (y + need_h > margin_px + usable_h):
                    if hasattr(dev, "newPage"):
                        dev.newPage()
                    y = float(margin_px)
                    count_on_page = 0

            used_h = self._draw_one_plate(
                painter,
                x0,
                y,
                plate_w_px,
                scale,
                b,
                i,
                total,
                caption_h_px=float(caption_h_px),
                caption_font_pt=float(caption_font_pt),
                dim_font_pt=float(dim_font_pt),
                dim_font_min_pt=float(dim_font_min_pt),
                gap_px=float(gap_px),
                pdf_mode=is_printer_like,
                color_map=color_map,
            )

            y += used_h + float(gap_px)
            count_on_page += 1


class SketchNameDialog(QDialog):
    """Ana balondaki ürün adını düzenlemek için."""

    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ürün Adı")
        self.setModal(True)

        self.setStyleSheet("""
        QDialog {
            background-color: white;
            border: 2px solid #444444;
            color: #000000;  /* Varsayılan metin rengi */
        }

        QLabel, QLineEdit, QPushButton {
            font-family: "DIN Alternate", "Noteworthy", "Bradley Hand", "Segoe Print", "Comic Sans MS", sans-serif;
        }
        QLabel {
            font-size: 13pt;
            color: #222222;
        }

        QLineEdit {
            font-size: 12pt;
            padding: 6px 10px;
            border: 2px solid #444444;
            border-radius: 8px;
            background-color: white;
            color: #222222;
        }

        QPushButton {
            font-size: 12pt;
            padding: 8px 18px;
            border: 2px solid #444444;
            border-radius: 16px;
            background-color: white;
            color: #222222;   /* Buton yazısı da koyu olsun */
        }

        QPushButton#okButton {
            color: #b00000;
            border-color: #b00000;
        }

        QPushButton#cancelButton {
            color: #004488;
            border-color: #004488;
        }

        QPushButton:hover {
            background-color: #f5f5f5;
        }
        """)


        label = QLabel("Bu satırın ürün adını yaz:")
        self.name_edit = QLineEdit()
        self.name_edit.setText(current_name)

        row = QHBoxLayout()
        row.addWidget(self.name_edit)

        ok_btn = QPushButton("Onay")
        ok_btn.setObjectName("okButton")
        cancel_btn = QPushButton("Vazgeç")
        cancel_btn.setObjectName("cancelButton")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addSpacing(8)
        layout.addLayout(row)
        layout.addSpacing(10)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.resize(360, 150)

    def get_name(self) -> str:
        return self.name_edit.text().strip()

class SketchPriceDialog(QDialog):
    """İşçilik gibi sadece fiyat düzenlemek için sade eskiz-stilli dialog."""

    def __init__(self, title_name: str, current_price: float, parent=None):
        super().__init__(parent)
        self._price = float(current_price or 0.0)

        self.setWindowTitle("Fiyat Düzenle")
        self.setModal(True)

        self.setStyleSheet("""
        QDialog {
            background-color: white;
            border: 2px solid #444444;
            color: #000000;
        }
        QLabel, QLineEdit, QPushButton {
            font-family: "DIN Alternate", "Noteworthy", "Bradley Hand", "Segoe Print", "Comic Sans MS", sans-serif;
        }
        QLabel { font-size: 11pt; color: #222222; }
        QLineEdit {
            font-size: 13pt;
            padding: 8px 12px;
            border: 2px solid #444444;
            border-radius: 10px;
            background-color: white;
            color: #222222;
        }
        QPushButton {
            font-size: 12pt;
            padding: 8px 18px;
            border: 2px solid #444444;
            border-radius: 16px;
            background-color: white;
            color: #222222;
        }
        QPushButton#okButton {
            color: #b00000;
            border-color: #b00000;
        }
        QPushButton#cancelButton {
            color: #004488;
            border-color: #004488;
        }
        QPushButton:hover { background-color: #f5f5f5; }
        """)

        main_layout = QVBoxLayout(self)

        name = (title_name or "").strip()
        header = QLabel(f"{name} fiyatını düzenle" if name else "Fiyatı düzenle")
        header.setWordWrap(True)
        main_layout.addWidget(header)
        main_layout.addSpacing(8)

        row = QHBoxLayout()
        row.addWidget(QLabel("Birim fiyat:"))
        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText("örn: 120,00")
        self.price_edit.setText(self._format_decimal(self._price))
        row.addWidget(self.price_edit)
        main_layout.addLayout(row)

        # OK / Vazgeç
        ok_btn = QPushButton("Onay")
        ok_btn.setObjectName("okButton")
        cancel_btn = QPushButton("Vazgeç")
        cancel_btn.setObjectName("cancelButton")

        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addSpacing(10)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.adjustSize()
        self.setMinimumWidth(420)

    def _parse_decimal(self, text: str, default: float = 0.0) -> float:
        txt = (text or "").strip()
        if not txt:
            return default
        txt = txt.replace(".", "").replace(",", ".")
        try:
            return float(txt)
        except ValueError:
            return default

    def _format_decimal(self, value: float) -> str:
        try:
            return f"{float(value):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return "0,00"

    def _on_ok(self):
        self._price = self._parse_decimal(self.price_edit.text(), self._price)
        self.accept()

    def get_price(self) -> float:
        return float(self._price)

class SketchOverwriteDialog(QDialog):
    """Aynı adlı ürün varsa Değiştir / İptal sorusu için."""

    def __init__(self, product_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ürünü Güncelle")
        self.setModal(True)

        self.setStyleSheet("""
        QDialog {
            background-color: white;
            border: 2px solid #444444;
            color: #000000;  /* Varsayılan metin rengi */
        }

        QLabel, QLineEdit, QPushButton {
            font-family: "DIN Alternate", "Noteworthy", "Bradley Hand", "Segoe Print", "Comic Sans MS", sans-serif;
        }

        QLabel {
            font-size: 13pt;
            color: #222222;
        }

        QLineEdit {
            font-size: 12pt;
            padding: 6px 10px;
            border: 2px solid #444444;
            border-radius: 8px;
            background-color: white;
            color: #222222;
        }

        QPushButton {
            font-size: 12pt;
            padding: 8px 18px;
            border: 2px solid #444444;
            border-radius: 16px;
            background-color: white;
            color: #222222;   /* Buton yazısı da koyu olsun */
        }

        QPushButton#okButton {
            color: #b00000;
            border-color: #b00000;
        }

        QPushButton#cancelButton {
            color: #004488;
            border-color: #004488;
        }

        QPushButton:hover {
            background-color: #f5f5f5;
        }
        """)


        label = QLabel(
            f"'{product_name}' adlı ürün zaten teklif listesinde.\n"
            "Bu ürünü yeni değerlerle güncellemek ister misin?"
        )
        label.setWordWrap(True)

        ok_btn = QPushButton("Değiştir")
        ok_btn.setObjectName("okButton")
        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("cancelButton")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addSpacing(10)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.resize(420, 160)

class SketchAddProductDialog(QDialog):
    """Ürünü teklif listesine eklerken Miktar, Birim ve Detay bilgisi alır."""

    UNITS = ["AD", "M²", "MT", "cm", "mm", "M³", "KG", "adet"]

    def __init__(self, product_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ürün Ekle")
        self.setModal(True)
        self.setStyleSheet("""
        QDialog { background-color: white; border: 2px solid #444444; color: #000000; }
        QLabel, QLineEdit, QPushButton, QComboBox {
            font-family: "DIN Alternate", "Noteworthy", "Bradley Hand", "Segoe Print", "Comic Sans MS", sans-serif;
        }
        QLabel { font-size: 12pt; color: #222222; }
        QLineEdit, QComboBox {
            font-size: 12pt; padding: 5px 10px;
            border: 2px solid #444444; border-radius: 8px;
            background-color: white; color: #222222;
        }
        QPushButton {
            font-size: 12pt; padding: 8px 18px;
            border: 2px solid #444444; border-radius: 16px;
            background-color: white; color: #222222;
        }
        QPushButton#okButton { color: #b00000; border-color: #b00000; }
        QPushButton#cancelButton { color: #004488; border-color: #004488; }
        QPushButton:hover { background-color: #f5f5f5; }
        QComboBox QAbstractItemView {
            background-color: white; color: #222222;
            selection-background-color: #0078d7; selection-color: white;
            border: 1px solid #999999;
        }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(f"Ürün: <b>{product_name}</b>"))

        # Detay
        layout.addWidget(QLabel("Detay / Açıklama:"))
        self._detay = QLineEdit()
        self._detay.setPlaceholderText("örn. 17.6 MT x 125 CM DUVAR KAPLAMA")
        layout.addWidget(self._detay)

        # Miktar + Birim
        row = QHBoxLayout()
        miktar_col = QVBoxLayout()
        miktar_col.addWidget(QLabel("Miktar:"))
        self._miktar = QLineEdit()
        self._miktar.setPlaceholderText("örn. 22")
        miktar_col.addWidget(self._miktar)

        birim_col = QVBoxLayout()
        birim_col.addWidget(QLabel("Birim:"))
        self._birim = QComboBox()
        self._birim.setEditable(True)
        self._birim.addItems(self.UNITS)
        self._birim.setCurrentText("AD")
        birim_col.addWidget(self._birim)

        row.addLayout(miktar_col)
        row.addLayout(birim_col)
        layout.addLayout(row)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Ekle")
        ok_btn.setObjectName("okButton")
        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("cancelButton")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.resize(440, 260)

    def get_detay(self) -> str:
        return self._detay.text().strip()

    def get_miktar(self) -> float:
        txt = self._miktar.text().replace(",", ".").strip()
        try:
            return float(txt)
        except ValueError:
            return 0.0

    def get_birim(self) -> str:
        return self._birim.currentText().strip() or "AD"


class SketchExportedItemsDialog(QDialog):
    """
    Teklifteki ürünleri listelemek, seçili ürünü silmek veya merkeze geri yüklemek için diyalog.
    """

    def __init__(self, parent):

        super().__init__(parent)
        self.ui = parent  # Ana arayüz (SketchPriceUI)

        self.setWindowTitle("Teklifteki Ürünler")
        self.setModal(True)

        self.setStyleSheet("""
        QDialog {
            background-color: white;
            border: 2px solid #444444;
            color: #000000;
        }

        QLabel, QListWidget, QPushButton {
            font-family: "DIN Alternate", "Noteworthy", "Bradley Hand", "Segoe Print", "Comic Sans MS", sans-serif;
        }

        QLabel {
            font-size: 13pt;
            color: #222222;
        }

        QListWidget {
            font-size: 12pt;
            border: 2px solid #444444;
            border-radius: 8px;
            padding: 6px;
            background-color: white;
            color: #222222;                 /* Metin rengi siyaha yakın */
            selection-background-color: #e0e0e0;
            selection-color: #000000;
        }


        QPushButton {
            font-size: 12pt;
            padding: 6px 16px;
            border: 2px solid #444444;
            border-radius: 16px;
            background-color: white;
            color: #222222;
        }

        QPushButton:hover {
            background-color: #f0f0f0;
        }
        """)

        info_label = QLabel("Teklif listesinde yer alan ürünler:")
        info_label.setWordWrap(True)

        self.list_widget = QListWidget()
        self._populate_list()

        btn_load = QPushButton("Seçili ürünü merkeze yükle")
        btn_delete = QPushButton("Seçili ürünü sil")
        btn_close = QPushButton("Kapat")

        btn_load.clicked.connect(self._on_load)
        btn_delete.clicked.connect(self._on_delete)
        btn_close.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_load)
        btn_row.addStretch()
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(info_label)
        layout.addWidget(self.list_widget)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.resize(700, 380)

    def _populate_list(self):
        """exported_items listesini ekrana döker."""
        self.list_widget.clear()

        items = self.ui.exported_items or []
        for idx, item in enumerate(items):
            name = str(item.get("name") or "Adsız Ürün")

            # Fiyatı güvenle çek
            try:
                unit_price = float(item.get("unit_price", 0.0))
            except (TypeError, ValueError):
                unit_price = 0.0

            price_txt = self.ui.format_amount(unit_price)

            summary = item.get("components_summary", "") or ""
            if len(summary) > 80:
                summary = summary[:77] + "..."

            display = f"{idx + 1}. {name} — {price_txt}"
            if summary:
                display += f" | {summary}"

            self.list_widget.addItem(display)

    def _current_row(self) -> int:
        return self.list_widget.currentRow()

    def _on_delete(self):
        row = self._current_row()
        if row < 0:
            QMessageBox.information(
                self,
                "Ürün seçilmedi",
                "Silmek için listeden bir ürün seçmelisin."
            )
            return

        if row >= len(self.ui.exported_items):
            return

        name = self.ui.exported_items[row].get("name", "Bu ürün")
        reply = QMessageBox.question(
            self,
            "Ürünü sil",
            f"'{name}' adlı ürünü teklif listesinden silmek istediğine emin misin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Asıl liste üzerinden sil
        del self.ui.exported_items[row]
        # Listeyi ekranda yenile
        self._populate_list()

    def _on_load(self):
        row = self._current_row()
        if row < 0:
            QMessageBox.information(
                self,
                "Ürün seçilmedi",
                "Merkeze yüklemek için listeden bir ürün seçmelisin."
            )
            return

        if row >= len(self.ui.exported_items):
            return

        item = self.ui.exported_items[row]

        # Mevcut satırı seçilen ürünle doldur
        self.ui.current_product_name = item.get("name", "Ürün Adı")
        self.ui.current_components = [dict(c) for c in (item.get("components") or [])]

        # Satır toplamını bileşenlerin subtotal değerlerinden yeniden hesapla
        self.ui.line_total = sum(
            float(c.get("subtotal", 0.0) or 0.0) for c in self.ui.current_components
        )

        # Rakam önizlemesini sıfırla
        self.ui.preview_raw = ""
        self.ui.update()

        self.accept()


class SketchProjectDialog(QDialog):
    """Mevcut projeyi listeden seç veya yeni proje adı gir."""

    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proje Seç / Oluştur")
        self.setModal(True)
        self._result_name = ""

        self.setStyleSheet("""
        QDialog { background-color: white; color: #000000; }
        QLabel {
            font-family: "DIN Alternate","Noteworthy","Bradley Hand","Segoe Print","Comic Sans MS",sans-serif;
            font-size: 12pt; color: #222222;
        }
        QListWidget {
            font-family: "DIN Alternate","Noteworthy","Bradley Hand","Segoe Print","Comic Sans MS",sans-serif;
            font-size: 11pt; color: #222222;
            background-color: #fafafa; border: 2px solid #aaaaaa; border-radius: 6px;
        }
        QListWidget::item:selected { background-color: #0078d7; color: white; }
        QListWidget::item:hover    { background-color: #e8f0fe; }
        QLineEdit {
            font-family: "DIN Alternate","Noteworthy","Bradley Hand","Segoe Print","Comic Sans MS",sans-serif;
            font-size: 11pt; padding: 5px 10px;
            border: 2px solid #444444; border-radius: 8px;
            background-color: white; color: #222222;
        }
        QPushButton {
            font-family: "DIN Alternate","Noteworthy","Bradley Hand","Segoe Print","Comic Sans MS",sans-serif;
            font-size: 11pt; padding: 7px 16px;
            border: 2px solid #444444; border-radius: 14px;
            background-color: white; color: #222222;
        }
        QPushButton#openBtn  { color: #006600; border-color: #006600; }
        QPushButton#cancelBtn { color: #004488; border-color: #004488; }
        QPushButton:hover { background-color: #f0f0f0; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ---- Mevcut projeler listesi ----
        layout.addWidget(QLabel("Mevcut Projeler:"))
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(180)

        # Teklifler/ altındaki proje klasörlerini tara (yeni format)
        teklifler_dir = os.path.join(get_app_base_dir(), "Teklifler")
        projects = []
        new_project_names = set()
        try:
            if os.path.isdir(teklifler_dir):
                for entry in os.scandir(teklifler_dir):
                    if not entry.is_dir():
                        continue
                    csv_path = os.path.join(entry.path, "proje.csv")
                    try:
                        mtime = os.path.getmtime(csv_path) if os.path.exists(csv_path) else entry.stat().st_mtime
                    except Exception:
                        mtime = 0.0
                    projects.append((mtime, entry.name))
                    new_project_names.add(entry.name)
        except Exception:
            pass

        # Kök klasördeki eski format projeleri de tara: <ad>.csv + kategoriler_<ad>.json
        try:
            root_dir = get_app_base_dir()
            _skip_stems = {"proje", "teklif"}
            for entry in os.scandir(root_dir):
                if not entry.is_file() or not entry.name.endswith(".csv"):
                    continue
                stem = entry.name[:-4]
                if stem in _skip_stems or stem.startswith("Teklif_") or stem.startswith("kategoriler_"):
                    continue
                kat = os.path.join(root_dir, f"kategoriler_{stem}.json")
                if not os.path.exists(kat):
                    continue
                if stem in new_project_names:
                    continue  # zaten Teklifler'e taşınmış
                try:
                    mtime = entry.stat().st_mtime
                except Exception:
                    mtime = 0.0
                projects.append((mtime, stem))
        except Exception:
            pass

        projects.sort(reverse=True)   # en yeni üstte
        for _, stem in projects:
            self.list_widget.addItem(stem)

        # Mevcut projeyi seçili göster
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).text() == current_name:
                self.list_widget.setCurrentRow(i)
                break

        layout.addWidget(self.list_widget)

        # ---- Yeni proje alanı ----
        layout.addWidget(QLabel("Yeni Proje Adı:"))
        self.new_name_edit = QLineEdit()
        self.new_name_edit.setPlaceholderText("Yeni proje adını buraya yaz…")
        layout.addWidget(self.new_name_edit)

        # Listeden seçim yapılınca yeni ad alanını temizle
        self.list_widget.currentItemChanged.connect(
            lambda cur, _prev: self.new_name_edit.clear() if cur else None
        )
        # Yeni ad yazılınca liste seçimini kaldır
        self.new_name_edit.textChanged.connect(
            lambda txt: self.list_widget.clearSelection() if txt.strip() else None
        )
        # Çift tıkla doğrudan aç
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)

        # ---- Butonlar ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        open_btn = QPushButton("Aç / Oluştur")
        open_btn.setObjectName("openBtn")
        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("cancelBtn")
        open_btn.clicked.connect(self._on_accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(open_btn)
        btn_row.addWidget(cancel_btn)
        layout.addSpacing(4)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.resize(420, 380)

    def _on_double_click(self, item):
        self._result_name = item.text()
        self.accept()

    def _on_accept(self):
        # Yeni ad öncelikli; yoksa listeden al
        new = self.new_name_edit.text().strip()
        if new:
            self._result_name = new
        elif self.list_widget.currentItem():
            self._result_name = self.list_widget.currentItem().text()
        else:
            return   # hiçbiri seçilmemiş
        self.accept()

    def get_name(self) -> str:
        return self._result_name


class SketchFirmaBilgileriDialog(QDialog):
    """Teklifi veren firmanın sabit bilgilerini ve logosunu düzenler."""

    LOGO_MAX_W = 400
    LOGO_MAX_H = 150

    def __init__(self, parent=None, prefill: dict = None, logo_path: str = None):
        super().__init__(parent)
        self.setWindowTitle("Firma Bilgileri")
        self.setModal(True)
        p = prefill or {}
        self._logo_save_path = logo_path
        self._logo_pixmap = QPixmap()
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as _f:
                    _img = QImage()
                    _img.loadFromData(_f.read())
                if not _img.isNull():
                    self._logo_pixmap = QPixmap.fromImage(_img)
            except Exception:
                pass

        self.setStyleSheet("""
        QDialog { background-color: #f9f9f9; }
        QLabel {
            font-family: "Calibri", "Segoe UI", Arial, sans-serif;
            font-size: 11pt; color: #1a1a1a;
        }
        QLabel#section {
            font-size: 11pt; font-weight: bold; color: #003366;
            border-bottom: 2px solid #003366; padding-bottom: 3px;
            margin-top: 4px;
        }
        QLabel#logo_prev {
            border: 2px dashed #bbb; border-radius: 6px;
            background: #fff; color: #999; font-size: 10pt;
        }
        QLineEdit {
            font-family: "Calibri", "Segoe UI", Arial, sans-serif;
            font-size: 11pt; padding: 5px 10px;
            border: 1px solid #bbbbbb; border-radius: 5px;
            background: white; color: #1a1a1a;
        }
        QLineEdit:focus { border-color: #003366; }
        QPushButton {
            font-family: "Calibri", "Segoe UI", Arial, sans-serif;
            font-size: 11pt; font-weight: bold; padding: 8px 24px;
            border: 2px solid #444; border-radius: 6px;
            background: white; color: #222;
        }
        QPushButton#okBtn     { color: white; background: #005500; border-color: #005500; }
        QPushButton#cancelBtn { color: #880000; border-color: #880000; }
        QPushButton#logoBtn   { font-size: 10pt; color: #003399; border-color: #003399;
                                padding: 6px 14px; font-weight: normal; }
        QPushButton#okBtn:hover     { background: #006600; }
        QPushButton#cancelBtn:hover { background: #fff0f0; }
        QPushButton#logoBtn:hover   { background: #eef4ff; }
        """)

        main = QVBoxLayout(self)
        main.setSpacing(8)
        main.setContentsMargins(18, 16, 18, 16)

        def section(txt):
            lbl = QLabel(txt); lbl.setObjectName("section"); return lbl

        def row_field(label, key, placeholder=""):
            hl = QHBoxLayout()
            lb = QLabel(label); lb.setFixedWidth(170)
            ed = QLineEdit()
            ed.setPlaceholderText(placeholder)
            v = p.get(key, "")
            if v: ed.setText(v)
            hl.addWidget(lb); hl.addWidget(ed)
            return hl, ed

        main.addWidget(section("Teklifi Veren Firma"))
        hl, self.e_unvan = row_field("Firma Ünvanı:", "unvan", "Örn. TENSHOOT Mimarlık A.Ş.")
        main.addLayout(hl)
        hl, self.e_adres = row_field("Adres:", "adres", "Mahalle, Sokak No, İlçe / Şehir")
        main.addLayout(hl)
        hl, self.e_vd    = row_field("Vergi Dairesi:", "vd", "Vergi dairesi adı")
        main.addLayout(hl)
        hl, self.e_vno   = row_field("Vergi Numarası:", "vno", "1234567890")
        main.addLayout(hl)
        hl, self.e_iban  = row_field("IBAN:", "iban", "TR00 0000 0000 0000 0000 0000 00")
        main.addLayout(hl)
        hl, self.e_banka = row_field("Banka / Şube:", "banka", "Banka adı ve şube")
        main.addLayout(hl)

        main.addSpacing(8)

        main.addWidget(section(
            f"Firma Logosu  —  maks. {self.LOGO_MAX_W} × {self.LOGO_MAX_H} piksel"
        ))
        logo_hl = QHBoxLayout()
        self._logo_label = QLabel("Logo yüklenmedi")
        self._logo_label.setObjectName("logo_prev")
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_label.setFixedSize(340, 110)
        self._refresh_logo_label()

        logo_btn = QPushButton("Logo Yükle / Değiştir")
        logo_btn.setObjectName("logoBtn")
        logo_btn.clicked.connect(self._pick_logo)

        logo_hl.addWidget(self._logo_label)
        logo_hl.addSpacing(12)
        logo_hl.addWidget(logo_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        logo_hl.addStretch()
        main.addLayout(logo_hl)

        main.addSpacing(12)

        br = QHBoxLayout(); br.addStretch()
        skip_btn   = QPushButton("Geç →");   skip_btn.setObjectName("cancelBtn")
        ok_btn     = QPushButton("Kaydet");  ok_btn.setObjectName("okBtn")
        skip_btn.setToolTip("Değişiklikleri kaydetmeden devam et")
        skip_btn.clicked.connect(self.reject)
        ok_btn.clicked.connect(self.accept)
        br.addWidget(skip_btn); br.addWidget(ok_btn)
        main.addLayout(br)

        self.resize(620, 0)
        self.adjustSize()

    def _refresh_logo_label(self):
        if not self._logo_pixmap.isNull():
            self._logo_label.setPixmap(
                self._logo_pixmap.scaled(336, 106,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            )
            self._logo_label.setText("")
        else:
            self._logo_label.setPixmap(QPixmap())
            self._logo_label.setText("Logo yüklenmedi")

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Logo Dosyası Seç", "",
            "Resim (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if not path:
            return
        # QPixmap(path) macOS'ta sessizce başarısız olabiliyor — bytes ile yükle
        try:
            with open(path, "rb") as _f:
                _img = QImage()
                _img.loadFromData(_f.read())
        except Exception as e:
            QMessageBox.warning(self, "Logo", f"Dosya okunamadı: {e}")
            return
        if _img.isNull():
            QMessageBox.warning(self, "Logo", "Dosya yüklenemedi veya desteklenmiyor.")
            return
        px = QPixmap.fromImage(_img)
        if px.width() > self.LOGO_MAX_W or px.height() > self.LOGO_MAX_H:
            px = px.scaled(self.LOGO_MAX_W, self.LOGO_MAX_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        self._logo_pixmap = px
        self._refresh_logo_label()

    def save_logo_to_disk(self) -> bool:
        if not self._logo_save_path or self._logo_pixmap.isNull():
            return False
        try:
            from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            self._logo_pixmap.toImage().save(buf, "PNG")
            buf.close()
            with open(self._logo_save_path, "wb") as f:
                f.write(ba.data())
            return True
        except Exception:
            return self._logo_pixmap.save(self._logo_save_path, "PNG")

    def get_info(self) -> dict:
        return {
            "unvan": self.e_unvan.text().strip(),
            "adres": self.e_adres.text().strip(),
            "vd":    self.e_vd.text().strip(),
            "vno":   self.e_vno.text().strip(),
            "iban":  self.e_iban.text().strip(),
            "banka": self.e_banka.text().strip(),
        }


class SketchTeklifInfoDialog(QDialog):
    """Teklif hazırlanmadan önce müşteri bilgilerini ve kapsam seçimini toplar."""

    KAPSAM_ITEMS = [
        "Nakliye",
        "Malzemeler",
        "Montaj",
        "Sarf Malzemeleri",
        "Düşey ve yatay taşıma",
        "Sigorta giderleri",
    ]

    def __init__(self, current_project: str, currency: str, prefill: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Teklif Bilgileri")
        self.setModal(True)
        p = prefill or {}

        self.setStyleSheet("""
        QDialog { background-color: #f9f9f9; }
        QLabel, QLineEdit, QCheckBox, QPushButton {
            font-family: "Segoe UI", "Calibri", Arial, sans-serif;
        }
        QLabel {
            font-size: 11pt; color: #1a1a1a;
        }
        QLabel#section {
            font-size: 11pt; font-weight: bold; color: #003366;
            border-bottom: 2px solid #003366; padding-bottom: 3px;
            margin-top: 4px;
        }
        QLineEdit {
            font-size: 11pt; padding: 5px 10px;
            border: 1px solid #bbbbbb; border-radius: 5px;
            background: white; color: #1a1a1a;
        }
        QLineEdit:focus { border-color: #003366; }
        QCheckBox {
            font-size: 11pt; color: #1a1a1a; spacing: 8px;
            background-color: transparent;
        }
        QCheckBox::indicator {
            width: 16px; height: 16px;
            border: 2px solid #888888;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:checked {
            border: 2px solid #003366;
            background-color: #003366;
            border-radius: 3px;
        }
        QPushButton {
            font-size: 11pt; font-weight: bold; padding: 8px 24px;
            border: 2px solid #444; border-radius: 6px;
            background: white; color: #222;
        }
        QPushButton#okBtn     { color: white; background: #005500; border-color: #005500; }
        QPushButton#cancelBtn { color: #880000; border-color: #880000; }
        QPushButton#okBtn:hover     { background: #006600; }
        QPushButton#cancelBtn:hover { background: #fff0f0; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(18, 16, 18, 16)

        def section(text):
            lbl = QLabel(text)
            lbl.setObjectName("section")
            return lbl

        def field(label_text, placeholder="", default="", saved_key=""):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(160)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            val = p.get(saved_key, default) if saved_key else default
            if val:
                edit.setText(val)
            row.addWidget(lbl)
            row.addWidget(edit)
            return row, edit

        # ── Teklif Bilgileri ──
        layout.addWidget(section("Teklif Bilgileri"))
        r, self.teklif_no_edit  = field("Teklif No:",         "örn. 2026-001",  p.get("teklif_no", ""), "teklif_no")
        layout.addLayout(r)
        r, self.hazirlayan_edit = field("Hazırlayan:",         "Ad Soyad",       p.get("hazirlayan", ""), "hazirlayan")
        layout.addLayout(r)
        r, self.sure_edit       = field("Geçerlilik Süresi:",  "örn. 30 gün",    p.get("sure", "30 gün"), "sure")
        layout.addLayout(r)

        cur_row = QHBoxLayout()
        cur_lbl = QLabel("Para Birimi:")
        cur_lbl.setFixedWidth(160)
        cur_val = QLabel(f"<b>{currency}</b>")
        cur_row.addWidget(cur_lbl)
        cur_row.addWidget(cur_val)
        cur_row.addStretch()
        layout.addLayout(cur_row)

        layout.addSpacing(4)

        # ── Müşteri Bilgileri ──
        layout.addWidget(section("Müşteri Bilgileri"))
        r, self.proje_edit = field("Proje Adı:",    "Proje adını yazın",   current_project,            "proje")
        layout.addLayout(r)
        r, self.kisi_edit  = field("İlgili Kişi:",  "Ad Soyad",            p.get("kisi", ""),           "kisi")
        layout.addLayout(r)
        r, self.firma_edit = field("Firma İsmi:",   "Firma adı",           p.get("firma", ""),          "firma")
        layout.addLayout(r)
        r, self.mail_edit  = field("E-Posta:",       "ornek@firma.com",     p.get("mail", ""),           "mail")
        layout.addLayout(r)
        r, self.tel_edit   = field("Telefon:",       "+90 5xx xxx xx xx",   p.get("tel", ""),            "tel")
        layout.addLayout(r)

        layout.addSpacing(4)

        # ── Kapsam ──
        layout.addWidget(section("Fiyata Dahil Olan Kalemler"))
        saved_dahil = set(p.get("dahil", self.KAPSAM_ITEMS))  # default: hepsi dahil
        self.chk = {}
        from PyQt6.QtWidgets import QCheckBox as _CB
        grid = QHBoxLayout()
        col1, col2 = QVBoxLayout(), QVBoxLayout()
        for i, item in enumerate(self.KAPSAM_ITEMS):
            cb = _CB(item)
            cb.setChecked(item in saved_dahil)
            self.chk[item] = cb
            (col1 if i % 2 == 0 else col2).addWidget(cb)
        grid.addLayout(col1)
        grid.addLayout(col2)
        layout.addLayout(grid)

        layout.addSpacing(6)

        # ── Ek maddeler (serbest metin) ──
        ek_label = QLabel("Ek Maddeler:")
        ek_label.setObjectName("section")
        layout.addWidget(ek_label)
        saved_ek = p.get("ek_maddeler", ["", ""])
        self.ek1 = QLineEdit(saved_ek[0] if len(saved_ek) > 0 else "")
        self.ek2 = QLineEdit(saved_ek[1] if len(saved_ek) > 1 else "")
        self.ek1.setPlaceholderText("Ek madde 1 (isteğe bağlı)")
        self.ek2.setPlaceholderText("Ek madde 2 (isteğe bağlı)")
        layout.addWidget(self.ek1)
        layout.addWidget(self.ek2)

        layout.addSpacing(10)

        # ── Butonlar ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn     = QPushButton("Devam →")
        ok_btn.setObjectName("okBtn")
        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("cancelBtn")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.resize(520, 0)
        self.adjustSize()

    def get_info(self) -> dict:
        dahil       = [k for k, cb in self.chk.items() if cb.isChecked()]
        dahil_degil = [k for k, cb in self.chk.items() if not cb.isChecked()]
        ek1 = self.ek1.text().strip()
        ek2 = self.ek2.text().strip()
        return {
            "teklif_no":   self.teklif_no_edit.text().strip(),
            "hazirlayan":  self.hazirlayan_edit.text().strip(),
            "proje":       self.proje_edit.text().strip(),
            "kisi":        self.kisi_edit.text().strip(),
            "firma":       self.firma_edit.text().strip(),
            "mail":        self.mail_edit.text().strip(),
            "tel":         self.tel_edit.text().strip(),
            "sure":        self.sure_edit.text().strip(),
            "dahil":       dahil,
            "dahil_degil": dahil_degil,
            "ek_maddeler": [ek1, ek2],
        }


class SketchCurrencyChoiceDialog(QDialog):
    def __init__(self, title: str, current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        self.setStyleSheet("""
        QDialog { background-color: white; border: 2px solid #444444; color: #111111; }
        QLabel, QComboBox, QPushButton { color: #111111; background-color: white; }
        QLabel { font-size: 12pt; }
        QComboBox {
            font-size: 12pt;
            padding: 6px 10px;
            border: 2px solid #444444;
            border-radius: 8px;
        }
        QComboBox QAbstractItemView {
            background-color: white;
            color: #111111;
            selection-background-color: #eaf2ff;
            selection-color: #111111;
        }
        QPushButton {
            font-size: 12pt;
            padding: 8px 18px;
            border: 2px solid #444444;
            border-radius: 16px;
        }
        QPushButton#okButton { color: #b00000; border-color: #b00000; }
        QPushButton#cancelButton { color: #004488; border-color: #004488; }
        """)

        info = QLabel("Hesap/Tablo para birimi:")
        self.combo = QComboBox()
        self.combo.addItems(["TL", "USD", "EUR"])
        cur = str(current or "USD").upper()
        self.combo.setCurrentText(cur if cur in ("TL", "USD", "EUR") else "USD")

        ok_btn = QPushButton("Onay")
        ok_btn.setObjectName("okButton")
        cancel_btn = QPushButton("Vazgeç")
        cancel_btn.setObjectName("cancelButton")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn = QHBoxLayout()
        btn.addStretch()
        btn.addWidget(ok_btn)
        btn.addWidget(cancel_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addWidget(self.combo)
        lay.addSpacing(8)
        lay.addLayout(btn)

        self.resize(360, 160)

    def get_currency(self) -> str:
        return str(self.combo.currentText() or "USD").upper()


class SketchPriceUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TenShoot Fiyat Analiz Yardımcı ARAYÜZ Ver: 2.0")
        self.setStyleSheet("background-color: white;")

        # Çizim yapılacak sanal sayfa boyutu (scroll bunun üzerinde gezecek)
        self.canvas_width = 1400
        self.canvas_height = 1600

        # Widget boyutunu bu canvas boyutuna sabitliyoruz
        self.resize(self.canvas_width, self.canvas_height)
        self.setMinimumSize(1200, 1200)

        # Arkaplan beyaz kalsın
        self.setAutoFillBackground(True)
        self.setStyleSheet("background-color: white;")


        # Platforma göre font seçimi
        if sys.platform == "darwin":  # macOS
            # Teknik çizim hissi veren ve okunaklı bir font
            self.base_font_family = "Menlo"
        else:  # Windows (veya diğerleri)
            self.base_font_family = "Segoe Print"

        # UI ölçeği – macOS retina'da yazıları büyüt
        if sys.platform == "darwin":
            self.ui_scale = 1.55
            self.panel_font_scale = 1.22
        else:
            self.ui_scale = 1.0
            self.panel_font_scale = 1.0



        # Varsayılan kategoriler (eğer JSON yoksa bunlar kullanılacak)
        self.material_categories = [
            {"name": "Nero Marquina 2 cm", "unit": "m²", "price": 120.0},
            {"name": "Amasya Bej 3 cm", "unit": "m²", "price": 95.0},
            {"name": "Valentino Grey 2 cm", "unit": "m²", "price": 110.0},
        ]
        self.labor_categories = [
            {"name": "Ebatlama", "unit": "m²", "price": 25.0},
            {"name": "El İşçiliği", "unit": "saat", "price": 40.0},
            {"name": "CNC Frezeleme", "unit": "m²", "price": 60.0},
            {"name": "Kurt Ağızı Açma", "unit": "mt", "price": 15.0},
            {"name": "Fuga Açma", "unit": "mt", "price": 10.0},
            {"name": "Yüzey Cilalama", "unit": "m²", "price": 35.0},
            {"name": "Su Jeti Kesimi", "unit": "mt", "price": 50.0},
        ]

        # Serbest Fire Hesaplama 
        self.free_waste_rect = QRectF()

        # Para birimi ayarları (JSON yüklemeden önce hazır olmalı)
        self.usd_rate = 40.0
        self.eur_rate = 45.0
        self.offer_currency = "USD"

        # Teklif simülasyonu için kâr yüzdeleri (JSON yüklemeden önce hazır olmalı)
        self.material_profit_percent = 25.0
        self.labor_profit_percents = {}

        # Aktif proje adı (path fonksiyonlarından önce hazır olmalı)
        self.current_project_name = ""

        # JSON'dan yükle (varsa)
        self.load_categories_from_json()

        # Keypad (basit hesap makinesi)
        self.keypad_rows = [
            ["7", "8", "9", "÷"],
            ["4", "5", "6", "×"],
            ["1", "2", "3", "-"],
            [",", "0", "=", "+"],
            ["C", "←"],
        ]

        # STATE
        self.preview_raw = ""      # miktar girişi (metin)
        self.line_total = 0.0      # bu satır toplamı
        self.current_components = []  # {"name","amount","unit","price","subtotal"}

        # Bu satırın ürün adı (merkez balon üstündeki yazı)
        self.current_product_name = "Ürün Adı"

        # Export edilmiş satırlar (teklif tablosu)
        self.exported_items = []   # {"name","unit_price","components_summary"}

        # Seçili kategori: ("material"/"labor", index)
        self.active_category = None

        # Çizim için alan referansları
        self.center_rect = QRectF()
        self.center_title_rect = QRectF()
        self.project_name_rect = QRectF()
        self.reset_rect = QRectF()
        self.preview_box_rect = QRectF()
        self.keypad_buttons = []
        self.material_rects = []
        self.labor_rects = []
        self.material_price_rects = []
        self.labor_price_rects = []
        self.material_profit_rect = QRectF()
        self.labor_profit_rects = []
        self.component_delete_rects = []

        # Malzeme / işçilik için + ve - balonları
        self.mat_plus_rect = QRectF()
        self.mat_minus_rect = QRectF()
        self.lab_plus_rect = QRectF()
        self.lab_minus_rect = QRectF()

         # Dışa aktar balonu alanı
        self.export_rect = QRectF()
        # "Aktarılan ürün sayısı" yazısının tıklanabilir alanı
        self.export_count_rect = QRectF()
        self.edit_rect = QRectF()
        self.report_rect = QRectF()
        self.teklif_rect = QRectF()

        self.usd_rate_rect = QRectF()
        self.eur_rate_rect = QRectF()
        self.offer_currency_rect = QRectF()

        # Sağ panel: kâr ayarları tıklanabilir alanları
        self.material_profit_rect = QRectF()
        self.labor_profit_rects = []
        self.component_delete_rects = []

        # Drag & drop için
        self.dragging_category = None   # ("material"/"labor", index) veya None


        # Export edilmiş satırlar (teklif tablosu)
        self.exported_items = []   # {"name","unit_price","components_summary"}


    # --------- KATEGORİ YÜKLEME / KAYDETME ---------

    def load_categories_from_json(self):
        """
        O anki proje adına göre kategoriler_*.json dosyasını okuyup
        malzeme / işçilik listelerini doldurur.
        """
        path = self.get_categories_json_path()
        if not os.path.exists(path):
            # Bu proje için daha önce kategori kaydedilmemiş olabilir.
            # Varsayılan kâr oranı %25 olsun.
            self.material_profit_percent = 25.0
            for cat in self.labor_categories:
                name = str(cat.get("name", "") or "").strip()
                if name:
                    self.labor_profit_percents[name] = float(self.labor_profit_percents.get(name, 25.0))
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("kategoriler JSON okunamadı:", e)
            return

        mats = data.get("malzeme")
        labs = data.get("iscilik")

        if isinstance(mats, list):
            self.material_categories = mats
        if isinstance(labs, list):
            self.labor_categories = labs

        for cat in self.material_categories:
            if not (cat.get("currency") or "").strip():
                cat["currency"] = "USD"
        for cat in self.labor_categories:
            if not (cat.get("currency") or "").strip():
                cat["currency"] = "USD"

        kar_cfg = data.get("kar_simulasyon", {}) if isinstance(data, dict) else {}
        para_cfg = data.get("para_ayarlari", {}) if isinstance(data, dict) else {}

        try:
            loaded_mat_profit = float(kar_cfg.get("material_profit_percent", 25.0))
        except (TypeError, ValueError):
            loaded_mat_profit = 25.0
        self.material_profit_percent = max(0.0, loaded_mat_profit)

        loaded_labor_profits = kar_cfg.get("labor_profit_percents", {})
        if isinstance(loaded_labor_profits, dict):
            self.labor_profit_percents = {}
            for key, val in loaded_labor_profits.items():
                try:
                    self.labor_profit_percents[str(key)] = max(0.0, float(val))
                except (TypeError, ValueError):
                    self.labor_profit_percents[str(key)] = 25.0
        else:
            self.labor_profit_percents = {}

        try:
            self.usd_rate = max(0.0001, float(para_cfg.get("usd_rate", self.usd_rate)))
        except (TypeError, ValueError):
            pass
        try:
            self.eur_rate = max(0.0001, float(para_cfg.get("eur_rate", self.eur_rate)))
        except (TypeError, ValueError):
            pass
        offer_cur = str(para_cfg.get("offer_currency", self.offer_currency) or "USD").upper()
        self.offer_currency = offer_cur if offer_cur in ("TL", "USD", "EUR") else "USD"

        # Eksik işçilik kalemlerini varsayılan %25 ile tamamla
        for cat in self.labor_categories:
            name = str(cat.get("name", "") or "").strip()
            if name and name not in self.labor_profit_percents:
                self.labor_profit_percents[name] = 25.0


    def save_categories_to_json(self):
        """
        O anki proje adına göre kategoriler_*.json dosyasına
        malzeme / işçilik listelerini yazar.
        """
        path = self.get_categories_json_path()
        data = {
            "malzeme": self.material_categories,
            "iscilik": self.labor_categories,
            "kar_simulasyon": {
                "material_profit_percent": float(self.material_profit_percent),
                "labor_profit_percents": self.labor_profit_percents,
            },
            "para_ayarlari": {
                "usd_rate": float(self.usd_rate),
                "eur_rate": float(self.eur_rate),
                "offer_currency": self.offer_currency,
            },
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Kaydetme Hatası",
                f"Kategori dosyası yazılırken hata oluştu:\n{e}",
            )


    def get_categories_json_path(self) -> str:
        return os.path.join(self.get_project_dir(), "kategoriler.json")


    # --------- YARDIMCILAR ---------

    def draw_sketch_ellipse(self, painter, rect: QRectF, color: QColor,
                             fill_alpha=0, pen_width=2, hatch=False):
        """Kalem hissi için jitter'lı elips ve (istersek) iç tarama."""
        # Dış hat kalemi
        pen = QPen(color, pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Hafif şeffaf doldurma (seçili balon için)
        if fill_alpha > 0:
            brush = QBrush(QColor(color.red(), color.green(), color.blue(), fill_alpha))
        else:
            brush = Qt.BrushStyle.NoBrush
        painter.setBrush(brush)

        # Dış hattı birkaç kez jitter'lı çiz
        for _ in range(3):
            dx = random.randint(-2, 2)
            dy = random.randint(-2, 2)
            rect_jitter = rect.adjusted(dx, dy, -dx, -dy)
            painter.drawEllipse(rect_jitter)

        # Seçili balon için iç tarama
        if hatch:
            painter.save()

            # Elipsi clip alanı yap -> çizgiler sadece balonun içinde görünür
            path = QPainterPath()
            path.addEllipse(rect)
            painter.setClipPath(path)

            hatch_pen = QPen(color, 1)
            hatch_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(hatch_pen)

            step = 5
            x0 = rect.left()
            y0 = rect.top()
            max_len = int(rect.width() + rect.height())

            # Diyagonal çizgiler, clip sayesinde sadece elips içinde kalır
            for i in range(0, max_len, step):
                p1 = QPointF(x0 + i, y0)
                p2 = QPointF(x0, y0 + i)
                painter.drawLine(p1, p2)

            painter.restore()
    def apply_category_edit_to_lines(self, old_name: str, new_cat: dict):
        """
        Bir MALZEME kategorisinin (isim/fiyat/fire) değişikliğini,
        o malzemeyi kullanan TÜM bileşenlere uygular.
        - Miktarları aynen bırakır
        - Birim fiyatı ve subtotali yeniden hesaplar
        """
        effective_price, waste_percent = self.effective_material_price_from_category(new_cat)
        try:
            base_price = float(new_cat.get("price", 0.0))
        except (TypeError, ValueError):
            base_price = 0.0

        new_name = new_cat.get("name", old_name)
        new_unit = new_cat.get("unit", "")
        new_currency = str(new_cat.get("currency", "USD") or "USD").upper()
        effective_offer_price = self.convert_currency(effective_price, new_currency, self.offer_currency)

        # 1) Export edilmiş satırlar
        for item in self.exported_items:
            comps = item.get("components") or []
            changed = False
            for c in comps:
                if c.get("group") == "material" and c.get("name") == old_name:
                    try:
                        amt = float(c.get("amount", 0.0))
                    except (TypeError, ValueError):
                        amt = 0.0

                    c["name"] = new_name
                    c["unit"] = new_unit or c.get("unit", "")
                    c["base_price"] = base_price
                    c["currency"] = new_currency
                    c["waste_percent"] = waste_percent
                    c["price"] = effective_offer_price
                    c["subtotal"] = amt * effective_offer_price
                    changed = True

            if changed:
                # Satır toplamını ve özeti güncelle
                item["unit_price"] = sum(
                    float(c.get("subtotal", 0.0)) for c in comps
                )
                item["components_summary"] = self.build_components_summary(comps)
                item["components"] = comps

        # 2) Şu anda merkez balonda duran (henüz dışa aktarılmamış) satır
        if self.current_components:
            line_changed = False
            for c in self.current_components:
                if c.get("group") == "material" and c.get("name") == old_name:
                    try:
                        amt = float(c.get("amount", 0.0))
                    except (TypeError, ValueError):
                        amt = 0.0

                    c["name"] = new_name
                    c["unit"] = new_unit or c.get("unit", "")
                    c["base_price"] = base_price
                    c["currency"] = new_currency
                    c["waste_percent"] = waste_percent
                    c["price"] = effective_offer_price
                    c["subtotal"] = amt * effective_offer_price
                    line_changed = True

            if line_changed:
                self.line_total = sum(
                    float(c.get("subtotal", 0.0)) for c in self.current_components
                )

        # 3) Proje tanımlıysa CSV'yi de güncelle
        if self.current_project_name.strip() and self.exported_items:
            self.write_offer_to_csv()        # proje hafızası
            self.write_offer_teklif_csv()    # Excel/Teklif dosyası

        self.update()


    def apply_labor_price_edit_to_lines(self, old_name: str, new_cat: dict):
        """
        Bir İŞÇİLİK kategorisinin birim fiyatı değiştiğinde
        onu kullanan tüm bileşenleri ve satır toplamlarını günceller.
        """
        try:
            new_price = float(new_cat.get("price", 0.0) or 0.0)
        except (TypeError, ValueError):
            new_price = 0.0
        new_currency = str(new_cat.get("currency", "USD") or "USD").upper()
        new_name = new_cat.get("name", old_name)
        new_unit = new_cat.get("unit", "")

        # Export edilmiş satırlar
        for item in self.exported_items:
            comps = item.get("components") or []
            changed = False
            for c in comps:
                if c.get("group") == "labor" and c.get("name") == old_name:
                    try:
                        amt = float(c.get("amount", 0.0))
                    except (TypeError, ValueError):
                        amt = 0.0

                    offer_price = self.convert_currency(new_price, new_currency, self.offer_currency)
                    c["name"] = new_name
                    c["unit"] = new_unit or c.get("unit", "")
                    c["currency"] = new_currency
                    c["base_price"] = new_price
                    c["price"] = offer_price
                    c["subtotal"] = amt * offer_price
                    changed = True

            if changed:
                item["unit_price"] = sum(
                    float(c.get("subtotal", 0.0)) for c in comps
                )
                item["components_summary"] = self.build_components_summary(comps)
                item["components"] = comps

        # Merkez balondaki satır
        if self.current_components:
            line_changed = False
            for c in self.current_components:
                if c.get("group") == "labor" and c.get("name") == old_name:
                    try:
                        amt = float(c.get("amount", 0.0))
                    except (TypeError, ValueError):
                        amt = 0.0

                    offer_price = self.convert_currency(new_price, new_currency, self.offer_currency)
                    c["name"] = new_name
                    c["unit"] = new_unit or c.get("unit", "")
                    c["currency"] = new_currency
                    c["base_price"] = new_price
                    c["price"] = offer_price
                    c["subtotal"] = amt * offer_price
                    line_changed = True

            if line_changed:
                self.line_total = sum(
                    float(c.get("subtotal", 0.0)) for c in self.current_components
                )

        if self.current_project_name.strip() and self.exported_items:
            self.write_offer_to_csv()

        self.update()

    def draw_center_text(self, painter, rect: QRectF, text: str,
                         color: QColor, point_size: int):
        # mac versiyonunda yazıları topluca büyütmek için ölçek
        scale = getattr(self, "ui_scale", 1.0)
        real_pt = int(round(point_size * scale))

        font = QFont(self.base_font_family, real_pt)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def draw_center_wrapped_text(self, painter, rect: QRectF, text: str,
                                 color: QColor, point_size: int, max_lines: int = 3):
        scale = getattr(self, "ui_scale", 1.0)
        real_pt = int(round(point_size * scale))

        font = QFont(self.base_font_family, real_pt)
        painter.setFont(font)
        painter.setPen(color)

        raw = " ".join((text or "").split())
        if not raw:
            raw = "Ürün Adı"

        fm = QFontMetricsF(font)
        max_w = max(10.0, rect.width() - 8.0)

        words = raw.split(" ")
        lines = []
        current = ""
        for w in words:
            candidate = w if not current else f"{current} {w}"
            if fm.horizontalAdvance(candidate) <= max_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = fm.elidedText(lines[-1], Qt.TextElideMode.ElideRight, max_w)

        if not lines:
            lines = ["Ürün Adı"]

        line_h = fm.height()
        total_h = line_h * len(lines)
        y = rect.center().y() - total_h / 2.0

        for line in lines:
            line_rect = QRectF(rect.left() + 4, y, rect.width() - 8, line_h)
            painter.drawText(
                line_rect,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter),
                line,
            )
            y += line_h


    def format_amount(self, value: float) -> str:
        s = f"{value:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        if s.endswith(",00"):
            s = s[:-3]
        return s

    def panel_font_size(self, point_size: int) -> int:
        scale = getattr(self, "panel_font_scale", 1.0)
        return max(8, int(round(point_size * scale)))

    def to_try(self, amount: float, currency: str) -> float:
        c = str(currency or "TL").upper()
        if c == "USD":
            return amount * self.usd_rate
        if c == "EUR":
            return amount * self.eur_rate
        return amount

    def from_try(self, amount_try: float, currency: str) -> float:
        c = str(currency or "TL").upper()
        if c == "USD":
            return amount_try / self.usd_rate if self.usd_rate else 0.0
        if c == "EUR":
            return amount_try / self.eur_rate if self.eur_rate else 0.0
        return amount_try

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        return self.from_try(self.to_try(float(amount), from_currency), to_currency)

    def recalculate_all_prices_for_offer_currency(self):
        # Export edilmiş ürünler
        for item in self.exported_items:
            comps = item.get("components") or []
            for c in comps:
                try:
                    amt = float(c.get("amount", 0.0) or 0.0)
                except (TypeError, ValueError):
                    amt = 0.0
                group = c.get("group")
                currency = str(c.get("currency", self.offer_currency) or self.offer_currency).upper()
                try:
                    base_price = float(c.get("base_price", c.get("price", 0.0)) or 0.0)
                except (TypeError, ValueError):
                    base_price = 0.0
                if group == "material":
                    try:
                        waste_percent = float(c.get("waste_percent", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        waste_percent = 0.0
                    ratio = 1.0 - max(0.0, waste_percent) / 100.0
                    eff_native = base_price / ratio if ratio > 0 else base_price
                    eff_offer = self.convert_currency(eff_native, currency, self.offer_currency)
                else:
                    eff_offer = self.convert_currency(base_price, currency, self.offer_currency)
                c["price"] = eff_offer
                c["subtotal"] = amt * eff_offer
            item["unit_price"] = sum(float(c.get("subtotal", 0.0) or 0.0) for c in comps)
            item["components_summary"] = self.build_components_summary(comps)
            item["components"] = comps

        # Merkezdeki satır
        for c in self.current_components:
            try:
                amt = float(c.get("amount", 0.0) or 0.0)
            except (TypeError, ValueError):
                amt = 0.0
            group = c.get("group")
            currency = str(c.get("currency", self.offer_currency) or self.offer_currency).upper()
            try:
                base_price = float(c.get("base_price", c.get("price", 0.0)) or 0.0)
            except (TypeError, ValueError):
                base_price = 0.0
            if group == "material":
                try:
                    waste_percent = float(c.get("waste_percent", 0.0) or 0.0)
                except (TypeError, ValueError):
                    waste_percent = 0.0
                ratio = 1.0 - max(0.0, waste_percent) / 100.0
                eff_native = base_price / ratio if ratio > 0 else base_price
                eff_offer = self.convert_currency(eff_native, currency, self.offer_currency)
            else:
                eff_offer = self.convert_currency(base_price, currency, self.offer_currency)
            c["price"] = eff_offer
            c["subtotal"] = amt * eff_offer

        self.line_total = sum(float(c.get("subtotal", 0.0) or 0.0) for c in self.current_components)

    def _normalize_expr(self, expr: str) -> str:
        return (
            (expr or "")
            .replace("×", "*")
            .replace("÷", "/")
            .replace(",", ".")
            .strip()
        )

    def _safe_eval_expr(self, expr: str) -> float:
        normalized = self._normalize_expr(expr)
        if not normalized:
            return 0.0

        node = ast.parse(normalized, mode="eval")

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return float(n.value)
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
                val = _eval(n.operand)
                return val if isinstance(n.op, ast.UAdd) else -val
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                left = _eval(n.left)
                right = _eval(n.right)
                if isinstance(n.op, ast.Add):
                    return left + right
                if isinstance(n.op, ast.Sub):
                    return left - right
                if isinstance(n.op, ast.Mult):
                    return left * right
                if right == 0:
                    raise ZeroDivisionError
                return left / right
            raise ValueError("Geçersiz ifade")

        return float(_eval(node))

    def _format_calc_result(self, value: float) -> str:
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        if text in ("", "-"):
            text = "0"
        return text.replace(".", ",")

    def preview_value(self) -> float:
        try:
            return self._safe_eval_expr(self.preview_raw)
        except Exception:
            return 0.0

    # --------- ETKİLEŞİM: MOUSE ---------

    def mousePressEvent(self, event):
        pos = event.position()

        # Serbest fire hesapla
        if self.free_waste_rect is not None and self.free_waste_rect.contains(pos):
            dlg = SketchFreeWasteDialog(self)
            dlg.exec()
            self.update()
            return

        if self.report_rect is not None and self.report_rect.contains(pos):
            self.export_project_report_pdf()
            return

        if self.teklif_rect is not None and self.teklif_rect.contains(pos):
            self._ask_teklif_format()
            return

        if self.usd_rate_rect.contains(pos):
            dlg = SketchPriceDialog("USD Kuru (1 USD = ? TL)", float(self.usd_rate), self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.usd_rate = max(0.0001, dlg.get_price())
                self.recalculate_all_prices_for_offer_currency()
                self.save_categories_to_json()
                self.update()
            return

        if self.eur_rate_rect.contains(pos):
            dlg = SketchPriceDialog("EUR Kuru (1 EUR = ? TL)", float(self.eur_rate), self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.eur_rate = max(0.0001, dlg.get_price())
                self.recalculate_all_prices_for_offer_currency()
                self.save_categories_to_json()
                self.update()
            return

        if self.offer_currency_rect.contains(pos):
            dlg = SketchCurrencyChoiceDialog("Teklif Para Birimi", self.offer_currency, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                choice = dlg.get_currency()
                if choice in ("TL", "USD", "EUR"):
                    self.offer_currency = choice
                    self.recalculate_all_prices_for_offer_currency()
                    self.save_categories_to_json()
                    self.update()
            return

        # Önce + / - balonları
        if self.mat_plus_rect.contains(pos):
            self.add_category_dialog("material")
            return
        if self.mat_minus_rect.contains(pos):
            self.remove_category_dialog("material")
            return
        if self.lab_plus_rect.contains(pos):
            self.add_category_dialog("labor")
            return
        if self.lab_minus_rect.contains(pos):
            self.remove_category_dialog("labor")
            return

        # Fiyat balonlarına tıklama -> fiyat düzenleme
        for idx, rect in enumerate(self.material_price_rects):
            if rect.contains(pos):
                self.edit_price_dialog("material", idx)
                return
        for idx, rect in enumerate(self.labor_price_rects):
            if rect.contains(pos):
                self.edit_price_dialog("labor", idx)
                return

        # Tuş takımı
        for btn in self.keypad_buttons:
            if btn["rect"].contains(pos):
                self.handle_key(btn["label"])
                return

        if self.material_profit_rect.contains(pos):
            dlg = SketchPriceDialog(
                "Malzeme Kâr %",
                float(self.material_profit_percent if self.material_profit_percent is not None else 25.0),
                self,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.material_profit_percent = max(0.0, dlg.get_price())
                self.save_categories_to_json()
                self.update()
            return

        for row in self.labor_profit_rects:
            rect = row.get("rect")
            name = row.get("name", "")
            if rect is not None and rect.contains(pos):
                current = float(self.labor_profit_percents.get(name, 25.0))
                dlg = SketchPriceDialog(f"{name} Kâr %", current, self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self.labor_profit_percents[name] = max(0.0, dlg.get_price())
                    self.save_categories_to_json()
                    self.update()
                return

        # SIFIRLA balonu
        if self.reset_rect.contains(pos):
            self.reset_values()
            return

        # Malzeme balonları (seçim + sürükleme başlangıcı)
        for idx, rect in enumerate(self.material_rects):
            if rect.contains(pos):
                self.active_category = ("material", idx)
                self.dragging_category = ("material", idx)
                self.drag_position = pos
                self.update()
                return

        # İşçilik balonları (seçim + sürükleme başlangıcı)
        for idx, rect in enumerate(self.labor_rects):
            if rect.contains(pos):
                self.active_category = ("labor", idx)
                self.dragging_category = ("labor", idx)
                self.drag_position = pos
                self.update()
                return

        # Dışa Aktar balonu
        if self.export_rect.contains(pos):
            self.export_current_line()
            return

        # Değiştir balonu
        if self.edit_rect.contains(pos):
            self.show_exported_items_dialog()
            return

        # Bu satır bileşenleri -> tekil sil ikonu
        for row in self.component_delete_rects:
            rect = row.get("rect")
            idx = int(row.get("index", -1))
            if rect is not None and rect.contains(pos) and idx >= 0:
                self.remove_component_at(idx)
                return

        # Merkez balon başlığı (ürün adı) – tıklayınca adını düzenle
        if self.center_title_rect.contains(pos):
            self.edit_product_name()
            return

        # EN SON: Proje adı satırı -> tıklayınca proje diyalogunu aç
        if self.project_name_rect.contains(pos):
            dlg = SketchProjectDialog(self.current_project_name, self)
            result = dlg.exec()
            if result == QDialog.DialogCode.Accepted:
                new_name = dlg.get_name()
                if new_name:
                    self.set_project_name(new_name)
            return



    def mouseMoveEvent(self, event):
        if self.dragging_category is not None:
            self.drag_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        pos = event.position()
        if self.dragging_category is not None:
            if self.center_rect.contains(pos):
                self.drop_active_category_into_center()
            self.dragging_category = None
            self.update()

    # --------- LOGİK: TUŞLAR, RESET, DROP, KATEGORİ İŞLEMLERİ ---------

    def handle_key(self, label: str):
        operators = {"+", "-", "×", "÷"}

        if label == "C":
            self.preview_raw = ""
            self.update()
            return

        if label == "←":
            if self.preview_raw:
                self.preview_raw = self.preview_raw[:-1]
            self.update()
            return

        if label == "=":
            try:
                result = self._safe_eval_expr(self.preview_raw)
                self.preview_raw = self._format_calc_result(result)
            except Exception:
                self.preview_raw = ""
            self.update()
            return

        if label in operators:
            if not self.preview_raw:
                if label == "-":
                    self.preview_raw = "-"
            elif self.preview_raw[-1] in operators:
                self.preview_raw = self.preview_raw[:-1] + label
            else:
                self.preview_raw += label
            self.update()
            return

        if label == ",":
            segment = self.preview_raw
            for op in operators:
                segment = segment.split(op)[-1]
            if "," not in segment:
                if not self.preview_raw or self.preview_raw[-1] in operators:
                    self.preview_raw += "0,"
                else:
                    self.preview_raw += ","
            self.update()
            return

        if label.isdigit():
            self.preview_raw += label
            self.update()
            return

    def reset_values(self):
        self.preview_raw = ""
        self.line_total = 0.0
        self.current_components = []
        self.update()

    def remove_component_at(self, index: int):
        if index < 0 or index >= len(self.current_components):
            return

        comp = self.current_components[index]
        name = comp.get("name", "Bu bileşen")
        confirm_box = QMessageBox(self)
        confirm_box.setIcon(QMessageBox.Icon.Question)
        confirm_box.setWindowTitle("Bileşeni sil")
        confirm_box.setText(f"'{name}' bileşenini bu satırdan silmek istediğine emin misin?")
        confirm_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        yes_btn = confirm_box.button(QMessageBox.StandardButton.Yes)
        no_btn = confirm_box.button(QMessageBox.StandardButton.No)
        if yes_btn is not None:
            yes_btn.setText("Evet")
        if no_btn is not None:
            no_btn.setText("Vazgeç")

        confirm_box.setStyleSheet(
            "QMessageBox { background-color: #ffffff; color: #111111; }"
            "QLabel { color: #111111; font-size: 11pt; }"
            "QPushButton {"
            " color: #111111;"
            " background-color: #ececec;"
            " border: 1px solid #5f5f5f;"
            " padding: 6px 16px;"
            " border-radius: 6px;"
            " font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #e2e2e2; }"
            "QPushButton:pressed { background-color: #d8d8d8; }"
        )

        if confirm_box.exec() != int(QMessageBox.StandardButton.Yes):
            return

        del self.current_components[index]
        self.line_total = sum(float(c.get("subtotal", 0.0) or 0.0) for c in self.current_components)
        self.update()

    def get_active_category_obj(self):
        if self.active_category is None:
            return None
        group, idx = self.active_category
        if group == "material":
            if 0 <= idx < len(self.material_categories):
                return self.material_categories[idx]
        else:
            if 0 <= idx < len(self.labor_categories):
                return self.labor_categories[idx]
        return None

    def drop_active_category_into_center(self):
        # Hangi gruptan geldiğimizi (malzeme / işçilik) öğren
        if self.active_category is None:
            return
        group, idx = self.active_category  # "material" veya "labor"

        cat = self.get_active_category_obj()
        if cat is None:
            return

        amount = self.preview_value()
        if amount <= 0:
            return

        # Tedarikçi birim fiyatı (senin yazdığın fiyat)
        base_price = float(cat.get("price", 0.0))
        source_currency = str(cat.get("currency", "USD") or "USD").upper()
        effective_price = base_price
        waste_percent = 0.0

        if group == "material":
            # Kategoriye kaydedilmiş fire yüzdesi
            try:
                waste_percent = float(cat.get("waste_percent", 0.0))
            except (TypeError, ValueError):
                waste_percent = 0.0

            if waste_percent < 0:
                waste_percent = 0.0

            if waste_percent >= 100.0:
                # %100 ve üstü mantıksız, uyar ve firesiz hesapla
                QMessageBox.warning(
                    self,
                    "Geçersiz fire",
                    "Fire oranı %100 veya üzerinde olamaz.\n"
                    "Bu malzeme fire hesaba katılmadan eklenecek."
                )
            else:
                oran = 1.0 - (waste_percent / 100.0)
                if oran > 0:
                    # Asıl istediğin formül:
                    # efektif_fiyat = tedarikçi_fiyatı / (1 - fire_oranı)
                    effective_price = base_price / oran
                else:
                    effective_price = base_price  # emniyet

        # İşçilikte fire yok, direkt base_price kullanılır
        offer_price = self.convert_currency(effective_price, source_currency, self.offer_currency)
        subtotal = amount * offer_price
        self.line_total += subtotal

        # Bileşen kaydı – hem efektif fiyatı hem baz fiyatı tutuyoruz
        comp = {
            "name": cat.get("name", ""),
            "amount": amount,
            "unit": cat.get("unit", ""),
            "price": offer_price,           # Teklife yansıyan (teklif para biriminde)
            "base_price": base_price,        # Kaynak para birimindeki fiyat
            "currency": source_currency,
            "waste_percent": waste_percent,  # Malzeme ise anlamlı
            "group": group,
            "subtotal": subtotal,
        }
        self.current_components.append(comp)

        # Miktar girişini sıfırla
        self.preview_raw = ""
        self.update()
    


    # --- Kategori ekleme / silme / fiyat düzenleme diyalogları ---

    def add_category_dialog(self, group: str):
        # group: "material" veya "labor"
        dlg = SketchCategoryDialog(self, group=group)
        result = dlg.exec()
        if result != QDialog.DialogCode.Accepted:
            return

        data = dlg.get_values()
        name = (data.get("name") or "").strip()
        unit = (data.get("unit") or "").strip()
        price = float(data.get("price") or 0.0)

        if not name:
            return
        if not unit:
            unit = "m²"
            data["unit"] = unit

        data["price"] = price

        if group == "material":
            # Plaka / fire / döndürme bilgileri de saklanıyor
            self.material_categories.append(data)
            self.active_category = ("material", len(self.material_categories) - 1)
        else:
            # İşçilik için sade kayıt yeterli
            cat = {
                "name": name,
                "unit": unit,
                "price": price,
                "currency": str(data.get("currency", "USD") or "USD"),
            }
            self.labor_categories.append(cat)
            self.labor_profit_percents[name] = float(self.labor_profit_percents.get(name, 25.0))
            self.active_category = ("labor", len(self.labor_categories) - 1)

        self.save_categories_to_json()
        self.update()



    def show_styled_info_message(self, title: str, text: str):
        info_box = QMessageBox(self)
        info_box.setIcon(QMessageBox.Icon.Information)
        info_box.setWindowTitle(title)
        info_box.setText(text)
        info_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        ok_btn = info_box.button(QMessageBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Tamam")
        info_box.setStyleSheet(
            "QMessageBox { background-color: #ffffff; color: #111111; }"
            "QLabel { color: #111111; font-size: 11pt; }"
            "QPushButton {"
            " color: #111111;"
            " background-color: #ececec;"
            " border: 1px solid #5f5f5f;"
            " padding: 6px 16px;"
            " border-radius: 6px;"
            " font-weight: 600;"
            "}"
            "QPushButton:hover { background-color: #e2e2e2; }"
            "QPushButton:pressed { background-color: #d8d8d8; }"
        )
        info_box.exec()

    def remove_category_dialog(self, group: str):
        if self.active_category is None:
            self.show_styled_info_message(
                "Seçim yok",
                "Silmek için önce soldan bir kategori seç.",
            )
            return

        active_group, idx = self.active_category
        if active_group != group:
            self.show_styled_info_message(
                "Yanlış grup",
                "Malzeme silmek için bir malzeme,\n"
                "işçilik silmek için bir işçilik seçmelisin.",
            )
            return

        if group == "material":
            if not (0 <= idx < len(self.material_categories)):
                return
            name = self.material_categories[idx]["name"]
        else:
            if not (0 <= idx < len(self.labor_categories)):
                return
            name = self.labor_categories[idx]["name"]

        # Yeni eskiz tarzı onay penceresi
        dlg = SketchConfirmDialog(
            f"'{name}' kategorisini silmek istediğine emin misin?",
            self
        )
        result = dlg.exec()
        # Onay'a basılmadıysa vazgeç
        if result != QDialog.DialogCode.Accepted:
            return

        # Gerçekten sil
        if group == "material":
            del self.material_categories[idx]
        else:
            removed_name = self.labor_categories[idx].get("name", "")
            del self.labor_categories[idx]
            if removed_name in self.labor_profit_percents:
                del self.labor_profit_percents[removed_name]

        self.active_category = None
        self.save_categories_to_json()
        self.update()

    def edit_price_dialog(self, group: str, idx: int):
        # Önce kategori objesini bul
        if group == "material":
            if not (0 <= idx < len(self.material_categories)):
                return
            cat = self.material_categories[idx]
        else:
            if not (0 <= idx < len(self.labor_categories)):
                return
            cat = self.labor_categories[idx]

        # --- MALZEME: Tam kategori diyalogu ile düzenle ---
        if group == "material":
            old_name = cat.get("name", "")

            dlg = SketchCategoryDialog(self, group="material")
            dlg.setWindowTitle("Malzeme Düzenle")
            dlg.set_initial_values(cat)

            result = dlg.exec()
            if result != QDialog.DialogCode.Accepted:
                return

            new_data = dlg.get_values()
            # Liste içindeki kategoriyi güncelle
            self.material_categories[idx] = new_data
            # JSON'a yaz
            self.save_categories_to_json()
            # Bu malzemeyi kullanan kalemleri fire + yeni fiyata göre güncelle
            self.apply_category_edit_to_lines(old_name, new_data)

        # --- İŞÇİLİK: tam kategori diyalogu ile düzenle (para birimi dahil) ---
        else:
            old_name = cat.get("name", "")
            dlg = SketchCategoryDialog(self, group="labor")
            dlg.setWindowTitle("İşçilik Düzenle")
            dlg.set_initial_values(cat)
            result = dlg.exec()
            if result != QDialog.DialogCode.Accepted:
                return

            new_data = dlg.get_values()
            self.labor_categories[idx] = new_data
            self.save_categories_to_json()
            self.apply_labor_price_edit_to_lines(old_name, new_data)



    def edit_product_name(self):
        dlg = SketchNameDialog(self.current_product_name, self)
        result = dlg.exec()
        if result != QDialog.DialogCode.Accepted:
            return
        new_name = dlg.get_name()
        if not new_name:
            return
        self.current_product_name = new_name
        self.update()

    def build_components_summary(self, comps):
        parts = []
        for c in comps:
            amt = self.format_amount(c["amount"])
            unit = c["unit"]
            price = self.format_amount(c["price"])
            subtotal = self.format_amount(c["subtotal"])
            parts.append(f"{c['name']} ({amt} {unit} x {price} = {subtotal})")
        return "; ".join(parts)


    def write_offer_to_csv(self):
        """exported_items listesini aktif projenin CSV dosyasına yazar."""
        path = self.get_project_csv_path()
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["Ürün Adı", "Toplam Birim Fiyat", "Bileşen Özeti", "Bileşen JSON", "Miktar", "Birim", "Detay"])
                for item in self.exported_items:
                    comp_json = json.dumps(item.get("components", []), ensure_ascii=False)
                    writer.writerow([
                        item["name"],
                        self.format_amount(item["unit_price"]),
                        item.get("components_summary", ""),
                        comp_json,
                        item.get("quantity", ""),
                        item.get("unit", ""),
                        item.get("detail", ""),
                    ])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Dışa aktarma hatası",
                f"{path} yazılırken hata oluştu:\n{e}",
            )
    def write_offer_teklif_csv(self):
        """
        exported_items listesini Excel için detaylı bir CSV'ye yazar.
        Bu dosya, proje .csv'sinden AYRI tutulur (Teklif_<proje>.csv),
        böylece proje tekrar açıldığında eski verilerin yüklenmesi bozulmaz.

        Kolonlar:
        Ürün Adı | Malzeme Toplamı | İşçilik Toplamı |
        Malzeme Adı | Miktar | Birim | Birim Fiyatı | Fire Oranı | Fireli B.Fiyatı |
        + her işçilik için: İşçilik Adı i | İşçilik Miktarı i | İşçilik Birimi i | İşçilik Birim Fiyatı i
        (i = 1..max_işçilik)
        """
        path = self.get_teklif_csv_path()

        try:
            items = self.exported_items or []

            # Bu projede maksimum işçilik sayısını bul
            max_labors = 0
            for item in items:
                comps = item.get("components") or []
                labors = [c for c in comps if c.get("group") == "labor"]
                if len(labors) > max_labors:
                    max_labors = len(labors)

            # CSV için sade sayı formatı (binlik yok, ondalık virgül)
            def _csv_num(value, decimals: int = 2) -> str:
                try:
                    v = float(value)
                except (TypeError, ValueError):
                    v = 0.0
                if decimals < 0:
                    decimals = 0
                fmt = f"{v:.{decimals}f}"      # 1234.50
                return f"{v:.{decimals}f}"    # 1234,50  → TR Excel sayıya çevirir

            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=';')

                # Başlık satırı
                header = [
                    "Ürün Adı",
                    "Malzeme Toplamı",
                    "İşçilik Toplamı",
                    "Malzeme Adı",
                    "Miktar",
                    "Birim",
                    "Birim Fiyatı",
                    "Fire Oranı",
                    "Fireli B.Fiyatı",
                ]

                # İşçilik sütunlarını dinamik ekle (kaç işçilik varsa o kadar)
                for i in range(1, max_labors + 1):
                    header.extend([
                        f"İşçilik Adı {i}",
                        f"İşçilik Miktarı {i}",
                        f"İşçilik Birimi {i}",
                        f"İşçilik Birim Fiyatı {i}",
                    ])

                writer.writerow(header)

                # Tek bir işçilik component'ini 4 hücreye açan helper
                def _labor_fields(c: dict):
                    try:
                        amount = float(c.get("amount", 0.0))
                    except (TypeError, ValueError):
                        amount = 0.0
                    unit = c.get("unit", "") or ""
                    try:
                        unit_price = float(c.get("price", c.get("base_price", 0.0)))
                    except (TypeError, ValueError):
                        unit_price = 0.0
                    return [
                        c.get("name", ""),
                        _csv_num(amount, 3),   # işçilik miktarı (sadece sayı)
                        unit,
                        _csv_num(unit_price, 2),
                    ]

                # Satırları yaz
                for item in items:
                    product_name = item.get("name", "")
                    comps = item.get("components") or []
                    materials = [c for c in comps if c.get("group") == "material"]
                    labors = [c for c in comps if c.get("group") == "labor"]

                    # ÜRÜN bazında toplam malzeme tutarı (amount * fireli birim fiyat)
                    material_total_val = 0.0
                    for m in materials:
                        try:
                            amount = float(m.get("amount", 0.0))
                        except (TypeError, ValueError):
                            amount = 0.0
                        try:
                            eff_price = float(m.get("price", m.get("base_price", 0.0)))
                        except (TypeError, ValueError):
                            eff_price = 0.0
                        material_total_val += amount * eff_price

                    # ÜRÜN bazında toplam işçilik tutarı (amount * birim fiyat)
                    labor_total_val = 0.0
                    for c in labors:
                        try:
                            amount = float(c.get("amount", 0.0))
                        except (TypeError, ValueError):
                            amount = 0.0
                        try:
                            unit_price = float(c.get("price", c.get("base_price", 0.0)))
                        except (TypeError, ValueError):
                            unit_price = 0.0
                        labor_total_val += amount * unit_price

                    material_total_str = _csv_num(material_total_val, 2)
                    labor_total_str    = _csv_num(labor_total_val, 2)

                    # Hiç malzeme yoksa bile ürün satırı tek satır olarak çıksın
                    if not materials:
                        row = [
                            product_name,
                            material_total_str,
                            labor_total_str,
                            "",  # Malzeme Adı
                            "",  # Miktar
                            "",  # Birim
                            "",  # Birim Fiyatı
                            "",  # Fire Oranı
                            "",  # Fireli B.Fiyatı
                        ]
                        # Bu ürün için tüm işçilikleri sırayla doldur
                        for idx in range(max_labors):
                            if idx < len(labors):
                                row.extend(_labor_fields(labors[idx]))
                            else:
                                row.extend(["", "", "", ""])
                        writer.writerow(row)
                        continue

                    # Her malzeme için bir satır
                    for m in materials:
                        try:
                            amount = float(m.get("amount", 0.0))
                        except (TypeError, ValueError):
                            amount = 0.0
                        amt_str = _csv_num(amount, 3)
                        unit = m.get("unit", "") or ""
                        try:
                            base_price = float(m.get("base_price", 0.0))
                        except (TypeError, ValueError):
                            base_price = 0.0
                        try:
                            waste_percent = float(m.get("waste_percent", 0.0))
                        except (TypeError, ValueError):
                            waste_percent = 0.0
                        try:
                            effective_price = float(m.get("price", 0.0))
                        except (TypeError, ValueError):
                            effective_price = 0.0

                        row = [
                            product_name,
                            material_total_str,                 # Ürünün tüm malzeme toplamı
                            labor_total_str,                    # Ürünün tüm işçilik toplamı
                            m.get("name", ""),
                            amt_str,                            # Miktar (sadece rakam)
                            unit,                               # Birim
                            _csv_num(base_price, 2),           # Birim Fiyatı
                            _csv_num(waste_percent, 1),        # Fire Oranı
                            _csv_num(effective_price, 2),      # Fireli B.Fiyatı
                        ]

                        for idx in range(max_labors):
                            if idx < len(labors):
                                row.extend(_labor_fields(labors[idx]))
                            else:
                                row.extend(["", "", "", ""])

                        writer.writerow(row)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Dışa aktarma hatası",
                f"Teklif CSV yazılırken hata oluştu:\\n{e}",
            )
    
    
    

    def effective_material_price_from_category(self, cat: dict) -> tuple[float, float]:
        """
        Malzeme için:
        - tedarikçi birim fiyatını (price)
        - fire yüzdesini (waste_percent)
        kullanarak efektif birim fiyatı hesaplar.
        Döndürdüğü: (effective_price, waste_percent)
        """
        try:
            base_price = float(cat.get("price", 0.0))
        except (TypeError, ValueError):
            base_price = 0.0

        try:
            waste_percent = float(cat.get("waste_percent", 0.0))
        except (TypeError, ValueError):
            waste_percent = 0.0

        if waste_percent < 0:
            waste_percent = 0.0

        # %100 ve üstü saçma → firesiz hesapla
        if waste_percent >= 100.0:
            return base_price, waste_percent

        oran = 1.0 - waste_percent / 100.0
        if oran <= 0:
            return base_price, waste_percent

        effective_price = base_price / oran
        return effective_price, waste_percent


    def compute_component_totals(self):
        """
        Tüm exported_items içinden:
        - malzeme bazında TOPLAM TUTAR + NET MİKTAR + BRÜT MİKTAR + BİRİM
        - işçilik bazında TOPLAM TUTAR
        - işçilik genel toplamı
        hesaplar.
        """
        # malzeme adı -> {"subtotal": para, "amount": net miktar, "gross_amount": fireli miktar, "unit": birim}
        material_stats = {}
        labor_stats = {}
        labor_total = 0.0

        for item in self.exported_items:
            comps = item.get("components") or []
            for c in comps:
                # alt toplam (para)
                try:
                    subtotal = float(c.get("subtotal", 0.0))
                except (TypeError, ValueError):
                    subtotal = 0.0

                group = c.get("group")
                name = c.get("name", "Bilinmeyen")

                if group == "material":
                    entry = material_stats.setdefault(
                        name,
                        {
                            "subtotal": 0.0,
                            "amount": 0.0,
                            "gross_amount": 0.0,
                            "unit": c.get("unit", ""),
                        },
                    )
                    entry["subtotal"] += subtotal

                    # miktar
                    try:
                        amt = float(c.get("amount", 0.0))
                    except (TypeError, ValueError):
                        amt = 0.0
                    entry["amount"] += amt

                    # fire dahil gerçek ihtiyaç miktarı (brüt)
                    try:
                        waste_percent = float(c.get("waste_percent", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        waste_percent = 0.0

                    if waste_percent < 0:
                        waste_percent = 0.0

                    if waste_percent >= 100.0:
                        gross_amt = amt
                    else:
                        ratio = 1.0 - (waste_percent / 100.0)
                        gross_amt = amt / ratio if ratio > 0 else amt

                    entry["gross_amount"] += gross_amt

                elif group == "labor":
                    labor_entry = labor_stats.setdefault(
                        name,
                        {
                            "subtotal": 0.0,
                            "amount": 0.0,
                            "unit": c.get("unit", ""),
                        },
                    )
                    labor_entry["subtotal"] += subtotal
                    try:
                        labor_amt = float(c.get("amount", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        labor_amt = 0.0
                    labor_entry["amount"] += labor_amt
                    labor_total += subtotal

        return material_stats, labor_stats, labor_total



    def export_current_line(self):
        """Merkez balondaki mevcut satırı teklif listesine ekler ve CSV'yi günceller."""
        if not self.current_project_name.strip():
            self.show_styled_info_message(
                "Proje adı yok",
                "Dışa aktarmadan önce üstteki 'Proje Adı' alanına bir isim yazmalısın."
            )
            return

        if self.line_total <= 0 or not self.current_components:
            self.show_styled_info_message(
                "Boş satır",
                "Dışa aktarmak için önce bu satıra en az bir bileşen eklemelisin."
            )
            return

        product_name = self.current_product_name.strip() or "Adsız Ürün"

        # Aynı isimle daha önce ürün aktarıldı mı? -> index bul
        existing_index = None
        for i, item in enumerate(self.exported_items):
            if item["name"] == product_name:
                existing_index = i
                break

        if existing_index is not None:
            dlg = SketchOverwriteDialog(product_name, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

        # Miktar / Birim / Detay diyalogu
        add_dlg = SketchAddProductDialog(product_name, self)
        # Önceki değerleri doldur (varsa)
        if existing_index is not None:
            prev = self.exported_items[existing_index]
            add_dlg._miktar.setText(str(prev.get("quantity", "")))
            add_dlg._birim.setCurrentText(prev.get("unit", "AD"))
            add_dlg._detay.setText(prev.get("detail", ""))
        if add_dlg.exec() != QDialog.DialogCode.Accepted:
            return

        unit_price = self.line_total
        components_summary = self.build_components_summary(self.current_components)
        components_copy = [dict(c) for c in self.current_components]

        new_item = {
            "name": product_name,
            "unit_price": unit_price,
            "components_summary": components_summary,
            "components": components_copy,
            "quantity": add_dlg.get_miktar(),
            "unit": add_dlg.get_birim(),
            "detail": add_dlg.get_detay(),
        }

        if existing_index is not None:
            self.exported_items[existing_index] = new_item
        else:
            self.exported_items.append(new_item)

        # CSV'yi güncelle
        self.write_offer_to_csv()        # proje hafızası
        self.write_offer_teklif_csv()    # Teklif_<proje>.csv

        # Sonra bu satırı sıfırla (fiyat ve bileşenleri)
        self.reset_values()

    def show_exported_items_dialog(self):
        """
        Aktarılan ürünleri listeleyen ve silme / merkeze yükleme imkanı veren pencere.
        Proje CSV'sini de tekrar okuyup exported_items'i garanti tazeliyoruz.
        """
        # Her ihtimale karşı proje CSV'yi yeniden yükle
        if self.current_project_name.strip():
            self.load_project_from_csv()

        if not self.exported_items:
            QMessageBox.information(
                self,
                "Teklif listesi boş",
                "Bu projede henüz dışa aktarılmış ürün yok."
            )
            return

        dlg = SketchExportedItemsDialog(self)
        dlg.exec()

        # Diyalog içinde exported_items değişmiş olabilir (silme vs.)
        self.write_offer_to_csv()
        self.write_offer_teklif_csv()
        self.update()
    


    def slugify_project_name(self, name: str) -> str:
        """Proje adını dosya adı için sadeleştir (boşluk -> alt çizgi, problemli karakterleri at)."""
        name = name.strip()
        if not name:
            return "teklif"
        bad_chars = '<>:"/\\|?*'
        cleaned = "".join(c for c in name if c not in bad_chars)
        cleaned = cleaned.replace(" ", "_")
        return cleaned or "teklif"

    def slugify(self, text: str) -> str:
        """
        Proje adını dosya adı olarak güvenli hale getir.
        Türkçe karakterlere dokunmuyoruz, sadece boşlukları '_' yapıp
        Windows için sorunlu karakterleri temizliyoruz.
        """
        text = (text or "").strip()
        if not text:
            return "Adsiz_Proje"

        # Windows'ta yasak karakterler
        invalid = '<>:"/\\|?*'

        out_chars = []
        for ch in text:
            if ch in invalid:
                out_chars.append("_")
            elif ch.isspace():
                out_chars.append("_")
            else:
                out_chars.append(ch)

        safe = "".join(out_chars)
        return safe or "Adsiz_Proje"

    def _project_folder_name(self, name: str) -> str:
        """Klasör adı: boşluklar korunur, sadece OS yasak karakterler '_' olur."""
        invalid = set('<>:"/\\|?*')
        cleaned = "".join('_' if c in invalid else c for c in (name or "Adsiz_Proje").strip())
        return cleaned or "Adsiz_Proje"

    def get_project_dir(self) -> str:
        """Teklifler/<proje_adı>/ klasörünü oluşturur ve yolunu döner."""
        name = (getattr(self, 'current_project_name', None) or "Adsiz_Proje").strip()
        folder = self._project_folder_name(name)
        path = os.path.join(get_app_base_dir(), "Teklifler", folder)
        os.makedirs(path, exist_ok=True)
        return path

    def get_project_csv_path(self):
        return os.path.join(self.get_project_dir(), "proje.csv")

    def get_teklif_csv_path(self):
        return os.path.join(self.get_project_dir(), "teklif.csv")



    def _migrate_old_project_files(self, name: str):
        """
        Kök klasördeki eski format dosyaları Teklifler/<ad>/ altına taşır.
        Eski format: <ad>.csv, kategoriler_<ad>.json, Teklif_<ad>.csv, teklif_info_<ad>.json
        Paylaşılan dosyalar (firma_bilgileri, firma_logo): sadece kopyalanır.
        """
        import shutil
        base = get_app_base_dir()
        proj_dir = os.path.join(base, "Teklifler", self._project_folder_name(name))
        os.makedirs(proj_dir, exist_ok=True)

        # (kaynak, hedef, taşı_mı?)
        migrations = [
            (os.path.join(base, f"{name}.csv"),               os.path.join(proj_dir, "proje.csv"),            True),
            (os.path.join(base, f"kategoriler_{name}.json"),  os.path.join(proj_dir, "kategoriler.json"),     True),
            (os.path.join(base, f"Teklif_{name}.csv"),        os.path.join(proj_dir, "teklif.csv"),           True),
            (os.path.join(base, f"teklif_info_{name}.json"),  os.path.join(proj_dir, "teklif_info.json"),     True),
            (os.path.join(base, "firma_bilgileri.json"),       os.path.join(proj_dir, "firma_bilgileri.json"), False),
            (os.path.join(base, "firma_logo.png"),             os.path.join(proj_dir, "firma_logo.png"),       False),
        ]

        for src, dst, move in migrations:
            if not os.path.exists(src):
                continue
            if os.path.exists(dst):
                continue  # hedefe zaten var, üzerine yazma
            try:
                if move:
                    shutil.move(src, dst)
                else:
                    shutil.copy2(src, dst)
            except Exception as e:
                print(f"Taşıma/kopyalama hatası: {src} → {dst}: {e}")

    def set_project_name(self, new_name: str):
        # Proje adını temizle
        new_name = (new_name or "").strip()
        if not new_name:
            new_name = "Adsız Proje"

        self.current_project_name = new_name

        # Eski format dosyaları Teklifler/ altına otomatik taşı
        self._migrate_old_project_files(new_name)

        # 1) Bu proje için daha önce kaydedilmiş kategoriler varsa yükle
        self.load_categories_from_json()

        # 2) Bu projeye ait CSV teklif satırlarını da geri yükle
        self.load_project_from_csv()

        # Standart açılış para birimi USD olsun
        self.offer_currency = "USD"
        self.recalculate_all_prices_for_offer_currency()

        # Proje adı balonunu vs. ekranda güncelle
        self.update()


    def _normalize_component_currency(self, comp: dict):
        if not isinstance(comp, dict):
            return

        curr = str(comp.get("currency", "") or "").upper().strip()
        if curr not in ("TL", "USD", "EUR"):
            curr = self.offer_currency
            comp["currency"] = curr

        try:
            price_val = float(comp.get("price", 0.0) or 0.0)
        except (TypeError, ValueError):
            price_val = 0.0
            comp["price"] = 0.0

        if "base_price" not in comp:
            comp["base_price"] = price_val

        try:
            comp["base_price"] = float(comp.get("base_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            comp["base_price"] = price_val

    def load_project_from_csv(self):
        self.exported_items = []
        path = self.get_project_csv_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f, delimiter=';')
                header_read = False
                for row in reader:
                    if not header_read:
                        header_read = True
                        continue
                    if len(row) < 3:
                        continue

                    name = row[0]
                    price_text = row[1]
                    comps_summary = row[2]

                    # Toplam fiyatı parse et
                    txt = price_text.replace(".", "").replace(",", ".").strip()
                    try:
                        unit_price = float(txt) if txt else 0.0
                    except ValueError:
                        unit_price = 0.0

                    # Bileşen JSON'u varsa al
                    components = []
                    if len(row) >= 4 and row[3].strip():
                        try:
                            components = json.loads(row[3])
                        except Exception:
                            components = []

                    if isinstance(components, list):
                        for comp in components:
                            self._normalize_component_currency(comp)

                    # Miktar / Birim / Detay (yeni alanlar, geriye dönük uyumlu)
                    quantity = 0.0
                    if len(row) >= 5 and row[4].strip():
                        try:
                            quantity = float(row[4].replace(",", "."))
                        except ValueError:
                            quantity = 0.0
                    unit = row[5].strip() if len(row) >= 6 else ""
                    detail = row[6].strip() if len(row) >= 7 else ""

                    self.exported_items.append({
                        "name": name,
                        "unit_price": unit_price,
                        "components_summary": comps_summary,
                        "components": components,
                        "quantity": quantity,
                        "unit": unit,
                        "detail": detail,
                    })

            self.recalculate_all_prices_for_offer_currency()
        except Exception as e:
            QMessageBox.warning(
                self,
                "CSV okuma hatası",
                f"Proje dosyası okunurken hata oluştu:\n{e}",
            )


    def _build_project_report_lines(self) -> list[str]:
        """Geriye dönük uyumluluk için basit metin raporu döndürür."""
        material_stats, labor_stats, labor_total = self.compute_component_totals()

        material_total = 0.0
        for stat in material_stats.values():
            try:
                material_total += float(stat.get("subtotal", 0.0) or 0.0)
            except (TypeError, ValueError):
                pass

        material_markup = max(0.0, float(self.material_profit_percent))
        material_with_profit = material_total * (1.0 + material_markup / 100.0)

        labor_with_profit_total = 0.0
        for labor_name, stat in labor_stats.items():
            labor_subtotal = float(stat.get("subtotal", 0.0) or 0.0)
            labor_markup = max(0.0, float(self.labor_profit_percents.get(labor_name, 25.0)))
            labor_with_profit_total += labor_subtotal * (1.0 + labor_markup / 100.0)

        final_offer_total = material_with_profit + labor_with_profit_total
        base_total = material_total + labor_total
        total_profit = final_offer_total - base_total

        report_currency = (self.offer_currency or "USD").upper()

        def fmt_money(value: float) -> str:
            return f"{self.format_amount(value)} {report_currency}"

        lines: list[str] = [
            "TENSHOOT PROJE RAPORU",
            f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            f"Proje: {self.current_project_name.strip() or '-'}",
            "",
            f"Aktarılan ürün sayısı: {len(self.exported_items)}",
            f"Maliyet toplamı: {self.format_amount(base_total)}",
            f"Toplam elde edilecek kâr: {self.format_amount(total_profit)}",
            f"Teklif (kârlı): {self.format_amount(final_offer_total)}",
        ]
        return lines

    def _get_teklif_save_path(self, filename: str) -> str:
        """Proje klasörü altında varsayılan kayıt yolunu döner."""
        return os.path.join(self.get_project_dir(), filename)

    def export_project_report_pdf(self):
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Detaylı Raporu PDF Kaydet",
            self._get_teklif_save_path("proje_raporu.pdf"),
            "PDF Files (*.pdf)",
        )
        if not out_path:
            return

        if not out_path.lower().endswith(".pdf"):
            out_path += ".pdf"

        material_stats, labor_stats, labor_total = self.compute_component_totals()

        material_total = 0.0
        for stat in material_stats.values():
            try:
                material_total += float(stat.get("subtotal", 0.0) or 0.0)
            except (TypeError, ValueError):
                pass

        material_markup = max(0.0, float(self.material_profit_percent))
        material_with_profit = material_total * (1.0 + material_markup / 100.0)

        labor_with_profit_total = 0.0
        labor_rows = []
        for labor_name in sorted(labor_stats.keys()):
            labor_subtotal = float(labor_stats[labor_name].get("subtotal", 0.0) or 0.0)
            labor_markup = max(0.0, float(self.labor_profit_percents.get(labor_name, 25.0)))
            labor_with_profit = labor_subtotal * (1.0 + labor_markup / 100.0)
            labor_with_profit_total += labor_with_profit
            labor_rows.append((labor_name, labor_markup, labor_with_profit))

        final_offer_total = material_with_profit + labor_with_profit_total
        base_total = material_total + labor_total
        total_profit = final_offer_total - base_total

        report_currency = (self.offer_currency or "USD").upper()

        def fmt_money(value: float) -> str:
            return f"{self.format_amount(value)} {report_currency}"

        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setResolution(144)
        printer.setOutputFileName(out_path)

        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.warning(self, "Rapor", "PDF oluşturulamadı.")
            return

        if sys.platform == "darwin":
            pdf_font_family = "Helvetica Neue"
            pdf_font_size = 11
            pdf_title_size = 17
            pdf_line_extra = 3
        else:
            pdf_font_family = "Arial"
            pdf_font_size = 10
            pdf_title_size = 16
            pdf_line_extra = 0

        normal_font = QFont(pdf_font_family, pdf_font_size)
        bold_font = QFont(pdf_font_family, pdf_font_size)
        bold_font.setBold(True)
        title_font = QFont(pdf_font_family, pdf_title_size)
        title_font.setBold(True)

        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        left = page_rect.left() + 42
        right = page_rect.right() - 42
        top = page_rect.top() + 34
        bottom = page_rect.bottom() - 34
        width = right - left

        y = top

        def ensure_space(height_needed: float):
            nonlocal y
            if y + height_needed <= bottom:
                return
            printer.newPage()
            y = top

        def draw_section_title(text: str):
            nonlocal y
            painter.setFont(bold_font)
            fm = QFontMetricsF(bold_font)
            h = fm.height() + 8 + pdf_line_extra
            ensure_space(h + 8)
            painter.setPen(QColor(25, 25, 25))
            painter.drawText(QRectF(left, y, width, h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
            y += h

        def draw_info_row(label: str, value: str):
            nonlocal y
            painter.setFont(normal_font)
            fm = QFontMetricsF(normal_font)
            h = fm.height() + 6 + pdf_line_extra
            ensure_space(h)
            painter.setPen(QColor(45, 45, 45))
            painter.drawText(QRectF(left + 6, y, width * 0.48, h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), label)
            painter.drawText(QRectF(left + width * 0.5, y, width * 0.48, h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), value)
            y += h

        def draw_box(top_y: float, box_h: float):
            painter.setPen(QPen(QColor(70, 70, 70), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(left, top_y, width, box_h))

        painter.setFont(title_font)
        title_h = QFontMetricsF(title_font).height() + 4 + pdf_line_extra
        painter.setPen(QColor(20, 20, 20))
        painter.drawText(QRectF(left, y, width, title_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "Tenshoot Proje Analiz Raporu")
        y += title_h + 2

        painter.setFont(normal_font)
        meta_h = QFontMetricsF(normal_font).height() + 4 + pdf_line_extra
        painter.setPen(QColor(60, 60, 60))
        painter.drawText(QRectF(left, y, width, meta_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        y += meta_h
        painter.drawText(QRectF(left, y, width, meta_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), f"Proje: {self.current_project_name.strip() or '-'}")
        y += meta_h
        painter.drawText(QRectF(left, y, width, meta_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), f"Bu rapordaki fiyatlar {report_currency} para birimindedir.")
        y += meta_h + 8

        # --- BİRİM FİYATLAR ---
        bp_row_h = QFontMetricsF(normal_font).height() + 6 + pdf_line_extra
        header_h = bp_row_h

        # Malzeme kategorileri birim fiyatları
        draw_section_title("MALZEME KATEGORİLERİ BİRİM FİYATLARI")
        mat_cols = [width * 0.38, width * 0.10, width * 0.22, width * 0.20, width * 0.10]
        mat_headers = ["Malzeme Adı", "Birim", "Orijinal Fiyat", f"Teklif ({report_currency})", "Fire %"]
        mat_rows_count = max(1, len(self.material_categories))
        mat_table_h = header_h * (mat_rows_count + 1) + 8
        ensure_space(mat_table_h + 10)
        mat_top = y
        draw_box(mat_top, mat_table_h)
        # dikey çizgiler
        cx0 = left
        for cw in mat_cols[:-1]:
            cx0 += cw
            painter.drawLine(int(cx0), int(mat_top), int(cx0), int(mat_top + mat_table_h))
        # başlık satırı
        painter.setFont(bold_font)
        painter.fillRect(QRectF(left, mat_top, width, header_h + 2), QColor(230, 230, 230))
        cx0 = left
        for i, hdr in enumerate(mat_headers):
            align = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) if i == 0 else int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            painter.drawText(QRectF(cx0 + 4, mat_top + 2, mat_cols[i] - 8, header_h), align, hdr)
            cx0 += mat_cols[i]
        painter.drawLine(int(left), int(mat_top + header_h + 2), int(right), int(mat_top + header_h + 2))
        # veri satırları
        painter.setFont(normal_font)
        yy = mat_top + header_h + 4
        for cat in (self.material_categories or [{"name": "(Malzeme yok)", "unit": "", "price": 0.0, "waste_percent": 0.0, "currency": "TL"}]):
            try:
                price = float(cat.get("price", 0.0))
            except (TypeError, ValueError):
                price = 0.0
            try:
                waste = float(cat.get("waste_percent", 0.0))
            except (TypeError, ValueError):
                waste = 0.0
            cat_currency = str(cat.get("currency", "TL") or "TL").upper()
            converted_price = self.convert_currency(price, cat_currency, report_currency)
            orig_str = f"{price:,.2f} {cat_currency}"
            conv_str = f"{converted_price:,.2f} {report_currency}" if cat_currency != report_currency else "-"
            vals = [cat.get("name", ""), cat.get("unit", ""), orig_str, conv_str, f"{waste:.1f}%"]
            cx0 = left
            for i, val in enumerate(vals):
                align = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) if i == 0 else int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                painter.drawText(QRectF(cx0 + 4, yy, mat_cols[i] - 8, bp_row_h), align, val)
                cx0 += mat_cols[i]
            yy += bp_row_h
            painter.drawLine(int(left), int(yy), int(right), int(yy))
        y = mat_top + mat_table_h + 10

        # İşçilik kategorileri birim fiyatları
        draw_section_title("İŞÇİLİK KATEGORİLERİ BİRİM FİYATLARI")
        lab_cols = [width * 0.42, width * 0.10, width * 0.24, width * 0.24]
        lab_headers = ["İşçilik Adı", "Birim", "Orijinal Fiyat", f"Teklif ({report_currency})"]
        lab_rows_count = max(1, len(self.labor_categories))
        lab_table_h = header_h * (lab_rows_count + 1) + 8
        ensure_space(lab_table_h + 10)
        lab_top = y
        draw_box(lab_top, lab_table_h)
        cx0 = left
        for cw in lab_cols[:-1]:
            cx0 += cw
            painter.drawLine(int(cx0), int(lab_top), int(cx0), int(lab_top + lab_table_h))
        painter.setFont(bold_font)
        painter.fillRect(QRectF(left, lab_top, width, header_h + 2), QColor(230, 230, 230))
        cx0 = left
        for i, hdr in enumerate(lab_headers):
            align = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) if i == 0 else int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            painter.drawText(QRectF(cx0 + 4, lab_top + 2, lab_cols[i] - 8, header_h), align, hdr)
            cx0 += lab_cols[i]
        painter.drawLine(int(left), int(lab_top + header_h + 2), int(right), int(lab_top + header_h + 2))
        painter.setFont(normal_font)
        yy = lab_top + header_h + 4
        for cat in (self.labor_categories or [{"name": "(İşçilik yok)", "unit": "", "price": 0.0, "currency": "TL"}]):
            try:
                price = float(cat.get("price", 0.0))
            except (TypeError, ValueError):
                price = 0.0
            cat_currency = str(cat.get("currency", "TL") or "TL").upper()
            converted_price = self.convert_currency(price, cat_currency, report_currency)
            orig_str = f"{price:,.2f} {cat_currency}"
            conv_str = f"{converted_price:,.2f} {report_currency}" if cat_currency != report_currency else "-"
            vals = [cat.get("name", ""), cat.get("unit", ""), orig_str, conv_str]
            cx0 = left
            for i, val in enumerate(vals):
                align = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) if i == 0 else int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                painter.drawText(QRectF(cx0 + 4, yy, lab_cols[i] - 8, bp_row_h), align, val)
                cx0 += lab_cols[i]
            yy += bp_row_h
            painter.drawLine(int(left), int(yy), int(right), int(yy))
        y = lab_top + lab_table_h + 10

        section_top = y
        draw_section_title("GENEL TOPLAMLAR")
        draw_info_row("Aktarılan ürün sayısı", f"{len(self.exported_items)}")
        draw_info_row("Maliyet toplamı", fmt_money(base_total))
        draw_info_row("Toplam elde edilecek kâr", fmt_money(total_profit))
        draw_info_row("Teklif (kârlı)", fmt_money(final_offer_total))
        draw_box(section_top, y - section_top + 4)
        y += 10

        draw_section_title("MALZEMELERİN FİRELİ TOPLAM MİKTARI")
        row_h = QFontMetricsF(normal_font).height() + 6 + pdf_line_extra
        material_row_count = max(1, len(material_stats))
        table_h = row_h * (material_row_count + 1) + 8
        ensure_space(table_h + 10)
        table_top = y
        draw_box(table_top, table_h)
        c1 = left + width * 0.45
        c2 = left + width * 0.72
        painter.drawLine(int(c1), int(table_top), int(c1), int(table_top + table_h))
        painter.drawLine(int(c2), int(table_top), int(c2), int(table_top + table_h))

        painter.setFont(bold_font)
        painter.drawText(QRectF(left + 6, table_top + 2, c1 - left - 12, row_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "Malzeme")
        painter.drawText(QRectF(c1 + 6, table_top + 2, c2 - c1 - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "Fireli Miktar")
        painter.drawText(QRectF(c2 + 6, table_top + 2, right - c2 - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), f"Toplam Fiyat ({report_currency})")
        painter.drawLine(int(left), int(table_top + row_h + 2), int(right), int(table_top + row_h + 2))

        painter.setFont(normal_font)
        yy = table_top + row_h + 4
        for name in sorted(material_stats.keys()):
            stat = material_stats[name]
            gross_amount = float(stat.get("gross_amount", 0.0) or 0.0)
            unit = (stat.get("unit", "") or "").strip()
            amount_text = f"{self.format_amount(gross_amount)} {unit}".strip()
            total_text = fmt_money(float(stat.get("subtotal", 0.0) or 0.0))
            painter.drawText(QRectF(left + 6, yy, c1 - left - 12, row_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), name)
            painter.drawText(QRectF(c1 + 6, yy, c2 - c1 - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), amount_text)
            painter.drawText(QRectF(c2 + 6, yy, right - c2 - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), total_text)
            yy += row_h
            painter.drawLine(int(left), int(yy), int(right), int(yy))
        if not material_stats:
            painter.drawText(QRectF(left + 6, yy, c1 - left - 12, row_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "(Malzeme kaydı yok)")
            painter.drawText(QRectF(c1 + 6, yy, c2 - c1 - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "-")
            painter.drawText(QRectF(c2 + 6, yy, right - c2 - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "-")
            yy += row_h
            painter.drawLine(int(left), int(yy), int(right), int(yy))
        y = table_top + table_h + 10

        draw_section_title("İŞÇİLİK MİKTAR TOPLAMLARI")
        labor_amount_rows = []
        for name in sorted(labor_stats.keys()):
            stat = labor_stats[name]
            amount_val = float(stat.get("amount", 0.0) or 0.0)
            unit = (stat.get("unit", "") or "").strip()
            labor_amount_rows.append((name, f"{self.format_amount(amount_val)} {unit}".strip()))
        if not labor_amount_rows:
            labor_amount_rows.append(("(İşçilik kaydı yok)", "-"))

        labor_table_h = row_h * (len(labor_amount_rows) + 1) + 8
        ensure_space(labor_table_h + 10)
        labor_top = y
        draw_box(labor_top, labor_table_h)
        labor_split_x = left + width * 0.68
        painter.drawLine(int(labor_split_x), int(labor_top), int(labor_split_x), int(labor_top + labor_table_h))

        painter.setFont(bold_font)
        painter.drawText(QRectF(left + 6, labor_top + 2, labor_split_x - left - 12, row_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "İşçilik")
        painter.drawText(QRectF(labor_split_x + 6, labor_top + 2, right - labor_split_x - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "Toplam Miktar")
        painter.drawLine(int(left), int(labor_top + row_h + 2), int(right), int(labor_top + row_h + 2))

        painter.setFont(normal_font)
        yy = labor_top + row_h + 4
        for name, amount_text in labor_amount_rows:
            painter.drawText(QRectF(left + 6, yy, labor_split_x - left - 12, row_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), name)
            painter.drawText(QRectF(labor_split_x + 6, yy, right - labor_split_x - 12, row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), amount_text)
            yy += row_h
            painter.drawLine(int(left), int(yy), int(right), int(yy))
        y = labor_top + labor_table_h + 10

        draw_section_title("KÂR SİMÜLASYONU")
        sim_rows = [("Malzeme", material_markup, material_with_profit)] + labor_rows
        sim_rows.append(("Yeni Teklif Toplamı", None, final_offer_total))

        sim_row_h = row_h
        sim_h = sim_row_h * (len(sim_rows) + 1) + 8
        ensure_space(sim_h + 10)
        sim_top = y
        draw_box(sim_top, sim_h)

        c1 = left + width * 0.52
        c2 = left + width * 0.73
        painter.drawLine(int(c1), int(sim_top), int(c1), int(sim_top + sim_h))
        painter.drawLine(int(c2), int(sim_top), int(c2), int(sim_top + sim_h))

        painter.setFont(bold_font)
        painter.drawText(QRectF(left + 6, sim_top + 2, c1 - left - 12, sim_row_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), "Kalem")
        painter.drawText(QRectF(c1 + 6, sim_top + 2, c2 - c1 - 12, sim_row_h), int(Qt.AlignmentFlag.AlignCenter), "Kâr %")
        painter.drawText(QRectF(c2 + 6, sim_top + 2, right - c2 - 12, sim_row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), f"Toplam ({report_currency})")
        painter.drawLine(int(left), int(sim_top + sim_row_h + 2), int(right), int(sim_top + sim_row_h + 2))

        painter.setFont(normal_font)
        yy = sim_top + sim_row_h + 4
        for name, markup, total in sim_rows:
            markup_text = "-" if markup is None else self.format_amount(markup)
            painter.drawText(QRectF(left + 6, yy, c1 - left - 12, sim_row_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), name)
            painter.drawText(QRectF(c1 + 6, yy, c2 - c1 - 12, sim_row_h), int(Qt.AlignmentFlag.AlignCenter), markup_text)
            painter.drawText(QRectF(c2 + 6, yy, right - c2 - 12, sim_row_h), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), fmt_money(total))
            yy += sim_row_h
            painter.drawLine(int(left), int(yy), int(right), int(yy))
        y = sim_top + sim_h + 10

        draw_section_title("AKTARILAN ÜRÜNLER")
        if not self.exported_items:
            draw_info_row("Durum", "Henüz aktarılmış ürün yok")
        else:
            for idx, item in enumerate(self.exported_items, start=1):
                item_h = QFontMetricsF(bold_font).height() + 6 + pdf_line_extra
                info_h = QFontMetricsF(normal_font).height() + 4 + pdf_line_extra
                ensure_space(item_h + (info_h * 2) + 10)

                painter.setFont(bold_font)
                painter.setPen(QColor(35, 35, 35))
                item_name = item.get("name", "")

                base_item_total = float(item.get("unit_price", 0.0) or 0.0)
                item_profit_total = 0.0
                for comp in (item.get("components") or []):
                    comp_subtotal = float(comp.get("subtotal", 0.0) or 0.0)
                    comp_group = comp.get("group")
                    if comp_group == "material":
                        item_profit_total += comp_subtotal * (1.0 + material_markup / 100.0)
                    elif comp_group == "labor":
                        labor_name = comp.get("name", "")
                        labor_markup = max(0.0, float(self.labor_profit_percents.get(labor_name, 25.0)))
                        item_profit_total += comp_subtotal * (1.0 + labor_markup / 100.0)
                    else:
                        item_profit_total += comp_subtotal

                if item_profit_total <= 0:
                    item_profit_total = base_item_total

                net_profit = item_profit_total - base_item_total
                net_profit_pct = (net_profit / base_item_total * 100.0) if base_item_total > 0 else 0.0

                painter.drawText(QRectF(left + 4, y, width * 0.62, item_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), f"{idx}. {item_name}")
                y += item_h

                info_rect = QRectF(left + width * 0.38, y, width * 0.60, info_h)

                painter.setFont(bold_font)
                painter.setPen(QColor(30, 30, 30))
                painter.drawText(
                    info_rect,
                    int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                    f"Toplam Maliyet: {fmt_money(base_item_total)}",
                )
                y += info_h

                info_rect2 = QRectF(left + width * 0.30, y, width * 0.68, info_h)
                painter.setFont(bold_font)
                painter.setPen(QColor(0, 70, 160))
                painter.drawText(
                    info_rect2,
                    int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                    f"Toplam Kârlı Fiyat: {fmt_money(item_profit_total)} | Net Kâr: %{self.format_amount(net_profit_pct)}",
                )
                y += info_h

                comps = item.get("components") or []
                comp_h = QFontMetricsF(normal_font).height() + 4 + pdf_line_extra
                for comp in comps:
                    ensure_space(comp_h)
                    cname = comp.get("name", "")
                    amt = float(comp.get("amount", 0.0) or 0.0)
                    unit = comp.get("unit", "")
                    sub = float(comp.get("subtotal", 0.0) or 0.0)
                    line = f"- {cname} | {self.format_amount(amt)} {unit} | {fmt_money(sub)}"
                    painter.drawText(QRectF(left + 18, y, width - 22, comp_h), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), line)
                    y += comp_h

                y += 4
                painter.drawLine(int(left + 4), int(y), int(right - 4), int(y))
                y += 8

        painter.end()

        dlg = QDialog(self)
        dlg.setWindowTitle("Rapor")
        dlg.setModal(True)
        dlg.setStyleSheet(
            "QDialog { background-color: #ffffff; color: #111111; }"
            "QLabel { color: #111111; font-size: 11pt; }"
        )

        icon_label = QLabel("✅")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        text_label = QLabel(f"PDF rapor kaydedildi:\n{out_path}")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        ok_btn = QPushButton("Tamam")
        ok_btn.setObjectName("reportOkButton")
        ok_btn.setMinimumWidth(120)
        ok_btn.setStyleSheet(
            "QPushButton#reportOkButton {"
            " color: #111111;"
            " background-color: #ececec;"
            " border: 1px solid #5f5f5f;"
            " padding: 6px 16px;"
            " border-radius: 6px;"
            " font-weight: 600;"
            "}"
            "QPushButton#reportOkButton:hover { background-color: #e2e2e2; }"
            "QPushButton#reportOkButton:pressed { background-color: #d8d8d8; }"
        )
        ok_palette = ok_btn.palette()
        ok_palette.setColor(ok_btn.foregroundRole(), QColor("#111111"))
        ok_palette.setColor(ok_btn.backgroundRole(), QColor("#ececec"))
        ok_btn.setPalette(ok_palette)
        ok_btn.clicked.connect(dlg.accept)

        top_layout = QHBoxLayout()
        top_layout.addWidget(icon_label)
        top_layout.addWidget(text_label, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)

        layout = QVBoxLayout(dlg)
        layout.addLayout(top_layout)
        layout.addSpacing(8)
        layout.addLayout(btn_layout)

        dlg.resize(520, 180)
        dlg.exec()


    def _get_teklif_info_path(self) -> str:
        return os.path.join(self.get_project_dir(), "teklif_info.json")

    def _load_teklif_info(self) -> dict:
        path = self._get_teklif_info_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_teklif_info(self, info: dict):
        path = self._get_teklif_info_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _get_firma_bilgileri_path(self) -> str:
        return os.path.join(self.get_project_dir(), "firma_bilgileri.json")

    def _get_firma_logo_path(self) -> str:
        return os.path.join(self.get_project_dir(), "firma_logo.png")

    def _load_firma_bilgileri(self) -> dict:
        path = self._get_firma_bilgileri_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_firma_bilgileri(self, info: dict):
        path = self._get_firma_bilgileri_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _ask_teklif_format(self):
        """Önce müşteri bilgilerini toplar, sonra format seçtiren dialog."""
        # ── Adım 1: Firma bilgileri (sıralı, iç içe modal yok — macOS uyumlu) ──
        fb = self._load_firma_bilgileri()
        lp = self._get_firma_logo_path()
        firma_dlg = SketchFirmaBilgileriDialog(self, prefill=fb, logo_path=lp)
        if firma_dlg.exec() == QDialog.DialogCode.Accepted:
            self._save_firma_bilgileri(firma_dlg.get_info())
            firma_dlg.save_logo_to_disk()
        # Kayıtlı (veya yeni kaydedilen) firma bilgilerini yükle
        firma_info     = self._load_firma_bilgileri()
        firma_logo_path = self._get_firma_logo_path()

        # ── Adım 2: Müşteri / teklif bilgileri ──
        saved = self._load_teklif_info()
        info_dlg = SketchTeklifInfoDialog(
            self.current_project_name.strip() or "",
            (self.offer_currency or "USD").upper(),
            prefill=saved,
            parent=self,
        )
        if info_dlg.exec() != QDialog.DialogCode.Accepted:
            return
        teklif_info = info_dlg.get_info()
        self._save_teklif_info(teklif_info)

        # 2. Format seçimi
        fmt_dlg = QDialog(self)
        fmt_dlg.setWindowTitle("Teklif Formatı")
        fmt_dlg.setModal(True)
        fmt_dlg.setStyleSheet("""
            QDialog { background-color: white; }
            QLabel { font-size: 12pt; color: #222; }
            QPushButton {
                font-size: 11pt; padding: 10px 20px;
                border: 2px solid #444; border-radius: 14px;
                background-color: white; color: #222;
            }
            QPushButton#excelBtn  { color: #006600; border-color: #006600; }
            QPushButton#pdfBtn    { color: #003399; border-color: #003399; }
            QPushButton#pdfSimBtn { color: #884400; border-color: #884400; }
            QPushButton:hover { background-color: #f0f0f0; }
        """)
        lbl = QLabel("Teklifi hangi formatta almak istiyorsunuz?")

        pdf_btn     = QPushButton("PDF — Detaylı\n(Malzeme + İşçilik breakdown)")
        pdf_btn.setObjectName("pdfBtn")
        pdf_sim_btn = QPushButton("PDF — Özet\n(Ürün Adı, Detay, Miktar, Birim Fiyat)")
        pdf_sim_btn.setObjectName("pdfSimBtn")
        excel_btn   = QPushButton("Excel (.csv)")
        excel_btn.setObjectName("excelBtn")

        pdf_btn.clicked.connect(lambda: (fmt_dlg.accept(),
            self.export_offer_teklif_pdf(teklif_info, firma_info, firma_logo_path)))
        pdf_sim_btn.clicked.connect(lambda: (fmt_dlg.accept(),
            self.export_offer_teklif_pdf_simple(teklif_info, firma_info, firma_logo_path)))
        excel_btn.clicked.connect(lambda: (fmt_dlg.accept(), self.export_offer_teklif_excel()))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(pdf_btn)
        btn_row.addWidget(pdf_sim_btn)
        btn_row.addWidget(excel_btn)
        btn_row.addStretch()

        layout = QVBoxLayout(fmt_dlg)
        layout.addWidget(lbl)
        layout.addSpacing(12)
        layout.addLayout(btn_row)
        fmt_dlg.resize(560, 130)
        fmt_dlg.exec()

    def export_offer_teklif_excel(self):
        """Teklif tablosunu Excel-uyumlu CSV olarak üretir (ek kütüphane gerekmez)."""
        if self.current_project_name.strip():
            self.load_project_from_csv()
        if not self.exported_items:
            QMessageBox.information(self, "Teklif", "Önce ürün ekleyiniz.")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Excel olarak kaydet", self._get_teklif_save_path("teklif.csv"), "CSV - Excel (*.csv)"
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".csv"):
            out_path += ".csv"

        report_currency = (self.offer_currency or "USD").upper()
        material_markup = max(0.0, float(self.material_profit_percent))

        def item_totals(item):
            mat_total = lab_total = 0.0
            for c in (item.get("components") or []):
                try:
                    sub = float(c.get("subtotal", 0.0) or 0.0)
                except (TypeError, ValueError):
                    sub = 0.0
                if c.get("group") == "material":
                    mat_total += sub
                elif c.get("group") == "labor":
                    lab_total += sub
            mat_profit = mat_total * (1.0 + material_markup / 100.0)
            lab_profit = 0.0
            for c in (item.get("components") or []):
                if c.get("group") != "labor":
                    continue
                try:
                    sub = float(c.get("subtotal", 0.0) or 0.0)
                except (TypeError, ValueError):
                    sub = 0.0
                lm = max(0.0, float(self.labor_profit_percents.get(c.get("name", ""), 25.0)))
                lab_profit += sub * (1.0 + lm / 100.0)
            return mat_total, lab_total, mat_total + lab_total, mat_profit + lab_profit

        def n(v):
            """Sayıyı Excel'in sayı olarak tanıyacağı formatta yaz (ondalık nokta)."""
            return f"{v:.2f}"

        try:
            with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")

                # Başlık satırları
                w.writerow(["Tenshoot Proje Analiz Raporu"])
                w.writerow([
                    f"Proje: {self.current_project_name.strip() or '-'}",
                    f"Tarih: {datetime.now().strftime('%d.%m.%Y')}",
                    f"Para Birimi: {report_currency}",
                ])
                w.writerow([])

                # Sütun başlıkları
                w.writerow([
                    "Ürün Adı", "Detay", "Miktar", "Birim",
                    f"Malzeme ({report_currency})",
                    f"İşçilik ({report_currency})",
                    "Toplam Maliyet",
                    "Karlı Toplam",
                    "Birim Fiyat",
                ])

                grand_mat = grand_lab = grand_tot = grand_karli = 0.0
                for item in self.exported_items:
                    mat, lab, tot, karli = item_totals(item)
                    grand_mat   += mat
                    grand_lab   += lab
                    grand_tot   += tot
                    grand_karli += karli
                    try:
                        qty = float(item.get("quantity") or 0.0)
                    except (TypeError, ValueError):
                        qty = 0.0
                    birim_fiyat = karli / qty if qty > 0 else 0.0
                    w.writerow([
                        item.get("name", ""),
                        item.get("detail", ""),
                        n(qty) if qty else "",
                        item.get("unit", ""),
                        n(mat), n(lab), n(tot), n(karli), n(birim_fiyat),
                    ])

                # Toplam satırı
                w.writerow([
                    "TOPLAM", "", "", "",
                    n(grand_mat), n(grand_lab), n(grand_tot), n(grand_karli), "",
                ])

            self.show_styled_info_message("Teklif", f"Excel (CSV) kaydedildi:\n{out_path}")

        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Excel Hatası", f"Hata:\n{e}\n\n{traceback.format_exc()}")

    def export_offer_teklif_pdf_simple(self, teklif_info=None, firma_info=None, firma_logo_path=None):
        """Özet teklif PDF: Ürün Adı | Detay | Miktar | Birim | Birim Fiyat | Toplam"""
        if self.current_project_name.strip():
            self.load_project_from_csv()
        if not self.exported_items:
            self.show_styled_info_message("Teklif", "Önce ürün ekleyiniz.")
            return

        info = teklif_info or {}
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Özet Teklif PDF kaydet", self._get_teklif_save_path("teklif_ozet.pdf"), "PDF Dosyası (*.pdf)"
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".pdf"):
            out_path += ".pdf"

        report_currency = (self.offer_currency or "USD").upper()
        cur_sym = {"TL": "₺", "USD": "$", "EUR": "€"}.get(report_currency, report_currency)
        material_markup = max(0.0, float(self.material_profit_percent))

        def fmt(v):
            return self.format_amount(v)

        def item_karli(item):
            mat_total = 0.0
            for c in (item.get("components") or []):
                try:
                    sub = float(c.get("subtotal", 0.0) or 0.0)
                except (TypeError, ValueError):
                    sub = 0.0
                if c.get("group") == "material":
                    mat_total += sub
            mat_profit = mat_total * (1.0 + material_markup / 100.0)
            lab_profit = 0.0
            for c in (item.get("components") or []):
                if c.get("group") != "labor":
                    continue
                try:
                    sub = float(c.get("subtotal", 0.0) or 0.0)
                except (TypeError, ValueError):
                    sub = 0.0
                lm = max(0.0, float(self.labor_profit_percents.get(c.get("name", ""), 25.0)))
                lab_profit += sub * (1.0 + lm / 100.0)
            return mat_profit + lab_profit

        painter = QPainter()
        pdf_started = False
        try:
            from PyQt6.QtGui import QPageLayout
            from PyQt6.QtCore import QMarginsF

            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setResolution(144)
            printer.setOutputFileName(out_path)
            printer.setPageLayout(QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(8, 10, 8, 10),
                QPageLayout.Unit.Millimeter,
            ))

            if not painter.begin(printer):
                self.show_styled_info_message("Teklif", "PDF oluşturulamadı.")
                return
            pdf_started = True

            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            left   = page_rect.left() + 18
            right  = page_rect.right() - 20
            top    = page_rect.top() + 20
            bottom = page_rect.bottom() - 20
            width  = right - left

            ff = "Calibri" if sys.platform != "darwin" else "Helvetica Neue"
            title_font = QFont(ff, 20); title_font.setBold(True)
            info_font  = QFont(ff, 10)
            firma_font = QFont(ff, 9)
            hdr_font   = QFont(ff, 10); hdr_font.setBold(True)
            data_font  = QFont(ff, 10)
            total_font = QFont(ff, 10); total_font.setBold(True)
            foot_font  = QFont(ff, 9)

            fi = firma_info or {}

            y = top
            page_no = 1

            # ── İki sütunlu başlık ──
            # Sol sütun: proje adı + müşteri bilgileri  (63%)
            # Sağ sütun: logo + firma bilgileri         (37%)
            left_w   = width * 0.56
            right_x  = left + left_w + 20
            right_w  = right - right_x
            hdr_y0   = top           # başlık bloğunun üst noktası

            # — Sağ sütun: Logo —
            # loadFromData: path tabanlı yükleme macOS'ta sessizce başarısız olabiliyor
            logo_img = QImage()
            if firma_logo_path and os.path.exists(firma_logo_path):
                try:
                    with open(firma_logo_path, "rb") as _lf:
                        logo_img.loadFromData(_lf.read())
                except Exception:
                    logo_img = QImage()
            if not logo_img.isNull():
                logo_img = logo_img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            ry = hdr_y0
            if not logo_img.isNull():
                logo_max_h = 100.0
                iw, ih = logo_img.width(), logo_img.height()
                scale = min(right_w / iw, logo_max_h / ih)
                lw, lh = iw * scale, ih * scale
                painter.drawImage(
                    QRectF(right_x, ry, lw, lh),
                    logo_img,
                    QRectF(0, 0, iw, ih)
                )
                ry += lh + 10

            # — Sağ sütun: Firma bilgileri —
            firma_lines = []
            if fi.get("unvan"):  firma_lines.append(("bold", fi["unvan"]))
            if fi.get("adres"):  firma_lines.append(("norm", fi["adres"]))
            vd_vno = " | ".join(filter(None, [fi.get("vd", ""), fi.get("vno", "")]))
            if vd_vno:           firma_lines.append(("norm", f"V.D / V.No: {vd_vno}"))
            if fi.get("iban"):   firma_lines.append(("norm", f"IBAN: {fi['iban']}"))
            if fi.get("banka"):  firma_lines.append(("norm", fi["banka"]))

            flh = QFontMetricsF(firma_font).height() + 12
            for style, txt_line in firma_lines:
                f2 = QFont(ff, 9); f2.setBold(style == "bold")
                painter.setFont(f2)
                painter.setPen(QColor(40, 40, 40))
                painter.drawText(QRectF(right_x, ry, right_w, flh),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                                 txt_line)
                ry += flh

            # — Sol sütun: Başlık —
            proje = (info.get("proje") or self.current_project_name.strip() or "—").upper()
            painter.setFont(title_font)
            painter.setPen(QColor(10, 10, 10))
            th = QFontMetricsF(title_font).height() + 18
            painter.drawText(QRectF(left, y, left_w, th),
                             int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                             f"{proje}  TEKLİFİ")
            y += th + 6

            # — Sol sütun: Müşteri bilgileri (iki alt sütun) —
            half = left_w / 2
            tarih_str = datetime.now().strftime("%d.%m.%Y")
            pairs = [
                (f"Teklif No: {info.get('teklif_no', '—')}",
                 f"Tarih: {tarih_str}"),
                (f"Hazırlayan: {info.get('hazirlayan', '—')}",
                 f"Geçerlilik: {info.get('sure', '—')}"),
                (f"İlgili Kişi: {info.get('kisi', '—')}",
                 f"Firma: {info.get('firma', '—')}"),
                (f"E-Posta: {info.get('mail', '—')}",
                 f"Telefon: {info.get('tel', '—')}"),
                (f"Para Birimi: {report_currency}", ""),
            ]
            ih = QFontMetricsF(info_font).height() + 12
            for left_txt, right_txt in pairs:
                painter.setFont(info_font)
                painter.setPen(QColor(50, 50, 50))
                painter.drawText(QRectF(left, y, half - 6, ih),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                                 left_txt)
                if right_txt:
                    painter.drawText(QRectF(left + half, y, half, ih),
                                     int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                                     right_txt)
                y += ih

            # Dikey ayırıcı çizgi (sağ ve sol sütun arası)
            painter.setPen(QPen(QColor(200, 200, 200), 0.8))
            painter.drawLine(QPointF(right_x - 7, hdr_y0), QPointF(right_x - 7, max(y, ry)))

            y = max(y, ry) + 8

            # Yatay ayırıcı çizgi
            painter.setPen(QPen(QColor(160, 160, 160), 0.8))
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            y += 6

            table_top = y   # dikey çizgiler bu noktadan başlayacak

            # ── Tablo ──
            cw = [
                width * 0.24,
                width * 0.30,
                width * 0.07,
                width * 0.06,
                width * 0.16,
                width * 0.17,
            ]
            hdrs = ["Ürün Adı", "Detay", "Mik.", "Bir.",
                    f"Birim Fiyat ({report_currency})", f"Toplam ({report_currency})"]

            HDR_BG   = QColor(198, 224, 180)
            HDR_TXT  = QColor(180, 0, 0)
            ROW_ALT  = QColor(245, 245, 245)
            TOTAL_BG = QColor(230, 230, 230)
            FOOT_H   = (QFontMetricsF(foot_font).height() + 8) * 5 + 10  # alan için rezerv

            line_h    = QFontMetricsF(data_font).height()
            min_row_h = line_h + 28

            def _lines(text, col_idx):
                text = str(text)
                if not text:
                    return 1
                fm = QFontMetricsF(data_font)
                avail_w = cw[col_idx] - 10
                lines, cur = 1, ""
                for word in text.split():
                    test = (cur + " " + word).strip()
                    if fm.horizontalAdvance(test) <= avail_w:
                        cur = test
                    else:
                        lines += 1; cur = word
                return lines

            def calc_rh(vals):
                return max(min_row_h,
                           max(_lines(vals[0], 0), _lines(vals[1] if len(vals) > 1 else "", 1))
                           * (line_h + 8) + 16)

            def draw_row_s(y_pos, vals, bg, font, txt_color=QColor(30, 30, 30), rh=None):
                rh = rh or min_row_h
                painter.fillRect(QRectF(left, y_pos, width, rh), bg)
                painter.setFont(font); painter.setPen(txt_color)
                cx = left
                for i, v in enumerate(vals):
                    if i in (0, 1):
                        r = QRectF(cx + 6, y_pos + 6, cw[i] - 12, rh - 12)
                        painter.drawText(r, int(Qt.AlignmentFlag.AlignLeft |
                                                Qt.AlignmentFlag.AlignTop |
                                                Qt.TextFlag.TextWordWrap), str(v))
                    else:
                        r = QRectF(cx + 4, y_pos, cw[i] - 8, rh)
                        painter.drawText(r, int(Qt.AlignmentFlag.AlignRight |
                                                Qt.AlignmentFlag.AlignVCenter), str(v))
                    cx += cw[i]
                painter.setPen(QPen(QColor(180, 180, 180), 0.5))
                painter.drawLine(QPointF(left, y_pos + rh), QPointF(right, y_pos + rh))

            # Tablo başlık satırı
            hdr_h = min_row_h * 2
            painter.fillRect(QRectF(left, y, width, hdr_h), HDR_BG)
            painter.setFont(hdr_font); painter.setPen(HDR_TXT)
            cx = left
            for i, hdr in enumerate(hdrs):
                af = Qt.AlignmentFlag.AlignLeft if i <= 1 else Qt.AlignmentFlag.AlignRight
                painter.drawText(QRectF(cx + 3, y, cw[i] - 6, hdr_h),
                                 int(af | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap), hdr)
                cx += cw[i]
            painter.setPen(QPen(QColor(150, 150, 150), 0.5))
            cx = left
            for cw_ in cw[:-1]:
                cx += cw_
                painter.drawLine(QPointF(cx, y), QPointF(cx, y + hdr_h))
            painter.setPen(QPen(QColor(180, 180, 180), 0.5))
            painter.drawLine(QPointF(left, y + hdr_h), QPointF(right, y + hdr_h))
            y += hdr_h

            # Veri satırları
            grand_total = 0.0
            for idx, item in enumerate(self.exported_items):
                karli = item_karli(item)
                try:
                    qty = float(item.get("quantity") or 0.0)
                except (TypeError, ValueError):
                    qty = 0.0
                birim_fiyat = karli / qty if qty > 0 else karli
                grand_total += karli
                bg = QColor(255, 255, 255) if idx % 2 == 0 else ROW_ALT
                vals = [
                    item.get("name", ""),
                    item.get("detail", ""),
                    fmt(qty) if qty else "",
                    item.get("unit", ""),
                    f"{cur_sym} {fmt(birim_fiyat)}",
                    f"{cur_sym} {fmt(karli)}",
                ]
                rh = calc_rh(vals)
                if y + rh > bottom - min_row_h * 2 - FOOT_H:
                    printer.newPage(); y = top; page_no += 1
                draw_row_s(y, vals, bg, data_font, rh=rh)
                y += rh

            # Dikey çizgiler (tablodan)
            painter.setPen(QPen(QColor(150, 150, 150), 0.5))
            cx = left
            for cw_ in cw[:-1]:
                cx += cw_
                painter.drawLine(QPointF(cx, table_top), QPointF(cx, y))

            # Toplam satırı
            if y + min_row_h > bottom - FOOT_H:
                printer.newPage(); y = top; page_no += 1
            draw_row_s(y, ["TOPLAM", "", "", "", "", f"{cur_sym} {fmt(grand_total)}"],
                       TOTAL_BG, total_font, QColor(180, 0, 0), rh=min_row_h)
            y += min_row_h

            # Dış çerçeve
            painter.setPen(QPen(QColor(100, 100, 100), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(left, table_top, width, y - table_top))

            # ── Dipnot / Kapsam ──
            y += 10
            painter.setPen(QPen(QColor(160, 160, 160), 0.5))
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            y += 4
            painter.setFont(foot_font)

            def foot_line(text, color=QColor(80, 80, 80)):
                nonlocal y
                painter.setPen(color)
                fh = QFontMetricsF(foot_font).height() + 8
                painter.drawText(QRectF(left, y, width, fh),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
                y += fh

            foot_line("• Belirtilen fiyatlara KDV dahil değildir.", QColor(160, 0, 0))
            dahil = info.get("dahil", [])
            dahil_degil = info.get("dahil_degil", [])
            if dahil:
                foot_line(f"• Fiyata dahil: {', '.join(dahil)}.")
            if dahil_degil:
                foot_line(f"• Fiyata dahil değil: {', '.join(dahil_degil)}.")
            for ek in info.get("ek_maddeler", []):
                if ek:
                    foot_line(f"• {ek}")

            painter.setFont(foot_font)
            painter.setPen(QColor(110, 110, 110))
            painter.drawText(QRectF(left, bottom + 4, width, 14), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), f"Sayfa {page_no}")

            # ── Yetkili Kaşe / İmza ──
            sign_h = 40
            if y + sign_h > bottom:
                printer.newPage(); y = top
            y += 28  # Tablodan daha fazla boşluk
            sign_f = QFont(ff, 10); sign_f.setBold(True)
            sign_text = "Yetkili Kaşe / İmza"
            fm_s = QFontMetricsF(sign_f)
            txt_w = fm_s.horizontalAdvance(sign_text)
            painter.setFont(sign_f); painter.setPen(QColor(40, 40, 40))
            painter.drawText(QPointF(left, y + fm_s.ascent()), sign_text)
            # Altı çizgi
            painter.setPen(QPen(QColor(40, 40, 40), 1.0))
            painter.drawLine(QPointF(left, y + fm_s.height() + 2),
                             QPointF(left + txt_w, y + fm_s.height() + 2))

        except Exception as e:
            import traceback
            self.show_styled_info_message("Teklif PDF Hatası", f"Hata:\n{e}\n\n{traceback.format_exc()}")
            return
        finally:
            if pdf_started:
                painter.end()

        self.show_styled_info_message("Teklif", f"Özet PDF kaydedildi:\n{out_path}")

    def export_offer_teklif_pdf(self, teklif_info=None, firma_info=None, firma_logo_path=None):
        """Teklif tablosunu PDF olarak üretir (Miktar, Birim, Malzeme, İşçilik, Birim Fiyat)."""
        if self.current_project_name.strip():
            self.load_project_from_csv()
        info = teklif_info or {}

        if not self.exported_items:
            QMessageBox.information(self, "Teklif", "Önce ürün ekleyiniz.")
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self, "Teklif PDF kaydet", self._get_teklif_save_path("teklif.pdf"), "PDF Dosyası (*.pdf)"
        )
        if not out_path:
            return
        if not out_path.lower().endswith(".pdf"):
            out_path += ".pdf"

        report_currency = (self.offer_currency or "USD").upper()
        cur_sym = {"TL": "₺", "USD": "$", "EUR": "€"}.get(report_currency, report_currency)
        material_markup = max(0.0, float(self.material_profit_percent))

        def fmt(v: float) -> str:
            return self.format_amount(v)

        def item_totals(item):
            mat_total = 0.0
            lab_total = 0.0
            for c in (item.get("components") or []):
                try:
                    sub = float(c.get("subtotal", 0.0) or 0.0)
                except (TypeError, ValueError):
                    sub = 0.0
                if c.get("group") == "material":
                    mat_total += sub
                elif c.get("group") == "labor":
                    lab_total += sub
            mat_profit = mat_total * (1.0 + material_markup / 100.0)
            lab_profit = 0.0
            for c in (item.get("components") or []):
                if c.get("group") != "labor":
                    continue
                try:
                    sub = float(c.get("subtotal", 0.0) or 0.0)
                except (TypeError, ValueError):
                    sub = 0.0
                lm = max(0.0, float(self.labor_profit_percents.get(c.get("name", ""), 25.0)))
                lab_profit += sub * (1.0 + lm / 100.0)
            karli = mat_profit + lab_profit
            return mat_total, lab_total, mat_total + lab_total, karli

        painter = QPainter()
        pdf_started = False
        try:
            from PyQt6.QtGui import QPageLayout
            from PyQt6.QtCore import QMarginsF

            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setResolution(144)
            printer.setOutputFileName(out_path)

            layout_obj = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Landscape,
                QMarginsF(8, 10, 8, 10),
                QPageLayout.Unit.Millimeter,
            )
            printer.setPageLayout(layout_obj)

            if not painter.begin(printer):
                QMessageBox.warning(self, "Teklif", "PDF oluşturulamadı.")
                return
            pdf_started = True
            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            left = page_rect.left() + 18
            right = page_rect.right() - 20
            top = page_rect.top() + 24
            bottom = page_rect.bottom() - 24
            width = right - left

            ff = "Calibri" if sys.platform != "darwin" else "Helvetica Neue"
            title_font = QFont(ff, 20); title_font.setBold(True)
            info_font  = QFont(ff, 10)
            firma_font = QFont(ff, 9)
            hdr_font   = QFont(ff, 10); hdr_font.setBold(True)
            data_font  = QFont(ff, 10)
            total_font = QFont(ff, 10); total_font.setBold(True)
            foot_font  = QFont(ff, 9)

            fi = firma_info or {}

            y = top
            page_no = 1

            # ── İki sütunlu başlık ──
            # Sol sütun (63%): proje adı + müşteri bilgileri
            # Sağ sütun (37%): logo + firma bilgileri
            left_w  = width * 0.56
            right_x = left + left_w + 20
            right_w = right - right_x
            hdr_y0  = top

            # — Sağ: Logo —
            logo_img = QImage()
            if firma_logo_path and os.path.exists(firma_logo_path):
                try:
                    with open(firma_logo_path, "rb") as _lf:
                        logo_img.loadFromData(_lf.read())
                except Exception:
                    logo_img = QImage()
            if not logo_img.isNull():
                logo_img = logo_img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            ry = hdr_y0
            if not logo_img.isNull():
                logo_max_h = 100.0
                iw, ih = logo_img.width(), logo_img.height()
                scale = min(right_w / iw, logo_max_h / ih)
                lw, lh = iw * scale, ih * scale
                painter.drawImage(
                    QRectF(right_x, ry, lw, lh),
                    logo_img,
                    QRectF(0, 0, iw, ih)
                )
                ry += lh + 10

            # — Sağ: Firma bilgileri —
            firma_lines = []
            if fi.get("unvan"):  firma_lines.append(("bold", fi["unvan"]))
            if fi.get("adres"):  firma_lines.append(("norm", fi["adres"]))
            vd_vno = " | ".join(filter(None, [fi.get("vd", ""), fi.get("vno", "")]))
            if vd_vno:           firma_lines.append(("norm", f"V.D / V.No: {vd_vno}"))
            if fi.get("iban"):   firma_lines.append(("norm", f"IBAN: {fi['iban']}"))
            if fi.get("banka"):  firma_lines.append(("norm", fi["banka"]))

            flh = QFontMetricsF(firma_font).height() + 12
            for style, txt_line in firma_lines:
                f2 = QFont(ff, 9); f2.setBold(style == "bold")
                painter.setFont(f2)
                painter.setPen(QColor(40, 40, 40))
                painter.drawText(QRectF(right_x, ry, right_w, flh),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                                 txt_line)
                ry += flh

            # — Sol: Başlık —
            proje = (info.get("proje") or self.current_project_name.strip() or "—").upper()
            painter.setFont(title_font)
            painter.setPen(QColor(10, 10, 10))
            th = QFontMetricsF(title_font).height() + 18
            painter.drawText(QRectF(left, y, left_w, th),
                             int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                             f"{proje}  TEKLİFİ  —  DETAYLI")
            y += th + 6

            # — Sol: Müşteri bilgileri —
            half = left_w / 2
            tarih_str = datetime.now().strftime("%d.%m.%Y")
            pairs = [
                (f"Teklif No: {info.get('teklif_no', '—')}",
                 f"Tarih: {tarih_str}"),
                (f"Hazırlayan: {info.get('hazirlayan', '—')}",
                 f"Geçerlilik: {info.get('sure', '—')}"),
                (f"İlgili Kişi: {info.get('kisi', '—')}",
                 f"Firma: {info.get('firma', '—')}"),
                (f"E-Posta: {info.get('mail', '—')}",
                 f"Telefon: {info.get('tel', '—')}"),
                (f"Para Birimi: {report_currency}", ""),
            ]
            ih = QFontMetricsF(info_font).height() + 12
            for lt, rt in pairs:
                painter.setFont(info_font)
                painter.setPen(QColor(50, 50, 50))
                painter.drawText(QRectF(left, y, half - 6, ih),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), lt)
                if rt:
                    painter.drawText(QRectF(left + half, y, half, ih),
                                     int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), rt)
                y += ih

            # Dikey ayırıcı
            painter.setPen(QPen(QColor(200, 200, 200), 0.8))
            painter.drawLine(QPointF(right_x - 7, hdr_y0), QPointF(right_x - 7, max(y, ry)))

            y = max(y, ry) + 6

            painter.setPen(QPen(QColor(160, 160, 160), 0.8))
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            y += 6

            table_top = y   # dikey çizgiler bu noktadan başlayacak
            FOOT_H = (QFontMetricsF(foot_font).height() + 8) * 5 + 10

            # Sütun genişlikleri (toplam = width)
            # Ürün Adı | Detay | Mik | Bir | Malzeme | İşçilik | Top.Maliyet | Karlı Top. | Birim Fiyat
            cw = [
                width * 0.20,  # Ürün Adı
                width * 0.22,  # Detay
                width * 0.05,  # Miktar
                width * 0.04,  # Birim
                width * 0.09,  # Malzeme
                width * 0.09,  # İşçilik
                width * 0.10,  # Toplam Maliyet
                width * 0.10,  # Karlı Toplam
                width * 0.11,  # Birim Fiyat
            ]
            hdrs = ["Ürün Adı", "Detay", "Mik.", "Bir.",
                    f"Malzeme\n({report_currency})", f"İşçilik\n({report_currency})",
                    "Toplam\nMaliyet", "Karlı\nToplam", "Birim\nFiyat"]
            HDR_BG   = QColor(198, 224, 180)   # Açık yeşil (Excel'deki gibi)
            HDR_TXT  = QColor(180, 0, 0)        # Koyu kırmızı başlık yazısı
            ROW_ALT  = QColor(245, 245, 245)
            TOTAL_BG = QColor(230, 230, 230)

            line_h = QFontMetricsF(data_font).height()
            min_row_h = line_h + 28   # minimum tek satır yüksekliği

            def _count_lines(text, col_idx):
                """Verilen sütun genişliğinde metnin kaç satır kapladığını hesaplar."""
                text = str(text)
                if not text:
                    return 1
                fm = QFontMetricsF(data_font)
                avail_w = cw[col_idx] - 10
                words = text.split()
                lines = 1
                cur_line = ""
                for word in words:
                    test = (cur_line + " " + word).strip()
                    if fm.horizontalAdvance(test) <= avail_w:
                        cur_line = test
                    else:
                        lines += 1
                        cur_line = word
                return lines

            def calc_row_h(vals):
                """Ürün Adı ve Detay sütunlarını sığdırmak için gereken satır yüksekliğini hesaplar."""
                name_lines   = _count_lines(vals[0] if vals else "", 0)
                detail_lines = _count_lines(vals[1] if len(vals) > 1 else "", 1)
                lines = max(name_lines, detail_lines)
                needed = lines * (line_h + 8) + 16
                return max(min_row_h, needed)

            def draw_row(y_pos, vals, bg, font, txt_color=QColor(30, 30, 30), this_row_h=None):
                rh = this_row_h if this_row_h is not None else min_row_h
                painter.fillRect(QRectF(left, y_pos, width, rh), bg)
                painter.setFont(font)
                painter.setPen(txt_color)
                cx = left
                for i, v in enumerate(vals):
                    if i in (0, 1):  # Ürün Adı ve Detay — sarmalı metin
                        r = QRectF(cx + 6, y_pos + 6, cw[i] - 12, rh - 12)
                        painter.drawText(r, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), str(v))
                    else:
                        r = QRectF(cx + 4, y_pos, cw[i] - 8, rh)
                        painter.drawText(r, int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), str(v))
                    cx += cw[i]
                # Yatay çizgi
                painter.setPen(QPen(QColor(180, 180, 180), 0.5))
                painter.drawLine(QPointF(left, y_pos + rh), QPointF(right, y_pos + rh))
                return rh

            def new_page():
                nonlocal y, page_no
                printer.newPage()
                y = top
                page_no += 1

            # Başlık satırı — çok satırlı başlıklar için 2 kat yükseklik
            hdr_h = min_row_h * 2
            painter.fillRect(QRectF(left, y, width, hdr_h), HDR_BG)
            painter.setFont(hdr_font)
            painter.setPen(HDR_TXT)
            cx = left
            for i, hdr in enumerate(hdrs):
                align_flag = Qt.AlignmentFlag.AlignLeft if i <= 1 else Qt.AlignmentFlag.AlignRight
                r = QRectF(cx + 3, y, cw[i] - 6, hdr_h)
                painter.drawText(r, int(align_flag | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap), hdr)
                cx += cw[i]
            # Dikey çizgiler
            painter.setPen(QPen(QColor(150, 150, 150), 0.5))
            cx = left
            for cwidth in cw[:-1]:
                cx += cwidth
                painter.drawLine(QPointF(cx, y), QPointF(cx, y + hdr_h))
            painter.setPen(QPen(QColor(180, 180, 180), 0.5))
            painter.drawLine(QPointF(left, y + hdr_h), QPointF(right, y + hdr_h))
            y += hdr_h

            # Veri satırları
            grand_mat = grand_lab = grand_tot = grand_karli = 0.0
            for idx, item in enumerate(self.exported_items):
                mat, lab, tot, karli = item_totals(item)
                grand_mat   += mat
                grand_lab   += lab
                grand_tot   += tot
                grand_karli += karli

                qty = item.get("quantity") or 0.0
                try:
                    qty = float(qty)
                except (TypeError, ValueError):
                    qty = 0.0
                birim_fiyat = karli / qty if qty > 0 else 0.0

                bg = QColor(255, 255, 255) if idx % 2 == 0 else ROW_ALT
                vals = [
                    item.get("name", ""),
                    item.get("detail", ""),
                    fmt(qty) if qty else "",
                    item.get("unit", ""),
                    f"{cur_sym} {fmt(mat)}",
                    f"{cur_sym} {fmt(lab)}",
                    f"{cur_sym} {fmt(tot)}",
                    f"{cur_sym} {fmt(karli)}",
                    f"{cur_sym} {fmt(birim_fiyat)}",
                ]
                this_rh = calc_row_h(vals)
                if y + this_rh > bottom - min_row_h * 2 - FOOT_H:
                    new_page()
                draw_row(y, vals, bg, data_font, this_row_h=this_rh)
                y += this_rh

            # Dikey çizgiler (table_top'tan başla)
            painter.setPen(QPen(QColor(150, 150, 150), 0.5))
            cx = left
            for cwidth in cw[:-1]:
                cx += cwidth
                painter.drawLine(QPointF(cx, table_top), QPointF(cx, y))

            # Toplam satırı
            if y + min_row_h > bottom - FOOT_H:
                new_page()
            total_vals = [
                "TOPLAM", "", "", "",
                f"{cur_sym} {fmt(grand_mat)}",
                f"{cur_sym} {fmt(grand_lab)}",
                f"{cur_sym} {fmt(grand_tot)}",
                f"{cur_sym} {fmt(grand_karli)}",
                "",
            ]
            draw_row(y, total_vals, TOTAL_BG, total_font, QColor(180, 0, 0), this_row_h=min_row_h)
            y += min_row_h

            # Dış çerçeve
            painter.setPen(QPen(QColor(100, 100, 100), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(left, table_top, width, y - table_top))

            # ── Dipnot ──
            y += 10
            painter.setPen(QPen(QColor(160, 160, 160), 0.5))
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            y += 4
            painter.setFont(foot_font)

            def foot_line(text, color=QColor(80, 80, 80)):
                nonlocal y
                painter.setPen(color)
                fh = QFontMetricsF(foot_font).height() + 8
                painter.drawText(QRectF(left, y, width, fh),
                                 int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
                y += fh

            foot_line("• Belirtilen fiyatlara KDV dahil değildir.", QColor(160, 0, 0))
            dahil = info.get("dahil", [])
            dahil_degil = info.get("dahil_degil", [])
            if dahil:
                foot_line(f"• Fiyata dahil: {', '.join(dahil)}.")
            if dahil_degil:
                foot_line(f"• Fiyata dahil değil: {', '.join(dahil_degil)}.")
            for ek in info.get("ek_maddeler", []):
                if ek:
                    foot_line(f"• {ek}")

            painter.setFont(foot_font)
            painter.setPen(QColor(110, 110, 110))
            painter.drawText(QRectF(left, bottom + 4, width, 14), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), f"Sayfa {page_no}")

            # ── Yetkili Kaşe / İmza ──
            sign_h = 40
            if y + sign_h > bottom:
                printer.newPage(); y = top
            y += 28  # Tablodan daha fazla boşluk
            sign_f = QFont(ff, 10); sign_f.setBold(True)
            sign_text = "Yetkili Kaşe / İmza"
            fm_s = QFontMetricsF(sign_f)
            txt_w = fm_s.horizontalAdvance(sign_text)
            painter.setFont(sign_f); painter.setPen(QColor(40, 40, 40))
            painter.drawText(QPointF(left, y + fm_s.ascent()), sign_text)
            painter.setPen(QPen(QColor(40, 40, 40), 1.0))
            painter.drawLine(QPointF(left, y + fm_s.height() + 2),
                             QPointF(left + txt_w, y + fm_s.height() + 2))

        except Exception as e:
            import traceback
            self.show_styled_info_message("Teklif PDF Hatası", f"Hata:\n{e}\n\n{traceback.format_exc()}")
            return
        finally:
            if pdf_started:
                painter.end()

        self.show_styled_info_message("Teklif", f"PDF kaydedildi:\n{out_path}")

    # --------- ÇİZİM ---------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        margin = 20

        # hit-box listelerini sıfırla
        self.keypad_buttons = []
        self.material_rects = []
        self.labor_rects = []
        self.material_price_rects = []
        self.labor_price_rects = []
        self.material_profit_rect = QRectF()
        self.labor_profit_rects = []

        # Başlık
        title_rect = QRectF(0, h * 0.02, w, 40)
        self.draw_center_text(
            painter,
            title_rect,
            "TenShoot Fiyatlama Ver : 2.0",
            QColor(40, 40, 40),
            16,
        )

        # Proje adı satırı (tıklanabilir, ortada dar bir alan)
        proj_width = w * 0.6
        proj_x = (w - proj_width) / 2.0
        proj_rect = QRectF(proj_x, h * 0.06, proj_width, 24)
        self.project_name_rect = proj_rect

        if self.current_project_name.strip():
            proj_text = f"Proje Adı: {self.current_project_name}"
        else:
            proj_text = "Proje Adı: (tıklayıp yaz)"

        self.draw_center_text(
            painter,
            proj_rect,
            proj_text,
            QColor(80, 80, 80),
            12,
        )


        pen = QPen(QColor(150, 150, 150), 1)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(float(margin), float(margin + 52)),
            QPointF(float(w - margin), float(margin + 52)),
        )

        # Kur / teklif para birimi kutularının konumu aşağıda (FİRE-RAPOR yanına) hesaplanacak
        self.usd_rate_rect = QRectF()
        self.eur_rate_rect = QRectF()
        self.offer_currency_rect = QRectF()

        # RAPOR kutusu konumu aşağıda (FİRE üstüne) hesaplanacak
        self.report_rect = QRectF()

        left_width = w * 0.25
        right_width = w * 0.20

            # === ANA BALON (küçük ve biraz yukarıda) ===
        center_diam = w * 0.20  # Eskisine göre ~%30–40 daha küçük
        center_rect = QRectF(
            w * 0.39,      # Orta kolonu hafifçe sağa kaydır
            h * 0.10,      # Biraz yukarı kaldır
            center_diam,
            center_diam,
        )
        self.center_rect = center_rect

        self.draw_sketch_ellipse(
            painter,
            center_rect,
            QColor(40, 40, 40),
            fill_alpha=0,
            pen_width=4,
        )

        header_rect = QRectF(
            self.center_rect.left() + 6,
            self.center_rect.top() + 8,
            self.center_rect.width() - 12,
            self.center_rect.height() * 0.34,
        )
        self.center_title_rect = header_rect
        self.draw_center_wrapped_text(
            painter,
            self.center_title_rect,
            self.current_product_name,
            QColor(80, 80, 80),
            14,
            max_lines=3,
        )


        value_rect = QRectF(self.center_rect.left(),
                            self.center_rect.center().y() - 25,
                            self.center_rect.width(), 50)
        self.draw_center_text(
            painter,
            value_rect,
            self.format_amount(self.line_total),
            QColor(20, 20, 20),
            24,
        )

        currency_rect = QRectF(self.center_rect.left(),
                               self.center_rect.bottom() - 35,
                               self.center_rect.width(), 20)
        self.draw_center_text(
            painter,
            currency_rect,
            self.offer_currency,
            QColor(100, 100, 100),
            12,
        )

        # Ana teklif (CSV) toplamını ana balonun altında göster
        total_offer = sum(item["unit_price"] for item in self.exported_items)
        summary_rect = QRectF(
            self.center_rect.left(),
            self.center_rect.bottom() + 5,
            self.center_rect.width(),
            20,
        )
        self.draw_center_text(
            painter,
            summary_rect,
            f"Ana teklif toplamı: {self.format_amount(total_offer)}",
            QColor(0, 0, 160),
            11,
        )


        sum_rect = QRectF(self.center_rect.left(),
                          self.center_rect.bottom() + 28,
                          self.center_rect.width(), 20)
        self.draw_center_text(
            painter,
            sum_rect,
            f"Bu satır toplamı: {self.format_amount(self.line_total)}",
            QColor(0, 0, 200),
            11,
        )

        # ==== SAĞ KOLON GEOMETRİ REFERANSI ====
        right_col_width = min(w * 0.30, 420.0)
        right_col_left = min(self.center_rect.right() + 65.0, w - margin - right_col_width)
        right_col_left = max(self.center_rect.right() + 40.0, right_col_left)
        right_col_center_x = right_col_left + right_col_width / 2.0

        # ==== SAĞ TARAFTA: FİRE / SIFIRLA / DIŞA AKTAR ====
        export_diam = max(88.0, right_col_width * 0.24)
        right_cluster_shift = min(44.0, right_col_width * 0.14)
        export_center_x = right_col_center_x - right_cluster_shift
        export_center_y = self.center_rect.center().y() + 8

        if sys.platform == "darwin":
            export_w = export_diam * 1.35
            export_h = export_diam * 0.95
        else:
            export_w = export_diam
            export_h = export_diam

        export_rect = QRectF(
            export_center_x - export_w / 2,
            export_center_y - export_h / 2,
            export_w,
            export_h,
        )
        self.export_rect = export_rect

        fire_w = export_rect.width() * 1.45
        fire_h = export_rect.height() * 0.46
        fire_y = export_rect.top() - fire_h - 14

        # RAPOR/FİRE balonları: kâr tablosu ile daha net hizalı, solda ayrı bir kolon
        fire_report_center_x = right_col_left + right_col_width * 0.32
        fire_x = fire_report_center_x - fire_w / 2
        self.free_waste_rect = QRectF(fire_x, fire_y, fire_w, fire_h)

        # RAPOR balonu: FİRE ile aynı merkezde ve hemen üstünde
        report_w = max(120.0, self.free_waste_rect.width() * 0.92)
        report_h = 32.0
        report_x = fire_report_center_x - report_w / 2.0
        report_y = max(margin + 58.0, self.free_waste_rect.top() - report_h * 2 - 16.0)
        self.report_rect = QRectF(report_x, report_y, report_w, report_h)

        # TEKLİF balonu: RAPOR ile FİRE arasında
        teklif_w = report_w
        teklif_h = report_h
        teklif_x = fire_report_center_x - teklif_w / 2.0
        teklif_y = self.report_rect.bottom() + 8.0
        self.teklif_rect = QRectF(teklif_x, teklif_y, teklif_w, teklif_h)

        # Kur / teklif para birimi kutuları: RAPOR/FİRE kolonu ile çakışmayacak ayrı kolon
        rate_w = min(250.0, max(190.0, right_col_width * 0.62))
        rate_h = 28.0
        rate_gap = 4.0
        rate_x = max(self.report_rect.right(), self.free_waste_rect.right()) + 16.0
        max_rate_x = w - margin - rate_w
        if rate_x > max_rate_x:
            shift_left = rate_x - max_rate_x
            self.report_rect.translate(-shift_left, 0)
            self.teklif_rect.translate(-shift_left, 0)
            self.free_waste_rect.translate(-shift_left, 0)
            rate_x = max_rate_x
        rate_top = self.report_rect.top() + 10.0

        self.usd_rate_rect = QRectF(rate_x, rate_top, rate_w, rate_h)
        self.eur_rate_rect = QRectF(rate_x, rate_top + rate_h + rate_gap, rate_w, rate_h)
        self.offer_currency_rect = QRectF(rate_x, rate_top + (rate_h + rate_gap) * 2, rate_w, rate_h)

        self.draw_sketch_ellipse(
            painter,
            self.free_waste_rect,
            QColor(40, 40, 40),
            fill_alpha=0,
            pen_width=2,
        )
        self.draw_center_text(
            painter,
            self.free_waste_rect,
            "FİRE",
            QColor(20, 20, 20),
            11,
        )
        self.draw_sketch_ellipse(
            painter,
            self.report_rect,
            QColor(20, 70, 180),
            fill_alpha=0,
            pen_width=2,
        )
        self.draw_center_text(
            painter,
            self.report_rect,
            "RAPOR",
            QColor(20, 70, 180),
            11,
        )
        self.draw_sketch_ellipse(
            painter,
            self.teklif_rect,
            QColor(0, 130, 60),
            fill_alpha=0,
            pen_width=2,
        )
        self.draw_center_text(
            painter,
            self.teklif_rect,
            "TEKLİF",
            QColor(0, 130, 60),
            11,
        )

        painter.setPen(QPen(QColor(20, 70, 180), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.usd_rate_rect)
        painter.drawRect(self.eur_rate_rect)
        painter.drawRect(self.offer_currency_rect)

        info_font = QFont(self.base_font_family, 9)
        painter.setFont(info_font)
        painter.setPen(QColor(20, 70, 180))
        painter.drawText(self.usd_rate_rect.adjusted(6, 0, -6, 0), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), f"USD Kuru: {self.format_amount(self.usd_rate)}")
        painter.drawText(self.eur_rate_rect.adjusted(6, 0, -6, 0), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), f"EUR Kuru: {self.format_amount(self.eur_rate)}")
        painter.drawText(self.offer_currency_rect.adjusted(6, 0, -6, 0), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), f"Teklif Para Birimi: {self.offer_currency}")

        # SIFIRLA balonu: ana balon ile dışa aktar arasında ortada,
        # dışa aktar çapının %30 küçüğü
        reset_diam = export_rect.width() * 0.70
        reset_center_x = (self.center_rect.right() + export_rect.left()) / 2.0
        reset_center_y = export_rect.center().y()
        self.reset_rect = QRectF(
            reset_center_x - reset_diam / 2,
            reset_center_y - reset_diam / 2,
            reset_diam,
            reset_diam,
        )

        self.draw_sketch_ellipse(
            painter,
            self.reset_rect,
            QColor(180, 0, 0),
            fill_alpha=0,
            pen_width=2,
        )
        reset_label_size = 9 if sys.platform == "darwin" else 11
        self.draw_center_text(
            painter,
            self.reset_rect,
            "SIFIRLA",
            QColor(180, 0, 0),
            reset_label_size,
        )

        # Dışa Aktar balonu
        self.draw_sketch_ellipse(
            painter,
            export_rect,
            QColor(40, 40, 40),
            fill_alpha=0,
            pen_width=3,
        )
        self.draw_center_text(
            painter,
            export_rect,
            "Dışa Aktar",
            QColor(40, 40, 40),
            12,
        )

        # Dışa Aktar'ın sağında Değiştir balonu
        edit_w = export_rect.width() * 0.78
        edit_h = export_rect.height() * 0.78
        edit_x = export_rect.right() + 10
        edit_y = export_rect.center().y() - edit_h / 2.0
        self.edit_rect = QRectF(edit_x, edit_y, edit_w, edit_h)
        self.draw_sketch_ellipse(
            painter,
            self.edit_rect,
            QColor(40, 40, 40),
            fill_alpha=0,
            pen_width=2,
        )
        self.draw_center_text(
            painter,
            self.edit_rect,
            "Değiştir",
            QColor(40, 40, 40),
            10,
        )

        # ---------- SOLDaki KATEGORİLER ----------
        left_x_center = margin + left_width * 0.5
        top_y = margin + 70

        # Malzeme başlığı + kendi + / - balonları
        mat_title_rect = QRectF(margin, top_y - 25, left_width, 20)
        self.draw_center_text(
            painter,
            mat_title_rect,
            "Malzeme",
            QColor(80, 80, 80),
            12,
        )

        plus_size = 18
        # sağ tarafa küçük + ve -
        self.mat_plus_rect = QRectF(
            mat_title_rect.right() - 2 * plus_size - 4,
            mat_title_rect.top() - 2,
            plus_size,
            plus_size,
        )
        self.mat_minus_rect = QRectF(
            mat_title_rect.right() - plus_size,
            mat_title_rect.top() - 2,
            plus_size,
            plus_size,
        )

        self.draw_sketch_ellipse(
            painter, self.mat_plus_rect, QColor(40, 120, 40), fill_alpha=0, pen_width=2
        )
        self.draw_center_text(
            painter, self.mat_plus_rect, "+", QColor(40, 120, 40), 11
        )

        self.draw_sketch_ellipse(
            painter, self.mat_minus_rect, QColor(150, 0, 0), fill_alpha=0, pen_width=2
        )
        self.draw_center_text(
            painter, self.mat_minus_rect, "−", QColor(150, 0, 0), 11
        )

        balloon_height = 40
        balloon_spacing = 10
        y_cursor = top_y

        # Malzeme balonları
        for idx, cat in enumerate(self.material_categories):
            main_rect = QRectF(
                left_x_center - (left_width * 0.6) / 2,
                y_cursor,
                left_width * 0.6,
                balloon_height,
            )
            self.material_rects.append(main_rect)

            is_active = (self.active_category == ("material", idx))
            text_color = QColor(180, 0, 0) if is_active else QColor(40, 40, 40)

            self.draw_sketch_ellipse(
                painter,
                main_rect,
                QColor(60, 60, 60),
                fill_alpha=20 if is_active else 0,
                pen_width=2,
                hatch=is_active,
            )
            self.draw_center_text(
                painter,
                main_rect,
                cat.get("name", ""),
                text_color,
                10,
            )

            # Yanında küçük fiyat balonu (tıklanabilir)
            price = float(cat.get("price", 0.0))
            unit = cat.get("unit", "")
            currency = str(cat.get("currency", "USD") or "USD").upper()
            price_text = f"{self.format_amount(price)} {currency} / {unit}"
            mini_rect = QRectF(
                main_rect.right() + 8,
                main_rect.center().y() - balloon_height * 0.4,
                left_width * 0.45,
                balloon_height * 0.8,
            )
            self.draw_sketch_ellipse(
                painter,
                mini_rect,
                QColor(40, 40, 40),
                fill_alpha=0,
                pen_width=1,
            )
            self.draw_center_text(
                painter,
                mini_rect,
                price_text,
                QColor(0, 0, 120),
                9,
            )
            self.material_price_rects.append(mini_rect)

            y_cursor += balloon_height + balloon_spacing

        # İşçilik başlığı
        labor_title_rect = QRectF(margin, y_cursor + 5, left_width, 20)
        self.draw_center_text(
            painter,
            labor_title_rect,
            "İşçilik",
            QColor(80, 80, 80),
            12,
        )

        self.lab_plus_rect = QRectF(
            labor_title_rect.right() - 2 * plus_size - 4,
            labor_title_rect.top() - 2,
            plus_size,
            plus_size,
        )
        self.lab_minus_rect = QRectF(
            labor_title_rect.right() - plus_size,
            labor_title_rect.top() - 2,
            plus_size,
            plus_size,
        )

        self.draw_sketch_ellipse(
            painter, self.lab_plus_rect, QColor(40, 120, 40), fill_alpha=0, pen_width=2
        )
        self.draw_center_text(
            painter, self.lab_plus_rect, "+", QColor(40, 120, 40), 11
        )

        self.draw_sketch_ellipse(
            painter, self.lab_minus_rect, QColor(150, 0, 0), fill_alpha=0, pen_width=2
        )
        self.draw_center_text(
            painter, self.lab_minus_rect, "−", QColor(150, 0, 0), 11
        )

        y_cursor += 30

        # İşçilik balonları
        for idx, cat in enumerate(self.labor_categories):
            main_rect = QRectF(
                left_x_center - (left_width * 0.6) / 2,
                y_cursor,
                left_width * 0.6,
                balloon_height,
            )
            self.labor_rects.append(main_rect)

            is_active = (self.active_category == ("labor", idx))
            text_color = QColor(180, 0, 0) if is_active else QColor(40, 40, 40)

            self.draw_sketch_ellipse(
                painter,
                main_rect,
                QColor(60, 60, 60),
                fill_alpha=20 if is_active else 0,
                pen_width=2,
                hatch=is_active,
            )
            self.draw_center_text(
                painter,
                main_rect,
                cat.get("name", ""),
                text_color,
                10,
            )

            price = float(cat.get("price", 0.0))
            unit = cat.get("unit", "")
            currency = str(cat.get("currency", "USD") or "USD").upper()
            price_text = f"{self.format_amount(price)} {currency} / {unit}"
            mini_rect = QRectF(
                main_rect.right() + 8,
                main_rect.center().y() - balloon_height * 0.4,
                left_width * 0.45,
                balloon_height * 0.8,
            )
            self.draw_sketch_ellipse(
                painter,
                mini_rect,
                QColor(40, 40, 40),
                fill_alpha=0,
                pen_width=1,
            )
            self.draw_center_text(
                painter,
                mini_rect,
                price_text,
                QColor(0, 80, 0),
                9,
            )
            self.labor_price_rects.append(mini_rect)

            y_cursor += balloon_height + balloon_spacing

        # ==== SAĞ TARAFTA: DIŞA AKTAR + ÖZETLER ====

        product_count = len(self.exported_items)
        total_offer = sum(item["unit_price"] for item in self.exported_items)

        # Tuş takımı geometrisini önceden hesapla (sol özet kutularını bunun altına yerleştireceğiz)
        key_size = w * 0.0385
        key_spacing = w * 0.005
        keypad_cols = max((len(row) for row in self.keypad_rows), default=3)
        keypad_width = (key_size * keypad_cols) + (key_spacing * max(0, keypad_cols - 1))
        start_x = self.center_rect.center().x() - keypad_width / 2.0
        keypad_top = self.center_rect.bottom() + h * 0.06
        keypad_rows_count = len(self.keypad_rows)
        keypad_bottom = keypad_top + (key_size * keypad_rows_count) + (key_spacing * max(0, keypad_rows_count - 1))

        # Dışa aktar balonu altında: bilgi kutusu (kâr tablosu limitlerinde)
        info_box_h = 58
        info_box_rect = QRectF(right_col_left, export_rect.bottom() + 10, right_col_width, info_box_h)
        painter.setPen(QPen(QColor(40, 40, 40), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(info_box_rect)

        info_split_y = info_box_rect.top() + info_box_rect.height() / 2.0
        painter.drawLine(int(info_box_rect.left()), int(info_split_y), int(info_box_rect.right()), int(info_split_y))

        self.export_count_rect = QRectF(info_box_rect.left(), info_box_rect.top(), info_box_rect.width(), info_box_rect.height() / 2.0)
        self.draw_center_text(
            painter,
            self.export_count_rect,
            f"Aktarılan ürün sayısı: {product_count} iş",
            QColor(120, 0, 0),
            11,
        )
        self.draw_center_text(
            painter,
            QRectF(info_box_rect.left(), info_split_y, info_box_rect.width(), info_box_rect.height() / 2.0),
            f"Maliyet Toplamı: {self.format_amount(total_offer)}",
            QColor(0, 0, 160),
            11,
        )

        # --- KATEGORİ TOPLAMLARI ---
        material_stats, labor_stats, labor_total = self.compute_component_totals()
        material_grand_total = 0.0
        for stat in material_stats.values():
            try:
                material_grand_total += float(stat.get("subtotal", 0.0) or 0.0)
            except (TypeError, ValueError):
                pass

        # Sol mini özet kutuları: keypad'in altında, ancak genişlik merkez balonla aynı
        mini_width = self.center_rect.width()
        mini_height = 52
        mini_x = self.center_rect.left()
        mini_top = keypad_bottom + 18

        material_box_rect = QRectF(mini_x, mini_top, mini_width, mini_height)
        labor_box_rect = QRectF(mini_x, mini_top + mini_height + 8, mini_width, mini_height)

        painter.drawRect(material_box_rect)
        painter.drawRect(labor_box_rect)

        font_mini = QFont(self.base_font_family, 13)
        painter.setFont(font_mini)
        painter.setPen(QColor(200, 0, 0))

        material_text = f"Malzeme Toplamı: {self.format_amount(material_grand_total)} {self.offer_currency}"
        labor_text = f"İşçilik Toplamı: {self.format_amount(labor_total)} {self.offer_currency}"

        painter.drawText(material_box_rect.adjusted(6, 0, -6, 0), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), material_text)
        painter.drawText(labor_box_rect.adjusted(6, 0, -6, 0), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), labor_text)

        # İşçilik kalemlerinin miktar toplamları (ayrı kutular)
        labor_amount_box_bottom = labor_box_rect.bottom()
        labor_name_font = QFont(self.base_font_family, 10)
        labor_val_font = QFont(self.base_font_family, 11)

        if labor_stats:
            labor_row_h = 34
            labor_row_gap = 6
            y_labor = labor_box_rect.bottom() + 10
            for labor_name in sorted(labor_stats.keys()):
                stat = labor_stats[labor_name]
                amount_val = float(stat.get("amount", 0.0) or 0.0)
                unit_txt = (stat.get("unit", "") or "").strip()
                amount_txt = f"{self.format_amount(amount_val)} {unit_txt}".strip()

                row_rect = QRectF(mini_x, y_labor, mini_width, labor_row_h)
                painter.setPen(QPen(QColor(40, 40, 40), 1))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(row_rect)

                painter.setFont(labor_name_font)
                painter.setPen(QColor(80, 80, 80))
                painter.drawText(
                    row_rect.adjusted(8, 0, -8, 0),
                    int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                    f"{labor_name.upper()} TOPLAMI:",
                )

                painter.setFont(labor_val_font)
                painter.setPen(QColor(0, 90, 0))
                painter.drawText(
                    row_rect.adjusted(8, 0, -8, 0),
                    int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
                    amount_txt,
                )

                y_labor += labor_row_h + labor_row_gap

            labor_amount_box_bottom = y_labor - labor_row_gap

        # --- Sağ boşlukta kâr simülasyonu paneli ---
        panel_top_anchor = info_box_rect.bottom() + 8
        table_rows = 2 + len(labor_stats) + 1
        row_h = 30
        table_height = table_rows * row_h + 14
        panel_rect = QRectF(right_col_left, panel_top_anchor, right_col_width, table_height + 72)

        if right_col_width >= 260:
            pen = QPen(QColor(40, 40, 40), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(panel_rect)

            title_font = QFont(self.base_font_family, self.panel_font_size(10))
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.drawText(panel_rect.adjusted(8, 6, -8, 0), int(Qt.AlignmentFlag.AlignLeft), "Kâr Simülasyon Tablosu")

            table_top = panel_rect.top() + 26
            col_name_w = panel_rect.width() * 0.50
            col_pct_w = panel_rect.width() * 0.22
            col_total_w = panel_rect.width() - col_name_w - col_pct_w

            painter.drawLine(int(panel_rect.left()), int(table_top), int(panel_rect.right()), int(table_top))
            x1 = panel_rect.left() + col_name_w
            x2 = x1 + col_pct_w
            painter.drawLine(int(x1), int(table_top), int(x1), int(table_top + table_height))
            painter.drawLine(int(x2), int(table_top), int(x2), int(table_top + table_height))

            row_font = QFont(self.base_font_family, self.panel_font_size(9))
            painter.setFont(row_font)
            y_row = table_top

            def draw_row(name, pct_text, total_text, editable=False, target_rect=None):
                nonlocal y_row
                painter.drawLine(int(panel_rect.left()), int(y_row + row_h), int(panel_rect.right()), int(y_row + row_h))
                painter.drawText(QRectF(panel_rect.left() + 4, y_row, col_name_w - 8, row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), name)
                pct_rect = QRectF(x1 + 2, y_row + 3, col_pct_w - 4, row_h - 6)
                if editable:
                    self.draw_sketch_ellipse(painter, pct_rect, QColor(0, 90, 0), fill_alpha=0, pen_width=1)
                    if target_rect is not None:
                        target_rect.setRect(pct_rect.x(), pct_rect.y(), pct_rect.width(), pct_rect.height())
                painter.drawText(pct_rect, int(Qt.AlignmentFlag.AlignCenter), pct_text)
                painter.drawText(QRectF(x2 + 4, y_row, col_total_w - 8, row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), total_text)
                y_row += row_h

            painter.drawText(QRectF(panel_rect.left() + 4, y_row, col_name_w - 8, row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), "Kalem")
            painter.drawText(QRectF(x1 + 2, y_row, col_pct_w - 4, row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter), "Kâr %")
            painter.drawText(QRectF(x2 + 4, y_row, col_total_w - 8, row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), "Toplam")
            y_row += row_h

            material_markup = max(0.0, float(self.material_profit_percent))
            material_with_profit = material_grand_total * (1.0 + material_markup / 100.0)
            draw_row(
                "Malzeme",
                f"{self.format_amount(material_markup)}",
                self.format_amount(material_with_profit),
                editable=True,
                target_rect=self.material_profit_rect,
            )

            labor_profit_total = 0.0
            for labor_name in sorted(labor_stats.keys()):
                labor_subtotal = float(labor_stats[labor_name].get("subtotal", 0.0) or 0.0)
                labor_markup = max(0.0, float(self.labor_profit_percents.get(labor_name, 25.0)))
                labor_with_profit = labor_subtotal * (1.0 + labor_markup / 100.0)
                labor_profit_total += labor_with_profit

                click_rect = QRectF()
                self.labor_profit_rects.append({"name": labor_name, "rect": click_rect})
                draw_row(
                    labor_name,
                    f"{self.format_amount(labor_markup)}",
                    self.format_amount(labor_with_profit),
                    editable=True,
                    target_rect=click_rect,
                )

            final_offer_total = material_with_profit + labor_profit_total
            base_total = material_grand_total + labor_total
            total_profit = final_offer_total - base_total
            draw_row("Yeni Teklif Toplamı", "-", self.format_amount(final_offer_total), editable=False)

            emphasis_font = QFont(self.base_font_family, self.panel_font_size(10))
            emphasis_font.setBold(True)
            painter.setFont(emphasis_font)
            painter.setPen(QColor(0, 80, 0))
            painter.drawText(
                QRectF(panel_rect.left() + 6, panel_rect.bottom() - 46, panel_rect.width() - 12, 18),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
                f"Toplam Elde Edilecek Kâr: {self.format_amount(total_profit)}",
            )
            painter.setPen(QColor(0, 0, 160))
            painter.drawText(
                QRectF(panel_rect.left() + 6, panel_rect.bottom() - 24, panel_rect.width() - 12, 20),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
                f"Teklif (Kârlı): {self.format_amount(final_offer_total)}",
            )

            # --- Malzemelerin fireli toplam miktar tablosu ---
            fire_rows = max(1, len(material_stats))
            fire_row_h = 22
            # Başlık(24) + sütun başlığı satırı + malzeme satırları + alt boşluk
            fire_table_h = 24 + fire_row_h * (fire_rows + 1) + 12
            fire_rect = QRectF(right_col_left, panel_rect.bottom() + 10, right_col_width, fire_table_h)
            painter.setPen(QPen(QColor(40, 40, 40), 2))
            painter.drawRect(fire_rect)

            fire_title_font = QFont(self.base_font_family, self.panel_font_size(9))
            fire_title_font.setBold(True)
            painter.setFont(fire_title_font)
            painter.setPen(QColor(30, 30, 30))
            painter.drawText(fire_rect.adjusted(8, 4, -8, 0), int(Qt.AlignmentFlag.AlignLeft), "Malzemelerin Fireli Toplam Miktarı")

            col1_right = fire_rect.left() + fire_rect.width() * 0.46
            col2_right = fire_rect.left() + fire_rect.width() * 0.73
            table_y = fire_rect.top() + 24
            painter.drawLine(int(fire_rect.left()), int(table_y), int(fire_rect.right()), int(table_y))
            painter.drawLine(int(col1_right), int(table_y), int(col1_right), int(fire_rect.bottom()))
            painter.drawLine(int(col2_right), int(table_y), int(col2_right), int(fire_rect.bottom()))

            painter.drawText(QRectF(fire_rect.left() + 4, table_y, col1_right - fire_rect.left() - 8, fire_row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), "Malzeme")
            painter.drawText(QRectF(col1_right + 4, table_y, col2_right - col1_right - 8, fire_row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), "Fireli Miktar")
            painter.drawText(QRectF(col2_right + 4, table_y, fire_rect.right() - col2_right - 8, fire_row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), "Toplam Fiyat")

            y_fire = table_y + fire_row_h
            painter.setFont(QFont(self.base_font_family, self.panel_font_size(8)))
            for name in sorted(material_stats.keys()):
                stat = material_stats[name]
                gross_amount = float(stat.get("gross_amount", 0.0) or 0.0)
                unit = (stat.get("unit", "") or "").strip()
                gross_text = f"{self.format_amount(gross_amount)} {unit}".strip()
                subtotal_text = self.format_amount(float(stat.get("subtotal", 0.0) or 0.0))

                painter.drawLine(int(fire_rect.left()), int(y_fire + fire_row_h), int(fire_rect.right()), int(y_fire + fire_row_h))
                painter.drawText(QRectF(fire_rect.left() + 4, y_fire, col1_right - fire_rect.left() - 8, fire_row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), name)
                painter.drawText(QRectF(col1_right + 4, y_fire, col2_right - col1_right - 8, fire_row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), gross_text)
                painter.drawText(QRectF(col2_right + 4, y_fire, fire_rect.right() - col2_right - 8, fire_row_h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), subtotal_text)
                y_fire += fire_row_h

            if not material_stats:
                painter.drawText(
                    QRectF(fire_rect.left() + 4, y_fire, fire_rect.width() - 8, fire_row_h),
                    int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                    "(Henüz malzeme yok)",
                )

            # --- BU SATIR BİLEŞENLERİ KUTUSU (aynı X ve genişlik) ---
            components_top = fire_rect.bottom() + 10
            components_height = max(180.0, h * 0.16)
            components_list_rect = QRectF(right_col_left, components_top, right_col_width, components_height)
        else:
            self.material_profit_rect = QRectF()
            components_top = h * 0.52
            components_height = h * 0.24
            components_list_rect = QRectF(export_rect.left(), components_top, export_rect.width(), components_height)

        # Çerçeveyi çiz
        pen = QPen(QColor(40, 40, 40))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(components_list_rect)

        inner_left = components_list_rect.left() + 8
        inner_width = components_list_rect.width() - 16
        y_text = components_list_rect.top() + 8
        line_h = 22

        font_components = QFont(self.base_font_family, 10)
        painter.setFont(font_components)
        painter.setPen(QColor(80, 80, 80))

        painter.drawText(
            QRectF(inner_left, y_text, inner_width, line_h),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            "Bu satır bileşenleri:",
        )
        y_text += line_h

        if self.current_components:
            for idx, comp in enumerate(self.current_components):
                name = comp.get("name", "")
                amount = comp.get("amount", 0.0)
                unit = comp.get("unit", "")
                amt_str = self.format_amount(amount)
                text = f"- {name} ({amt_str} {unit})" if unit else f"- {name} ({amt_str})"

                del_size = line_h - 4
                del_rect = QRectF(inner_left + inner_width - del_size, y_text + 2, del_size, del_size)
                text_rect = QRectF(inner_left, y_text, inner_width - del_size - 6, line_h)

                painter.setPen(QColor(80, 80, 80))
                painter.drawText(
                    text_rect,
                    int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                    text,
                )

                self.draw_sketch_ellipse(
                    painter,
                    del_rect,
                    QColor(170, 0, 0),
                    fill_alpha=0,
                    pen_width=1,
                )
                painter.setPen(QColor(170, 0, 0))
                painter.drawText(del_rect, int(Qt.AlignmentFlag.AlignCenter), "×")
                self.component_delete_rects.append({"index": idx, "rect": QRectF(del_rect)})

                y_text += line_h
                if y_text > components_list_rect.bottom() - line_h:
                    break
        else:
            painter.drawText(
                QRectF(inner_left, y_text, inner_width, line_h),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                "(Henüz eklenmiş bileşen yok)",
            )

        needed_canvas_height = max(
            self.minimumHeight(),
            components_list_rect.bottom() + 60,
            labor_amount_box_bottom + 40,
        )
        self.setMinimumHeight(int(needed_canvas_height))

        # --- Rakam tuş takımı yerleşimi ---
        y = keypad_top

        # Önizleme balonu
        self.preview_box_rect = QRectF(
            start_x - key_size * 1.35,
            y,
            key_size * 1.2,
            key_size * 1.1,
        )
        self.draw_sketch_ellipse(
            painter,
            self.preview_box_rect,
            QColor(180, 0, 0),
            fill_alpha=0,
            pen_width=1,
        )
        preview_box_text = self.format_amount(self.preview_value())
        self.draw_center_text(
            painter,
            self.preview_box_rect,
            preview_box_text,
            QColor(180, 0, 0),
            13,
        )

        # Keypad tuşları
        for row in self.keypad_rows:
            x = start_x
            for label in row:
                rect = QRectF(x, y, key_size, key_size)
                self.draw_sketch_ellipse(
                    painter,
                    rect,
                    QColor(40, 40, 40),
                    fill_alpha=0,
                    pen_width=1,
                )
                self.draw_center_text(
                    painter,
                    rect,
                    label,
                    QColor(20, 20, 20),
                    14,
                )
                self.keypad_buttons.append({"label": label, "rect": QRectF(rect)})
                x += key_size + key_spacing
            y += key_size + key_spacing



        # ---------- Drag edilen kategori balonunu hayalet olarak çiz ----------
        if self.dragging_category is not None:
            group, idx = self.dragging_category
            cat = None
            if group == "material" and 0 <= idx < len(self.material_categories):
                cat = self.material_categories[idx]
            elif group == "labor" and 0 <= idx < len(self.labor_categories):
                cat = self.labor_categories[idx]
            if cat is not None:
                ghost_rect = QRectF(
                    self.drag_position.x() - 50,
                    self.drag_position.y() - 20,
                    100,
                    40,
                )
                self.draw_sketch_ellipse(
                    painter,
                    ghost_rect,
                    QColor(80, 80, 80),
                    fill_alpha=10,
                    pen_width=2,
                )
                self.draw_center_text(
                    painter,
                    ghost_rect,
                    cat.get("name", ""),
                    QColor(80, 0, 0),
                    9,
                )


def main():
    app = QApplication(sys.argv)
    window = SketchPriceUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Önce lisans kontrolü
    if not verify_license():
        # Lisans geçersiz veya yok -> programı kapat
        sys.exit(0)

    # Lisans TAMAM ise arayüzü aç
    content = SketchPriceUI()

    # Scroll alanı
    scroll = QScrollArea()
    scroll.setWidget(content)
    scroll.setWidgetResizable(True)

    # Görünen pencere boyutu (üst kısmı göstersin, alta doğru scroll yap)
    scroll.resize(1300, 800)
    scroll.setWindowTitle("TenShoot Fiyat Analiz Yardımcı ARAYÜZ Ver : 2.0")

    # Arkaplanın da beyaz kalması için (gölgeli alan olmasın)
    scroll.setStyleSheet("background-color: white;")

    scroll.show()
    sys.exit(app.exec())
