"""Promotions Page - eligible tracker, history, configurable rules."""

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QDialog, QFormLayout,
    QProgressBar, QMessageBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import get_session, log_action, calculate_months_remaining
from src.database.models import Employee, Title, PromotionRule, PromotionHistory
from src.ui.styles import (
    btn_primary, btn_outline, INPUT_SS
)

_ICO = QSize(16, 16)

PROMO_TABLE_SS = """
QTableWidget {
    background: white;
    border: none;
    gridline-color: #f3f4f6;
    font-size: 14px;
    color: #111827;
    outline: none;
}
QTableWidget::item {
    padding: 0 12px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
}
QTableWidget::item:selected { background: #eff6ff; color: #111827; }
QHeaderView::section {
    background: white;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 700;
    color: #111827;
    min-height: 50px;
    text-align: left;
}
"""

PROMO_CARD_SS = """
QFrame#PromoCard {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
QFrame#PromoCard QLabel {
    border: none;
    background: transparent;
}
"""

PROMO_TAB_SS = """
QTabWidget::pane { border: none; background: #f9fafb; margin-top: 24px; }
QTabBar { background: #e5e7eb; border-radius: 14px; }
QTabBar::tab {
    background: transparent;
    color: #111827;
    padding: 9px 14px;
    border: none;
    font-size: 14px;
    font-weight: 700;
    min-height: 24px;
}
QTabBar::tab:first { border-top-left-radius: 14px; border-bottom-left-radius: 14px; }
QTabBar::tab:last { border-top-right-radius: 14px; border-bottom-right-radius: 14px; }
QTabBar::tab:selected { background: white; color: #030213; }
"""

MESSAGE_BOX_SS = """
QMessageBox { background: white; color: #111827; }
QMessageBox QLabel { color: #111827; background: transparent; font-size: 13px; }
QPushButton {
    background: white;
    color: #111827;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    min-width: 84px;
    min-height: 30px;
    font-weight: 600;
}
QPushButton:hover { background: #f3f4f6; }
QPushButton:default {
    background: #030213;
    color: white;
    border: none;
}
"""


class PromotionsPage(QWidget):
    def __init__(self, user, navigate_to_employee=None):
        super().__init__()
        self.user = user
        self.navigate_to_employee = navigate_to_employee
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel("Promotion Management")
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel("Manage promotion rules and track employee eligibility")
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(PROMO_TAB_SS)

        self.eligible_tab = EligibleTab(self.user, navigate_to_employee=self.navigate_to_employee)
        self.history_tab  = HistoryTab(self.user)
        self.rules_tab    = RulesTab(self.user)

        self.tabs.addTab(self.eligible_tab, "Eligible Employees")
        self.tabs.addTab(self.history_tab,  "Promotion History")
        self.tabs.addTab(self.rules_tab,    "Promotion Rules")
        self.tabs.currentChanged.connect(self._on_tab_change)
        layout.addWidget(self.tabs, 1)

    def _on_tab_change(self, index):
        if index == 0: self.eligible_tab.refresh()
        elif index == 1: self.history_tab.refresh()
        elif index == 2: self.rules_tab.refresh()

    def showEvent(self, event):
        self.eligible_tab.refresh()
        super().showEvent(event)


