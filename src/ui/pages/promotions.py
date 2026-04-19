"""Promotions Page — eligible tracker, history, configurable rules."""

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QDialog, QFormLayout,
    QProgressBar, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont

from src.core.i18n import t
from src.database.connection import get_session, log_action, calculate_months_remaining
from src.database.models import Employee, Title, PromotionRule, PromotionHistory
from src.ui.styles import (
    btn_primary, btn_blue, btn_outline, btn_ghost, btn_danger,
    TABLE_SS, CARD_SS, SCROLL_SS, TAB_SS, INPUT_SS,
    BADGE_BLUE, BADGE_GREEN, BADGE_YELLOW
)

_ICO = QSize(16, 16)


class PromotionsPage(QWidget):
    def __init__(self, user, navigate_to_employee=None):
        super().__init__()
        self.user = user
        self.navigate_to_employee = navigate_to_employee
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(72)
        hdr.setStyleSheet("background: white; border-bottom: 2px solid #e5e7eb;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(32, 0, 32, 0)
        hl.setSpacing(12)
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.chart-line", color="#2563eb").pixmap(20, 20))
        title = QLabel(t("promotions_title"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
        sub = QLabel(t("promotions_subtitle"))
        sub.setStyleSheet("font-size: 13px; color: #9ca3af; margin-left: 4px;")
        hl.addWidget(ico)
        hl.addWidget(title)
        hl.addWidget(sub)
        hl.addStretch()
        layout.addWidget(hdr)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_SS)

        self.eligible_tab = EligibleTab(self.user, navigate_to_employee=self.navigate_to_employee)
        self.history_tab  = HistoryTab(self.user)
        self.rules_tab    = RulesTab(self.user)

        self.tabs.addTab(self.eligible_tab, "Eligible Employees")
        self.tabs.addTab(self.history_tab,  "Promotion History")
        self.tabs.addTab(self.rules_tab,    "Promotion Rules")
        self.tabs.currentChanged.connect(self._on_tab_change)
        layout.addWidget(self.tabs)

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Stat cards row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(16)
        layout.addLayout(self.stats_row)

        # Race explanation banner
        banner = QFrame()
        banner.setStyleSheet(
            "background: #eff6ff; border-radius: 10px; border: 1px solid #bfdbfe;"
        )
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(12)
        bico = QLabel()
        bico.setPixmap(qta.icon("fa5s.flag-checkered", color="#2563eb").pixmap(18, 18))
        btxt = QLabel(t("race_explanation"))
        btxt.setStyleSheet("font-size: 13px; color: #1e40af; background: transparent;")
        btxt.setWordWrap(True)
        bl.addWidget(bico)
        bl.addWidget(btxt, 1)
        layout.addWidget(banner)

        # Table card
        table_card = QFrame()
        table_card.setStyleSheet(CARD_SS)
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(0, 0, 0, 0)
        tcl.setSpacing(0)

        card_hdr = QFrame()
        card_hdr.setStyleSheet("background: transparent; border-bottom: 1px solid #e5e7eb;")
        chl = QHBoxLayout(card_hdr)
        chl.setContentsMargins(20, 14, 20, 14)
        ch_title = QLabel("Employee Promotion Tracker")
        ch_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #111827;")
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
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        tcl.addWidget(self.table)
        layout.addWidget(table_card)

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

                next_title_name = "—"
                if race["next_title_id"]:
                    nt = session.query(Title).filter_by(id=race["next_title_id"]).first()
                    if nt:
                        next_title_name = nt.name

                rows.append({
                    "id": emp.id,
                    "name": emp.full_name,
                    "emp_id": emp.employee_id,
                    "current": emp.title.name if emp.title else "—",
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

        # Stat cards
        for label, val, color, icon_name, bg in [
            (t("eligible_now"),  eligible_count, "#10b981", "fa5s.check-circle", "#dcfce7"),
            (t("eligible_soon"), soon_count,     "#f59e0b", "fa5s.clock",        "#fef9c3"),
            (t("in_progress"),   progress_count, "#2563eb", "fa5s.chart-line",   "#dbeafe"),
        ]:
            card = QFrame()
            card.setStyleSheet(CARD_SS)
            card.setFixedHeight(80)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(16, 0, 16, 0)
            cl.setSpacing(14)
            ico_box = QLabel()
            ico_box.setFixedSize(44, 44)
            ico_box.setAlignment(Qt.AlignCenter)
            ico_box.setStyleSheet(f"background: {bg}; border-radius: 10px;")
            ico_box.setPixmap(qta.icon(icon_name, color=color).pixmap(20, 20))
            txt = QVBoxLayout()
            txt.setSpacing(0)
            vl = QLabel(str(val))
            vl.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
            ll = QLabel(label)
            ll.setStyleSheet("font-size: 12px; color: #6b7280;")
            txt.addWidget(vl)
            txt.addWidget(ll)
            cl.addWidget(ico_box)
            cl.addLayout(txt)
            cl.addStretch()
            self.stats_row.addWidget(card)
        self.stats_row.addStretch()

        # Populate table
        self.table.setRowCount(len(rows))
        for ri, row in enumerate(rows):
            self.table.setRowHeight(ri, 56)

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
            self.table.setItem(ri, 3, QTableWidgetItem(f"{row['elapsed']} mo"))
            self.table.setItem(ri, 4, QTableWidgetItem(f"−{row['comm']} mo"))
            self.table.setItem(ri, 5, QTableWidgetItem(f"+{row['sanction']} mo"))

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
            if mr == 0:
                lbl_txt = "✓ Eligible now"
                lbl_color = "#10b981"
            elif mr <= 6:
                lbl_txt = f"{mr} months left"
                lbl_color = "#f59e0b"
            else:
                lbl_txt = f"{mr} months left"
                lbl_color = "#6b7280"
            p_lbl = QLabel(lbl_txt)
            p_lbl.setStyleSheet(f"font-size: 11px; color: {lbl_color};")
            prog_l.addWidget(p_lbl)
            self.table.setCellWidget(ri, 6, prog_w)

            # Action button
            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(8, 8, 8, 8)
            if row["status"] == "eligible":
                btn = QPushButton("  Approve")
                btn.setIcon(qta.icon("fa5s.check", color="white"))
                btn.setIconSize(QSize(13, 13))
                btn.setStyleSheet(btn_blue(32))
                btn.clicked.connect(lambda _, eid=row["id"]: self._approve_promotion(eid))
            else:
                btn = QPushButton("  View")
                btn.setIcon(qta.icon("fa5s.eye", color="#374151"))
                btn.setIconSize(QSize(13, 13))
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
        return item

    def _approve_promotion(self, employee_id):
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_id).first()
            race = calculate_months_remaining(emp, session)
            if not race["eligible"]:
                QMessageBox.warning(self, t("warning"), "Employee is not yet eligible.")
                return
            next_title = session.query(Title).filter_by(id=race["next_title_id"]).first()
            old_title  = emp.title
            confirm = QMessageBox.question(
                self, "Confirm Promotion",
                f"Promote {emp.full_name}\nfrom {old_title.name} → {next_title.name}?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
            emp.title_id = next_title.id
            from src.database.models import PromotionHistory
            history = PromotionHistory(
                employee_id=emp.id,
                from_title_id=old_title.id,
                to_title_id=next_title.id,
                approved_by_id=self.user.id,
                basis="accelerated" if race["commendation_reduction"] > 0 else "time_based",
                months_taken=race["months_elapsed"],
                notes=f"Commendation: −{race['commendation_reduction']}mo, Sanction: +{race['sanction_addition']}mo",
            )
            session.add(history)
            log_action(session, self.user.id, "promotion.approve", "employee", emp.id,
                description=f"Promoted {emp.full_name}: {old_title.name} → {next_title.name}",
                before_value=f'{{"title": "{old_title.name}"}}',
                after_value=f'{{"title": "{next_title.name}"}}',
            )
            session.commit()
            QMessageBox.information(self, t("success"),
                f"{emp.full_name} promoted to {next_title.name}!")
            self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
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
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(CARD_SS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        ch = QFrame()
        ch.setStyleSheet("background: transparent; border-bottom: 1px solid #e5e7eb;")
        chl = QHBoxLayout(ch)
        chl.setContentsMargins(20, 14, 20, 14)
        chl.addWidget(QLabel("Recent Promotions") if False else
                       _bold_label("Recent Promotions"))
        cl.addWidget(ch)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Employee", "Promotion", "Basis", "Months Taken", "Approved By", "Date"
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        cl.addWidget(self.table)
        layout.addWidget(card)

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
                "months": str(h.months_taken) + " mo" if h.months_taken else "—",
                "by": h.approved_by.full_name,
                "date": h.promoted_at.strftime("%Y-%m-%d") if h.promoted_at else "—",
            } for h in history]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
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

            self.table.setItem(i, 2, QTableWidgetItem(row["basis"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["months"]))
            self.table.setItem(i, 4, QTableWidgetItem(row["by"]))
            self.table.setItem(i, 5, QTableWidgetItem(row["date"]))


# ── Rules Tab ─────────────────────────────────────────────────────────────────
class RulesTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Race explanation card
        info = QFrame()
        info.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #eff6ff,stop:1 #f5f3ff);"
            " border-radius: 10px; border: 1px solid #bfdbfe;"
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
        rules_txt = (
            "• Each level has a base track duration in months\n"
            "• Employees advance 1 checkpoint/month automatically\n"
            "• Commendations speed up the race (Cat1: −1mo, Cat2: −3mo, Cat3: −6mo)\n"
            "• Sanctions delay the race (+1 to +12 months)\n"
            "• After promotion the clock resets to zero — no carryover"
        )
        ib = QLabel(rules_txt)
        ib.setStyleSheet("font-size: 13px; color: #1e40af; background: transparent;")
        il.addWidget(ib)
        layout.addWidget(info)

        # Table card
        card = QFrame()
        card.setStyleSheet(CARD_SS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        ch = QFrame()
        ch.setStyleSheet("background: transparent; border-bottom: 1px solid #e5e7eb;")
        chl = QHBoxLayout(ch)
        chl.setContentsMargins(20, 14, 20, 14)
        chl.addWidget(_bold_label("Promotion Track Configuration"))
        chl.addStretch()
        cl.addWidget(ch)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Level Transition", "Base Duration (months)",
            "Salary Increase on Promotion", "Actions"
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 90)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        cl.addWidget(self.table)
        layout.addWidget(card)

    def refresh(self):
        session = get_session()
        try:
            rules = session.query(PromotionRule).all()
            rows = [{
                "id": r.id,
                "transition": f"{r.from_title.name}  →  {r.to_title.name}",
                "base_months": r.base_months,
                "salary_increase": f"{r.to_title.promotion_salary_increase_pct}%",
            } for r in rules]
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 52)

            tr_w = QWidget()
            trl = QHBoxLayout(tr_w)
            trl.setContentsMargins(12, 0, 4, 0)
            trl.setSpacing(8)
            ico2 = QLabel()
            ico2.setPixmap(qta.icon("fa5s.chart-line", color="#2563eb").pixmap(14, 14))
            trl.addWidget(ico2)
            tl2 = QLabel(row["transition"])
            tl2.setStyleSheet("font-size: 13px; font-weight: 600; color: #111827;")
            trl.addWidget(tl2)
            trl.addStretch()
            self.table.setCellWidget(i, 0, tr_w)

            self.table.setItem(i, 1, QTableWidgetItem(f"{row['base_months']} months"))
            self.table.setItem(i, 2, QTableWidgetItem(row["salary_increase"]))

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet(
                "QPushButton { background: #eff6ff; color: #2563eb; border: none;"
                " border-radius: 6px; font-size: 12px; font-weight: 600; margin: 10px; }"
                " QPushButton:hover { background: #dbeafe; }"
            )
            edit_btn.clicked.connect(lambda _, rid=row["id"]: self._edit_rule(rid))
            self.table.setCellWidget(i, 3, edit_btn)

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
        self.setFixedWidth(440)
        self.setStyleSheet("background: white; color: #111827;")
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

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Base Track Duration (months) *", self.months_spin)
        layout.addLayout(form)

        note = QLabel("Commendations and sanctions are optional modifiers on top of this base duration.")
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
                self.transition_lbl.setText(f"{rule.from_title.name} → {rule.to_title.name}")
                self.months_spin.setValue(rule.base_months)
        finally:
            session.close()

    def _save(self):
        session = get_session()
        try:
            rule = session.query(PromotionRule).filter_by(id=self.rule_id).first()
            old = rule.base_months
            rule.base_months = self.months_spin.value()
            log_action(session, self.user.id, "promotion_rule.update", "promotion_rule", self.rule_id,
                description=f"Rule updated: {old} → {rule.base_months} months",
                before_value=f'{{"base_months": {old}}}',
                after_value=f'{{"base_months": {rule.base_months}}}',
            )
            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, t("error"), str(e))
        finally:
            session.close()


def _bold_label(text, size=15):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: {size}px; font-weight: 600; color: #111827;")
    return lbl
