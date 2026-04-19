"""
Import Data Page
- Upload CSV or Excel file
- Validate rows (required fields, format checks)
- Preview results with valid/warning/error rows
- Import valid rows only
- Provides downloadable CSV template
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import get_session, generate_employee_id, log_action, degree_to_title_name
from src.database.models import Employee, Title, OrgUnit
from datetime import datetime
import csv
import os


REQUIRED_COLUMNS = ["first_name", "last_name", "degree", "position", "join_date", "base_salary"]
OPTIONAL_COLUMNS = ["work_email", "phone", "address", "personal_email"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

TEMPLATE_HEADERS = [
    "first_name", "last_name", "degree", "position",
    "join_date", "base_salary", "work_email", "phone", "address"
]


class ImportDataPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.preview_data = []
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet("background: white; border-bottom: 2px solid #e5e7eb;")
        h = QHBoxLayout(header)
        h.setContentsMargins(28, 0, 28, 0)
        title = QLabel(t("import_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
        sub = QLabel(t("import_subtitle"))
        sub.setStyleSheet("font-size: 13px; color: #9ca3af; margin-left: 12px;")
        h.addWidget(title)
        h.addWidget(sub)
        h.addStretch()
        layout.addWidget(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(28, 24, 28, 28)
        cl.setSpacing(20)

        # Steps indicator
        steps = QFrame()
        steps.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        sl = QHBoxLayout(steps)
        sl.setContentsMargins(24, 16, 24, 16)
        sl.setSpacing(0)

        self.step_labels = []
        for i, step in enumerate(["1. Upload File", "2. Validate Data", "3. Import"]):
            lbl = QLabel(step)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size: 13px; color: #9ca3af; padding: 6px 20px;")
            self.step_labels.append(lbl)
            sl.addWidget(lbl)
            if i < 2:
                arrow = QLabel("→")
                arrow.setAlignment(Qt.AlignCenter)
                arrow.setStyleSheet("color: #d1d5db; font-size: 16px;")
                sl.addWidget(arrow)
        cl.addWidget(steps)
        self._set_step(0)

        # Two column layout
        cols = QHBoxLayout()
        cols.setSpacing(20)
        cols.setAlignment(Qt.AlignTop)

        # Left: upload area + preview
        left = QVBoxLayout()
        left.setSpacing(16)

        # Upload card
        self.upload_card = QFrame()
        self.upload_card.setFixedHeight(200)
        self.upload_card.setStyleSheet("background: white; border-radius: 12px; border: 2px dashed #bfdbfe;")
        uc = QVBoxLayout(self.upload_card)
        uc.setAlignment(Qt.AlignCenter)
        uc.setSpacing(12)

        upload_icon = QLabel("📂")
        upload_icon.setAlignment(Qt.AlignCenter)
        upload_icon.setStyleSheet("font-size: 36px; background: transparent;")
        uc.addWidget(upload_icon)

        upload_title = QLabel("Upload Employee Data File")
        upload_title.setAlignment(Qt.AlignCenter)
        upload_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #111827; background: transparent;")
        uc.addWidget(upload_title)

        upload_sub = QLabel("Supported: CSV (.csv)")
        upload_sub.setAlignment(Qt.AlignCenter)
        upload_sub.setStyleSheet("font-size: 13px; color: #9ca3af; background: transparent;")
        uc.addWidget(upload_sub)

        upload_btn = QPushButton("Choose File")
        upload_btn.setCursor(Qt.PointingHandCursor)
        upload_btn.setFixedSize(140, 36)
        upload_btn.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; } QPushButton:hover { background: #111827; }")
        upload_btn.clicked.connect(self._choose_file)
        uc.addWidget(upload_btn, alignment=Qt.AlignCenter)
        left.addWidget(self.upload_card)

        # File info label
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("font-size: 12px; color: #6b7280; padding: 0 4px;")
        left.addWidget(self.file_label)

        # Stats row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(12)
        left.addLayout(self.stats_row)

        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(8)
        self.preview_table.setHorizontalHeaderLabels([
            "Row", "First Name", "Last Name", "Degree",
            "Position", "Join Date", "Salary", "Status"
        ])
        self.preview_table.setStyleSheet("""
            QTableWidget { background: white; border: 1px solid #e5e7eb; border-radius: 12px; font-size: 13px; color: #111827; }
            QTableWidget::item { padding: 6px 10px; border-bottom: 1px solid #f3f4f6; color: #111827; }
            QHeaderView::section { background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb; padding: 8px 10px; font-size: 12px; font-weight: bold; color: #6b7280; }
        """)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.preview_table.setColumnWidth(0, 50)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setVisible(False)
        left.addWidget(self.preview_table)

        # Import button
        self.import_btn = QPushButton("✓  Import Valid Rows")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.setFixedHeight(44)
        self.import_btn.setStyleSheet("QPushButton { background: #10b981; color: white; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #059669; } QPushButton:disabled { background: #d1d5db; color: #9ca3af; }")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._import)
        left.addWidget(self.import_btn)

        cols.addLayout(left, 3)

        # Right: instructions
        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        # Template download
        tmpl_card = QFrame()
        tmpl_card.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e5e7eb;")
        tc = QVBoxLayout(tmpl_card)
        tc.setContentsMargins(16, 14, 16, 14)
        tc.setSpacing(8)
        tc_title = QLabel("📥 Download Template")
        tc_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #111827; background: transparent;")
        tc.addWidget(tc_title)
        tc_sub = QLabel("Use this template to ensure correct column formatting before importing.")
        tc_sub.setWordWrap(True)
        tc_sub.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        tc.addWidget(tc_sub)
        tmpl_btn = QPushButton("Download CSV Template")
        tmpl_btn.setCursor(Qt.PointingHandCursor)
        tmpl_btn.setFixedHeight(34)
        tmpl_btn.setStyleSheet("QPushButton { background: #f3f4f6; color: #374151; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 12px; } QPushButton:hover { background: #e5e7eb; }")
        tmpl_btn.clicked.connect(self._download_template)
        tc.addWidget(tmpl_btn)
        right.addWidget(tmpl_card)

        # Required columns
        req_card = QFrame()
        req_card.setStyleSheet("background: #eff6ff; border-radius: 12px; border: 1px solid #bfdbfe;")
        rc = QVBoxLayout(req_card)
        rc.setContentsMargins(16, 14, 16, 14)
        rc.setSpacing(6)
        rc_title = QLabel("Required Columns")
        rc_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e40af; background: transparent;")
        rc.addWidget(rc_title)
        for col in REQUIRED_COLUMNS:
            lbl = QLabel(f"• {col}")
            lbl.setStyleSheet("font-size: 12px; color: #4338ca; background: transparent;")
            rc.addWidget(lbl)
        right.addWidget(req_card)

        # Cleaning guide
        guide_card = QFrame()
        guide_card.setStyleSheet("background: #fefce8; border-radius: 12px; border: 1px solid #fde047;")
        gc = QVBoxLayout(guide_card)
        gc.setContentsMargins(16, 14, 16, 14)
        gc.setSpacing(6)
        gc_title = QLabel("Data Cleaning Guide")
        gc_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #854d0e; background: transparent;")
        gc.addWidget(gc_title)
        for tip in [
            "degree must be: BSc, MSc, PhD, or Other",
            "join_date format: YYYY-MM-DD",
            "base_salary: number only (e.g. 2500)",
            "Remove duplicate entries before importing",
            "Ensure no empty required fields",
        ]:
            lbl = QLabel(f"• {tip}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 12px; color: #a16207; background: transparent;")
            gc.addWidget(lbl)
        right.addWidget(guide_card)

        cols.addLayout(right, 2)
        cl.addLayout(cols)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _set_step(self, step):
        for i, lbl in enumerate(self.step_labels):
            if i == step:
                lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563eb; background: #eff6ff; border-radius: 6px; padding: 6px 20px;")
            else:
                lbl.setStyleSheet("font-size: 13px; color: #9ca3af; padding: 6px 20px;")

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Employee Data File", "", "CSV Files (*.csv)"
        )
        if not path:
            return

        self.file_label.setText(f"File: {os.path.basename(path)}")
        self._set_step(1)
        self._validate_file(path)

    def _validate_file(self, path):
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = [h.strip().lower() for h in (reader.fieldnames or [])]

                missing = [col for col in REQUIRED_COLUMNS if col not in headers]
                if missing:
                    QMessageBox.critical(self, "Invalid File",
                        f"Missing required columns: {', '.join(missing)}\n\nDownload the template for the correct format.")
                    return

                rows = []
                for i, row in enumerate(reader, start=2):
                    cleaned = {k.strip().lower(): v.strip() for k, v in row.items()}
                    issues = []

                    for col in REQUIRED_COLUMNS:
                        if not cleaned.get(col):
                            issues.append(f"Missing {col}")

                    degree = cleaned.get("degree", "")
                    if degree and degree not in ["BSc", "MSc", "PhD", "Other"]:
                        issues.append(f"Invalid degree '{degree}'")

                    try:
                        if cleaned.get("join_date"):
                            datetime.strptime(cleaned["join_date"], "%Y-%m-%d")
                    except ValueError:
                        issues.append("join_date must be YYYY-MM-DD")

                    try:
                        if cleaned.get("base_salary"):
                            float(cleaned["base_salary"])
                    except ValueError:
                        issues.append("base_salary must be a number")

                    status = "error" if issues else "valid"
                    rows.append({
                        "row": i,
                        "first_name": cleaned.get("first_name", ""),
                        "last_name":  cleaned.get("last_name", ""),
                        "degree":     cleaned.get("degree", ""),
                        "position":   cleaned.get("position", ""),
                        "join_date":  cleaned.get("join_date", ""),
                        "base_salary":cleaned.get("base_salary", ""),
                        "work_email": cleaned.get("work_email", ""),
                        "phone":      cleaned.get("phone", ""),
                        "address":    cleaned.get("address", ""),
                        "status":     status,
                        "issues":     issues,
                        "_raw":       cleaned,
                    })

            self.preview_data = rows
            self._show_preview(rows)
        except Exception as e:
            QMessageBox.critical(self, t("error"), f"Could not read file:\n{str(e)}")

    def _show_preview(self, rows):
        valid = [r for r in rows if r["status"] == "valid"]
        errors = [r for r in rows if r["status"] == "error"]

        # Stats
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for label, val, color in [
            (f"Total Rows", len(rows), "#2563eb"),
            (f"Valid", len(valid), "#10b981"),
            (f"Errors", len(errors), "#ef4444"),
        ]:
            card = QFrame()
            card.setFixedHeight(70)
            card.setStyleSheet("background: white; border-radius: 8px; border: 1px solid #e5e7eb;")
            cl = QHBoxLayout(card)
            cl.setContentsMargins(12, 0, 12, 0)
            v = QLabel(str(val))
            v.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
            l = QLabel(label)
            l.setStyleSheet("font-size: 12px; color: #9ca3af;")
            col = QVBoxLayout()
            col.addWidget(v)
            col.addWidget(l)
            cl.addLayout(col)
            self.stats_row.addWidget(card)
        self.stats_row.addStretch()

        # Preview table
        self.preview_table.setVisible(True)
        self.preview_table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            self.preview_table.setRowHeight(i, 40)
            self.preview_table.setItem(i, 0, QTableWidgetItem(str(row["row"])))
            self.preview_table.setItem(i, 1, QTableWidgetItem(row["first_name"]))
            self.preview_table.setItem(i, 2, QTableWidgetItem(row["last_name"]))
            self.preview_table.setItem(i, 3, QTableWidgetItem(row["degree"]))
            self.preview_table.setItem(i, 4, QTableWidgetItem(row["position"]))
            self.preview_table.setItem(i, 5, QTableWidgetItem(row["join_date"]))
            self.preview_table.setItem(i, 6, QTableWidgetItem(row["base_salary"]))

            if row["status"] == "valid":
                status_item = QTableWidgetItem("✓ Valid")
                status_item.setForeground(QColor("#10b981"))
                status_item.setBackground(QColor("#dcfce7"))
            else:
                msg = ", ".join(row["issues"])
                status_item = QTableWidgetItem(f"✗ {msg}")
                status_item.setForeground(QColor("#ef4444"))
                status_item.setBackground(QColor("#fef2f2"))
                status_item.setToolTip(msg)

            self.preview_table.setItem(i, 7, status_item)

            # Row background tint
            if row["status"] == "error":
                for col in range(7):
                    item = self.preview_table.item(i, col)
                    if item:
                        item.setBackground(QColor("#fff5f5"))

        self.import_btn.setEnabled(len(valid) > 0)
        self.import_btn.setText(f"✓  Import {len(valid)} Valid Row{'s' if len(valid) != 1 else ''}")

    def _import(self):
        valid_rows = [r for r in self.preview_data if r["status"] == "valid"]
        if not valid_rows:
            return

        confirm = QMessageBox.question(self, "Confirm Import",
            f"Import {len(valid_rows)} employee records?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        session = get_session()
        imported = 0
        errors = []

        try:
            for row in valid_rows:
                try:
                    degree = row["degree"]
                    title_name = degree_to_title_name(degree)
                    title = session.query(Title).filter_by(name=title_name).first()
                    if not title:
                        errors.append(f"Row {row['row']}: Title {title_name} not found")
                        continue

                    emp_id = generate_employee_id(session)
                    join_dt = datetime.strptime(row["join_date"], "%Y-%m-%d")

                    emp = Employee(
                        employee_id=emp_id,
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        degree=degree,
                        position=row["position"],
                        join_date=join_dt,
                        base_salary=float(row["base_salary"]),
                        work_email=row.get("work_email") or None,
                        phone=row.get("phone") or None,
                        address=row.get("address") or None,
                        status="active",
                        title_id=title.id,
                    )
                    session.add(emp)
                    session.flush()
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {row['row']}: {str(e)}")

            log_action(session, self.user.id, "import.bulk_employees", "employee", None,
                description=f"Bulk CSV import: {imported} employees imported successfully")
            session.commit()
            self._set_step(2)

            msg = f"Successfully imported {imported} employee record(s)."
            if errors:
                msg += f"\n\n{len(errors)} row(s) failed:\n" + "\n".join(errors[:5])
            QMessageBox.information(self, t("import_success"), msg)

            self.preview_data = []
            self.preview_table.setVisible(False)
            self.preview_table.setRowCount(0)
            self.import_btn.setEnabled(False)
            self.import_btn.setText("✓  Import Valid Rows")
            self.file_label.setText("")
            self._set_step(0)

            while self.stats_row.count():
                item = self.stats_row.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()

    def _download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Template", "employee_import_template.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(TEMPLATE_HEADERS)
                writer.writerow([
                    "John", "Smith", "BSc", "Software Engineer",
                    "2024-01-15", "2500", "john@company.com", "+36 20 123 4567", "Budapest, Hungary"
                ])
                writer.writerow([
                    "Sarah", "Johnson", "MSc", "HR Manager",
                    "2023-06-01", "3200", "sarah@company.com", "", ""
                ])
            QMessageBox.information(self, t("success"), f"Template saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))