# ── Eligible Tab ──────────────────────────────────────────────────────────────
class EligibleTab(QWidget):
    def __init__(self, user, navigate_to_employee=None):
        super().__init__()
        self.user = user
        self.navigate_to_employee = navigate_to_employee
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("border: none; background: #f9fafb;")
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        # Stat cards row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(16)
        layout.addLayout(self.stats_row)

        # Race explanation banner
        banner = QFrame()
        banner.setObjectName("PromoBanner")
        banner.setStyleSheet(
            "QFrame#PromoBanner { background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe; }"
            "QFrame#PromoBanner QLabel { background: transparent; border: none; }"
        )
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(12)
        bico = QLabel()
        bico.setPixmap(qta.icon("fa5s.info-circle", color="#2563eb").pixmap(18, 18))
        btxt = QLabel("Showing employees who are eligible now or within 6 months of eligibility.")
        btxt.setStyleSheet("font-size: 14px; color: #1e40af; background: transparent;")
        btxt.setWordWrap(True)
        bl.addWidget(bico)
        bl.addWidget(btxt, 1)
        layout.addWidget(banner)

        # Table card
        table_card = QFrame()
        table_card.setObjectName("PromoCard")
        table_card.setStyleSheet(PROMO_CARD_SS)
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(0, 0, 0, 0)
        tcl.setSpacing(0)

        card_hdr = QFrame()
        card_hdr.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #e5e7eb;")
        chl = QHBoxLayout(card_hdr)
        chl.setContentsMargins(32, 28, 32, 28)
        ch_title = QLabel("Employee Promotion Tracker")
        ch_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827;")
        chl.addWidget(ch_title)
        chl.addStretch()
        tcl.addWidget(card_hdr)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Employee", "Current Level", "Next Level",
            "Months Elapsed", "Commendation", "Sanction",
            "Months Left", "Actions"
        ])
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setStyleSheet(PROMO_TABLE_SS)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for col, width in {
            0: 190, 1: 116, 2: 104, 3: 132,
            4: 130, 5: 112, 6: 178, 7: 150,
        }.items():
            self.table.setColumnWidth(col, width)
        for col in (0, 6):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        for col in (1, 2, 3, 4, 5, 7):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tcl.addWidget(self.table, 1)
        layout.addWidget(table_card)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def refresh(self):
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        session = get_session()
        try:
            employees = session.query(Employee).filter_by(status="active").all()
            rows = []
            eligible_count = soon_count = progress_count = 0

            for emp in employees:
                race = calculate_months_remaining(emp, session)
                if not race["has_next_level"]:
                    continue
                mr = race["months_remaining"]
                if mr == 0:
                    status = "eligible"; eligible_count += 1
                elif mr <= 6:
                    status = "soon"; soon_count += 1
                else:
                    status = "progress"; progress_count += 1

                next_title_name = "-"
                if race["next_title_id"]:
                    nt = session.query(Title).filter_by(id=race["next_title_id"]).first()
                    if nt:
                        next_title_name = nt.name

                if status in ("eligible", "soon"):
                    rows.append({
                        "id": emp.id,
                        "name": emp.full_name,
                        "emp_id": emp.employee_id,
                        "current": emp.title.name if emp.title else "-",
                        "next": next_title_name,
                        "elapsed": race["months_elapsed"],
                        "comm": race["commendation_reduction"],
                        "sanction": race["sanction_addition"],
                        "mr": mr,
                        "status": status,
                        "base_months": race.get("base_months", 36),
                    })
        finally:
            session.close()

        rows.sort(key=lambda row: (0 if row["status"] == "eligible" else 1, row["mr"], row["name"]))

        # Stat cards
        for label, val, color, icon_name, bg in [
            (t("eligible_now"),  eligible_count, "#10b981", "fa5s.check-circle", "#dcfce7"),
            (t("eligible_soon"), soon_count,     "#f59e0b", "fa5s.clock",        "#fef3c7"),
            (t("in_progress"),   progress_count, "#2563eb", "fa5s.chart-line",   "#dbeafe"),
        ]:
            card = QFrame()
            card.setObjectName("PromoCard")
            card.setStyleSheet(PROMO_CARD_SS)
            card.setFixedHeight(96)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(22, 0, 22, 0)
            cl.setSpacing(14)
            ico_box = QLabel()
            ico_box.setFixedSize(48, 48)
            ico_box.setAlignment(Qt.AlignCenter)
            ico_box.setStyleSheet(f"background: {bg}; border-radius: 8px;")
            ico_box.setPixmap(qta.icon(icon_name, color=color).pixmap(22, 22))
            txt = QVBoxLayout()
            txt.setSpacing(2)
            ll = QLabel(label)
            ll.setStyleSheet("font-size: 14px; color: #374151;")
            vl = QLabel(str(val))
            vl.setStyleSheet("font-size: 24px; font-weight: 800; color: #111827;")
            txt.addWidget(ll)
            txt.addWidget(vl)
            cl.addWidget(ico_box)
            cl.addLayout(txt)
            cl.addStretch()
            self.stats_row.addWidget(card)
        self.stats_row.addStretch()

        # Populate table
        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(112 + (64 * max(1, len(rows))))
        for ri, row in enumerate(rows):
            self.table.setRowHeight(ri, 64)

            # Employee name + ID
            name_w = QWidget()
            nl = QVBoxLayout(name_w)
            nl.setContentsMargins(12, 4, 4, 4)
            nl.setSpacing(1)
            n1 = QLabel(row["name"])
            n1.setStyleSheet("font-size: 13px; font-weight: 600; color: #111827;")
            n2 = QLabel(row["emp_id"])
            n2.setStyleSheet("font-size: 11px; color: #6b7280;")
            nl.addWidget(n1)
            nl.addWidget(n2)
            self.table.setCellWidget(ri, 0, name_w)

            self.table.setItem(ri, 1, self._badge_item(row["current"], "#dbeafe", "#1e40af"))
            self.table.setItem(ri, 2, self._badge_item(row["next"], "#dcfce7", "#166534"))
            self._set_text_item(ri, 3, f"{row['elapsed']} mo")
            self._set_text_item(ri, 4, f"-{row['comm']} mo")
            self._set_text_item(ri, 5, f"+{row['sanction']} mo")

            # Progress cell
            mr = row["mr"]
            bm = max(row["base_months"], 1)
            pct = max(0, min(100, int(100 - (mr / bm * 100))))
            prog_w = QWidget()
            prog_l = QVBoxLayout(prog_w)
            prog_l.setContentsMargins(12, 8, 12, 8)
            prog_l.setSpacing(3)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(pct)
            bar.setFixedHeight(8)
            bar.setTextVisible(False)
            if mr == 0:
                bar_color = "#10b981"
            elif mr <= 6:
                bar_color = "#f59e0b"
            else:
                bar_color = "#3b82f6"
            bar.setStyleSheet(
                f"QProgressBar {{ background: #e5e7eb; border-radius: 4px; border: none; }}"
                f" QProgressBar::chunk {{ background: {bar_color}; border-radius: 4px; }}"
            )
            prog_l.addWidget(bar)
            status_row = QHBoxLayout()
            status_row.setContentsMargins(0, 0, 0, 0)
            status_row.setSpacing(6)
            status_icon = QLabel()
            status_icon.setFixedSize(14, 14)
            if mr == 0:
                lbl_txt = "Eligible now"
                lbl_color = "#10b981"
                status_icon.setPixmap(qta.icon("fa5s.check-circle", color=lbl_color).pixmap(13, 13))
            elif mr <= 6:
                lbl_txt = f"{mr} months left"
                lbl_color = "#f59e0b"
                status_icon.setPixmap(qta.icon("fa5s.clock", color=lbl_color).pixmap(13, 13))
            else:
                lbl_txt = f"{mr} months left"
                lbl_color = "#6b7280"
                status_icon.setPixmap(qta.icon("fa5s.chart-line", color=lbl_color).pixmap(13, 13))
            p_lbl = QLabel(lbl_txt)
            p_lbl.setStyleSheet(f"font-size: 12px; color: {lbl_color};")
            status_row.addWidget(status_icon)
            status_row.addWidget(p_lbl)
            status_row.addStretch()
            prog_l.addLayout(status_row)
            self.table.setCellWidget(ri, 6, prog_w)

            # Action button
            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(6, 8, 6, 8)
            act_l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if row["status"] == "eligible":
                btn = QPushButton("  Approve")
                btn.setIcon(qta.icon("fa5s.check", color="white"))
                btn.setIconSize(QSize(13, 13))
                btn.setFixedSize(112, 40)
                btn.setStyleSheet(btn_primary(40))
                btn.clicked.connect(lambda _, eid=row["id"]: self._approve_promotion(eid))
            else:
                btn = QPushButton("  View")
                btn.setIcon(qta.icon("fa5s.eye", color="#374151"))
                btn.setIconSize(QSize(13, 13))
                btn.setFixedSize(96, 40)
                btn.setStyleSheet(btn_outline(32))
                if self.navigate_to_employee:
                    btn.clicked.connect(lambda _, eid=row["id"]: self.navigate_to_employee(eid))
                else:
                    btn.setEnabled(False)
            act_l.addWidget(btn)
            self.table.setCellWidget(ri, 7, act_w)

    def _badge_item(self, text, bg, fg):
        item = QTableWidgetItem(text)
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return item

    def _set_text_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, col, item)

    def _approve_promotion(self, employee_id):
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_id).first()
            race = calculate_months_remaining(emp, session)
            if not race["eligible"]:
                _warning(self, t("warning"), "Employee is not yet eligible.")
                return
            next_title = session.query(Title).filter_by(id=race["next_title_id"]).first()
            old_title  = emp.title
            salary_before = emp.base_salary
            salary_pct = next_title.promotion_salary_increase_pct if next_title else 0
            salary_after = round(salary_before * (1 + salary_pct / 100), 2)
            confirm = _question(
                self, "Confirm Promotion",
                f"Promote {emp.full_name}\nfrom {old_title.name} to {next_title.name}?\n\n"
                f"Salary increase: {salary_pct:.1f}%\n"
                f"Base salary: EUR {salary_before:,.2f} to EUR {salary_after:,.2f}",
            )
            if confirm != QMessageBox.Yes:
                return
            emp.title_id = next_title.id
            emp.base_salary = salary_after
            from src.database.models import PromotionHistory
            history = PromotionHistory(
                employee_id=emp.id,
                from_title_id=old_title.id,
                to_title_id=next_title.id,
                approved_by_id=self.user.id,
                basis="accelerated" if race["commendation_reduction"] > 0 else "time_based",
                months_taken=race["months_elapsed"],
                notes=f"Commendation: -{race['commendation_reduction']}mo, Sanction: +{race['sanction_addition']}mo",
            )
            session.add(history)
            log_action(
                session, action="promotion.approve", performed_by_id=self.user.id,
                target_table="employee", target_id=emp.id,
                description=f"Promoted {emp.full_name}: {old_title.name} to {next_title.name}; salary +{salary_pct:.1f}%",
                before_value=f'{{"title": "{old_title.name}", "base_salary": {salary_before}}}',
                after_value=f'{{"title": "{next_title.name}", "base_salary": {salary_after}}}',
            )
            session.commit()
            _information(self, t("success"),
                f"{emp.full_name} promoted to {next_title.name}!")
            self.refresh()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()


# ── History Tab ───────────────────────────────────────────────────────────────
class HistoryTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("PromoCard")
        card.setStyleSheet(PROMO_CARD_SS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        ch = QFrame()
        ch.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #e5e7eb;")
        chl = QHBoxLayout(ch)
        chl.setContentsMargins(32, 28, 32, 28)
        chl.addWidget(QLabel("Recent Promotions") if False else
                       _bold_label("Recent Promotions", size=20, weight=800))
        cl.addWidget(ch)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Employee", "Promotion", "Basis", "Months Taken", "Approved By", "Date"
        ])
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setStyleSheet(PROMO_TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cl.addWidget(self.table)
        layout.addWidget(card)
        layout.addStretch()

    def refresh(self):
        session = get_session()
        try:
            history = session.query(PromotionHistory).order_by(
                PromotionHistory.promoted_at.desc()
            ).all()
            rows = [{
                "name": h.employee.full_name, "emp_id": h.employee.employee_id,
                "from": h.from_title.name, "to": h.to_title.name,
                "basis": h.basis.replace("_", " ").title(),
                "months": str(h.months_taken) + " mo" if h.months_taken else "-",
                "by": h.approved_by.full_name,
                "date": h.promoted_at.strftime("%Y-%m-%d") if h.promoted_at else "-",
            } for h in history]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(112 + (56 * max(1, len(rows))))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 52)
            # Employee cell
            ew = QWidget()
            el = QVBoxLayout(ew)
            el.setContentsMargins(12, 4, 4, 4)
            el.setSpacing(1)
            e1 = QLabel(row["name"])
            e1.setStyleSheet("font-size: 13px; font-weight: 600; color: #111827;")
            e2 = QLabel(row["emp_id"])
            e2.setStyleSheet("font-size: 11px; color: #6b7280;")
            el.addWidget(e1); el.addWidget(e2)
            self.table.setCellWidget(i, 0, ew)

            promo_w = QWidget()
            pl = QHBoxLayout(promo_w)
            pl.setContentsMargins(12, 0, 4, 0)
            pl.setSpacing(8)
            fl = QLabel(row["from"])
            fl.setStyleSheet(f"background: #f3f4f6; color: #374151; border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: 600;")
            arrow = QLabel()
            arrow.setPixmap(qta.icon("fa5s.arrow-right", color="#10b981").pixmap(12, 12))
            tl = QLabel(row["to"])
            tl.setStyleSheet(f"background: #dcfce7; color: #166534; border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: 600;")
            pl.addWidget(fl); pl.addWidget(arrow); pl.addWidget(tl); pl.addStretch()
            self.table.setCellWidget(i, 1, promo_w)

            _set_table_item(self.table, i, 2, row["basis"])
            _set_table_item(self.table, i, 3, row["months"])
            _set_table_item(self.table, i, 4, row["by"])
            _set_table_item(self.table, i, 5, row["date"])


# ── Rules Tab ─────────────────────────────────────────────────────────────────
class RulesTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: #f9fafb;")
        content = QWidget()
        content.setStyleSheet("background: #f9fafb;")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        # Race explanation card
        info = QFrame()
        info.setObjectName("PromoInfo")
        info.setStyleSheet(
            "QFrame#PromoInfo { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #eff6ff,stop:1 #f5f3ff);"
            " border-radius: 8px; border: 1px solid #bfdbfe; }"
            "QFrame#PromoInfo QLabel { background: transparent; border: none; }"
        )
        il = QVBoxLayout(info)
        il.setContentsMargins(20, 16, 20, 16)
        il.setSpacing(6)
        ih = QHBoxLayout()
        ih.setSpacing(10)
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.chart-line", color="#2563eb").pixmap(18, 18))
        it = QLabel("How the Promotion Race Works")
        it.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e40af;")
        ih.addWidget(ico); ih.addWidget(it); ih.addStretch()
        il.addLayout(ih)
        il.addWidget(_guide_line("1", "Base duration", "Every level has a configurable track duration in months.", "#2563eb"))
        il.addWidget(_guide_line("2", "Monthly progress", "Employees move forward 1 checkpoint each month automatically.", "#2563eb"))
        il.addWidget(_guide_line("3", "Commendations", "Awards reduce months remaining. Cat1: 1 month, Cat2: 3 months, Cat3: 6 months.", "#10b981"))
        il.addWidget(_guide_line("4", "Sanctions", "Active sanctions add delay months to the promotion timeline.", "#f59e0b"))
        il.addWidget(_guide_line("5", "Reset after promotion", "When promoted, the next race starts from month 0 on the promotion date.", "#7e22ce"))
        layout.addWidget(info)

        # Table card
        card = QFrame()
        card.setObjectName("PromoCard")
        card.setStyleSheet(PROMO_CARD_SS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        ch = QFrame()
        ch.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #e5e7eb;")
        chl = QHBoxLayout(ch)
        chl.setContentsMargins(32, 28, 32, 28)
        header_text = QVBoxLayout()
        header_text.setSpacing(6)
        header_text.addWidget(_bold_label("Promotion Track Configuration", size=20, weight=800))
        sub = QLabel("Configure the promotion race timeline and salary bump for each level")
        sub.setStyleSheet("font-size: 14px; color: #4b5563; background: transparent;")
        header_text.addWidget(sub)
        chl.addLayout(header_text)
        chl.addStretch()
        cl.addWidget(ch)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Level Transition", "Base Duration (months)",
            "Salary Increase on Promotion", "Actions"
        ])
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setStyleSheet(PROMO_TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cl.addWidget(self.table)
        layout.addWidget(card)
        layout.addWidget(self._modifier_card())
        layout.addWidget(self._reset_policy_card())
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def refresh(self):
        session = get_session()
        try:
            rules = session.query(PromotionRule).all()
            rows = [{
                "id": r.id,
                "from": r.from_title.name,
                "to": r.to_title.name,
                "base_months": r.base_months,
                "salary_increase": f"{r.to_title.promotion_salary_increase_pct}%",
            } for r in rules]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(112 + (56 * max(1, len(rows))))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 52)

            tr_w = QWidget()
            trl = QHBoxLayout(tr_w)
            trl.setContentsMargins(12, 0, 4, 0)
            trl.setSpacing(8)
            ico2 = QLabel()
            ico2.setPixmap(qta.icon("fa5s.chart-line", color="#2563eb").pixmap(14, 14))
            trl.addWidget(ico2)
            from_lbl = _level_badge(row["from"], "#f3f4f6", "#374151")
            arrow = QLabel()
            arrow.setPixmap(qta.icon("fa5s.arrow-right", color="#10b981").pixmap(12, 12))
            to_lbl = _level_badge(row["to"], "#dcfce7", "#166534")
            trl.addWidget(from_lbl)
            trl.addWidget(arrow)
            trl.addWidget(to_lbl)
            trl.addStretch()
            self.table.setCellWidget(i, 0, tr_w)

            _set_table_item(self.table, i, 1, f"{row['base_months']} months")
            _set_table_item(self.table, i, 2, row["salary_increase"])

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet(
                "QPushButton { background: #eff6ff; color: #2563eb; border: none;"
                " border-radius: 6px; font-size: 12px; font-weight: 600; margin: 10px; }"
                " QPushButton:hover { background: #dbeafe; }"
            )
            edit_btn.clicked.connect(lambda _, rid=row["id"]: self._edit_rule(rid))
            self.table.setCellWidget(i, 3, edit_btn)

    def _modifier_card(self):
        card = QFrame()
        card.setStyleSheet("QFrame { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; } QLabel { background: transparent; border: none; }")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.clock", color="#f59e0b").pixmap(20, 20))
        layout.addWidget(icon, alignment=Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(8)
        title = QLabel("Track Modifiers (Optional)")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #92400e;")
        text.addWidget(title)
        text.addWidget(_mini_line("fa5s.award", "Commendations reduce the months remaining in the current race.", "#92400e"))
        text.addWidget(_mini_line("fa5s.exclamation-triangle", "Sanctions add delay months to the promotion timeline.", "#92400e"))
        text.addWidget(_mini_line("fa5s.cog", "Configure awards and sanction impacts on their own pages.", "#92400e"))
        layout.addLayout(text, 1)
        return card

    def _reset_policy_card(self):
        card = QFrame()
        card.setStyleSheet("QFrame { background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 8px; } QLabel { background: transparent; border: none; }")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.chart-line", color="#7e22ce").pixmap(20, 20))
        layout.addWidget(icon, alignment=Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(8)
        title = QLabel("Reset Policy")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #6b21a8;")
        body = QLabel("After a promotion, the employee starts a new race from month 0. The timer for the next promotion begins from the promotion date.")
        body.setWordWrap(True)
        body.setStyleSheet("font-size: 14px; color: #6b21a8;")
        text.addWidget(title)
        text.addWidget(body)
        layout.addLayout(text, 1)
        return card

    def _edit_rule(self, rule_id):
        dialog = RuleEditDialog(self.user, rule_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()


class RuleEditDialog(QDialog):
    def __init__(self, user, rule_id, parent=None):
        super().__init__(parent)
        self.user = user
        self.rule_id = rule_id
        self.setWindowTitle("Edit Promotion Rule")
        self.setFixedWidth(520)
        self.setStyleSheet("QDialog { background: white; color: #111827; } QLabel { background: transparent; color: #111827; }")
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        layout.addWidget(_bold_label("Edit Promotion Rule", size=17))

        self.transition_lbl = QLabel("")
        self.transition_lbl.setStyleSheet("font-size: 14px; color: #2563eb; font-weight: 600;")
        layout.addWidget(self.transition_lbl)

        self.months_spin = QSpinBox()
        self.months_spin.setRange(1, 120)
        self.months_spin.setStyleSheet(INPUT_SS)
        self.months_spin.setFixedHeight(42)

        self.salary_spin = QDoubleSpinBox()
        self.salary_spin.setRange(0.0, 100.0)
        self.salary_spin.setDecimals(1)
        self.salary_spin.setSingleStep(0.5)
        self.salary_spin.setSuffix("%")
        self.salary_spin.setStyleSheet(INPUT_SS)
        self.salary_spin.setFixedHeight(42)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.addRow("Base Track Duration (months) *", self.months_spin)
        form.addRow("Salary Increase on Promotion *", self.salary_spin)
        layout.addLayout(form)

        note = QLabel("Commendations and sanctions modify the race duration. The salary increase is applied to the employee base salary when this promotion is approved.")
        note.setStyleSheet("font-size: 12px; color: #9ca3af;")
        note.setWordWrap(True)
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(t("cancel"))
        cancel.setFixedHeight(36)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(btn_outline(36))
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("save"))
        save.setFixedHeight(36)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(btn_primary(36))
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _load(self):
        session = get_session()
        try:
            rule = session.query(PromotionRule).filter_by(id=self.rule_id).first()
            if rule:
                self.transition_lbl.setText(f"{rule.from_title.name} to {rule.to_title.name}")
                self.months_spin.setValue(rule.base_months)
                self.salary_spin.setValue(rule.to_title.promotion_salary_increase_pct)
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            rule = session.query(PromotionRule).filter_by(id=self.rule_id).first()
            old_months = rule.base_months
            old_salary = rule.to_title.promotion_salary_increase_pct
            rule.base_months = self.months_spin.value()
            rule.to_title.promotion_salary_increase_pct = self.salary_spin.value()
            log_action(
                session, action="promotion_rule.update", performed_by_id=self.user.id,
                target_table="promotion_rule", target_id=self.rule_id,
                description=f"Rule updated: {old_months} to {rule.base_months} months; salary {old_salary:.1f}% to {rule.to_title.promotion_salary_increase_pct:.1f}%",
                before_value=f'{{"base_months": {old_months}, "salary_increase_pct": {old_salary}}}',
                after_value=f'{{"base_months": {rule.base_months}, "salary_increase_pct": {rule.to_title.promotion_salary_increase_pct}}}',
            )
            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()


def _set_table_item(table, row, col, text):
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    table.setItem(row, col, item)


def _level_badge(text, bg, fg):
    label = QLabel(text)
    label.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 7px; padding: 4px 10px; font-size: 12px; font-weight: 700;")
    return label


def _guide_line(number, title, body, color):
    row = QWidget()
    row.setStyleSheet("background: transparent; border: none;")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 3, 0, 3)
    layout.setSpacing(10)
    badge = QLabel(number)
    badge.setFixedSize(22, 22)
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(f"background: white; color: {color}; border: 1px solid #bfdbfe; border-radius: 11px; font-size: 12px; font-weight: 800;")
    text = QLabel(f"<b>{title}</b>: {body}")
    text.setWordWrap(True)
    text.setStyleSheet("font-size: 13px; color: #1e40af;")
    layout.addWidget(badge, alignment=Qt.AlignTop)
    layout.addWidget(text, 1)
    return row


def _mini_line(icon_name, text, color):
    row = QWidget()
    row.setStyleSheet("background: transparent; border: none;")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    icon = QLabel()
    icon.setFixedSize(16, 16)
    icon.setPixmap(qta.icon(icon_name, color=color).pixmap(14, 14))
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"font-size: 14px; color: {color};")
    layout.addWidget(icon, alignment=Qt.AlignTop)
    layout.addWidget(label, 1)
    return row


def _styled_message_box(parent, icon, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    box.setDefaultButton(default_button)
    box.setStyleSheet(MESSAGE_BOX_SS)
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)


def _information(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Information, title, text)


def _question(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)


def _bold_label(text, size=15, weight=600):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: {size}px; font-weight: {weight}; color: #111827; background: transparent;")
    return lbl
