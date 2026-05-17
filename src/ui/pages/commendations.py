"""
Commendations Page
- Issue single or bulk (team) commendations
- 3 categories: Cat1=-1mo, Cat2=-3mo, Cat3=-6mo
- Max 3 commendations per employee per role (enforced)
- Unique auto-generated ID per commendation
- History view
"""

import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QLineEdit, QComboBox, QTextEdit,
    QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from src.core.i18n import t
from src.database.connection import (
    get_session, generate_commendation_ref, log_action,
    can_receive_commendation, count_commendations_in_current_role,
    is_other_employee
)
from src.database.models import Employee, Commendation, CommendationEmployee, SystemUser
from datetime import datetime


CATEGORIES = {
    1: {"label_key": "category_1", "months": -1, "desc_key": "category_1_desc", "color": "#10b981", "bg": "#dcfce7"},
    2: {"label_key": "category_2", "months": -3, "desc_key": "category_2_desc", "color": "#2563eb", "bg": "#eff6ff"},
    3: {"label_key": "category_3", "months": -6, "desc_key": "category_3_desc", "color": "#8b5cf6", "bg": "#f3e8ff"},
}

PAGE_BG = "#f9fafb"
TEXT = "#030213"
MUTED = "#4b5563"
BORDER = "#e5e7eb"

TAB_SS = """
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

CARD_SS = """
QFrame#Card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
QFrame#Card QLabel {
    background: transparent;
    border: none;
}
"""

INPUT_SS = """
QLineEdit, QTextEdit {
    border: none;
    border-radius: 8px;
    padding: 0 16px;
    font-size: 14px;
    color: #111827;
    background: #f3f3f5;
    selection-background-color: #2563eb;
    outline: none;
}
QTextEdit {
    padding: 10px 16px;
}
QLineEdit:focus, QTextEdit:focus {
    background: white;
    border: 1px solid #2563eb;
}
"""

COMBO_SS = """
QComboBox {
    border: none;
    border-radius: 8px;
    padding: 0 36px 0 16px;
    font-size: 14px;
    color: #111827;
    background: #f3f3f5;
    min-height: 40px;
    outline: none;
}
QComboBox:focus { border: 1px solid #2563eb; background: white; }
QComboBox::drop-down { width: 32px; border: none; background: transparent; }
QComboBox::down-arrow { image: url(src/ui/assets/chevron_down.svg); width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background: white;
    color: #111827;
    border: 1px solid #e5e7eb;
    border-radius: 0;
    selection-background-color: #eff6ff;
    selection-color: #111827;
    outline: none;
    padding: 4px;
}
"""

TABLE_SS = """
QTableWidget {
    background: white;
    alternate-background-color: white;
    border: none;
    gridline-color: #f3f4f6;
    font-size: 14px;
    color: #111827;
    outline: none;
    selection-background-color: #eff6ff;
}
QTableWidget::item {
    background: white;
    padding: 0 12px;
    border: none;
    border-bottom: 1px solid #f3f4f6;
    color: #111827;
}
QTableWidget::item:hover { background: #f9fafb; }
QTableWidget::item:selected { background: #eff6ff; color: #111827; }
QHeaderView::section {
    background: white;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 800;
    color: #030213;
    min-height: 50px;
    text-align: left;
}
QToolTip {
    background-color: #111827;
    color: white;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 6px 8px;
}
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
QPushButton:default { background: #030213; color: white; border: none; }
"""


class CommendationsPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("commendations_title"))
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #111827; background: transparent;")
        subtitle = QLabel(t("commendations_subtitle"))
        subtitle.setStyleSheet("font-size: 16px; color: #4b5563; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_SS)

        self.issue_tab   = IssueCommendationTab(self.user, self._on_issued)
        self.history_tab = CommendationHistoryTab(self.user)

        self.tabs.addTab(self.issue_tab,   t("issue_commendation"))
        self.tabs.addTab(self.history_tab, t("commendation_history"))
        self.tabs.currentChanged.connect(lambda i: self.history_tab.refresh() if i == 1 else None)
        layout.addWidget(self.tabs, 1)

    def _on_issued(self):
        self.tabs.setCurrentIndex(1)
        self.history_tab.refresh()

    def showEvent(self, event):
        self.issue_tab.refresh_employees()
        super().showEvent(event)


# Issue Commendation Tab
class IssueCommendationTab(QWidget):
    def __init__(self, user, on_issued):
        super().__init__()
        self.user = user
        self.on_issued = on_issued
        self.selected_employees = set()
        self.mode = "single"
        self.setStyleSheet("background: #f9fafb;")
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        main = QHBoxLayout(content)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(30)
        main.setAlignment(Qt.AlignTop)

        # Left form
        left = QVBoxLayout()
        left.setSpacing(16)

        # Mode selector
        mode_card = QFrame()
        mode_card.setObjectName("Card")
        mode_card.setStyleSheet(CARD_SS)
        mc = QVBoxLayout(mode_card)
        mc.setContentsMargins(30, 28, 30, 28)
        mc.setSpacing(24)
        mc_title = QLabel(t("commendation_type"))
        mc_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        mc.addWidget(mc_title)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        self.single_btn = QPushButton(t("single_employee"))
        self.single_btn.setIcon(qta.icon("fa5s.user", color="#2563eb"))
        self.single_btn.setIconSize(QSize(28, 28))
        self.single_btn.setFixedHeight(150)
        self.single_btn.setCursor(Qt.PointingHandCursor)
        self.single_btn.clicked.connect(lambda: self._set_mode("single"))

        self.bulk_btn = QPushButton(t("team_award"))
        self.bulk_btn.setIcon(qta.icon("fa5s.users", color="#6b7280"))
        self.bulk_btn.setIconSize(QSize(28, 28))
        self.bulk_btn.setFixedHeight(150)
        self.bulk_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_btn.clicked.connect(lambda: self._set_mode("bulk"))

        mode_row.addWidget(self.single_btn)
        mode_row.addWidget(self.bulk_btn)
        mc.addLayout(mode_row)
        left.addWidget(mode_card)

        # Details card
        details_card = QFrame()
        details_card.setObjectName("Card")
        details_card.setStyleSheet(CARD_SS)
        dc = QVBoxLayout(details_card)
        dc.setContentsMargins(30, 28, 30, 28)
        dc.setSpacing(16)

        dc_title = QLabel(t("commendation_details"))
        dc_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        dc.addWidget(dc_title)

        title_lbl = QLabel(t("award_title") + " *")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #030213; background: transparent;")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(t("award_title_placeholder"))
        self.title_input.setFixedHeight(44)
        self.title_input.setStyleSheet(INPUT_SS)
        dc.addWidget(title_lbl)
        dc.addWidget(self.title_input)

        cat_lbl = QLabel(t("commendation_category") + " *")
        cat_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #030213; background: transparent;")
        self.cat_combo = QComboBox()
        self.cat_combo.setFixedHeight(44)
        self.cat_combo.setStyleSheet(COMBO_SS)
        _polish_combo(self.cat_combo)
        self.cat_combo.addItem(t("select_category_tier"), None)
        for cat_id, cat in CATEGORIES.items():
            self.cat_combo.addItem(t(cat["label_key"]), cat_id)
        dc.addWidget(cat_lbl)
        dc.addWidget(self.cat_combo)
        cat_hint = QLabel(t("higher_categories_hint"))
        cat_hint.setStyleSheet("font-size: 12px; color: #64748b; background: transparent;")
        dc.addWidget(cat_hint)

        desc_lbl = QLabel(t("description") + " *")
        desc_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #030213; background: transparent;")
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(80)
        self.desc_input.setPlaceholderText(t("commendation_description_placeholder"))
        self.desc_input.setStyleSheet(INPUT_SS)
        dc.addWidget(desc_lbl)
        dc.addWidget(self.desc_input)
        left.addWidget(details_card)

        # Employee selection card
        emp_card = QFrame()
        emp_card.setObjectName("Card")
        emp_card.setStyleSheet(CARD_SS)
        ec = QVBoxLayout(emp_card)
        ec.setContentsMargins(30, 28, 30, 28)
        ec.setSpacing(14)

        self.emp_card_title = QLabel(t("select_employee"))
        self.emp_card_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        ec.addWidget(self.emp_card_title)

        # Single employee combo
        self.single_combo = QComboBox()
        self.single_combo.setFixedHeight(44)
        self.single_combo.setStyleSheet(COMBO_SS)
        _polish_combo(self.single_combo)
        ec.addWidget(self.single_combo)

        # Bulk employee checkboxes container
        self.bulk_scroll = QScrollArea()
        self.bulk_scroll.setFixedHeight(200)
        self.bulk_scroll.setWidgetResizable(True)
        self.bulk_scroll.setStyleSheet("border: none; background: transparent;")
        self.bulk_container = QWidget()
        self.bulk_container.setStyleSheet("background: white;")
        self.bulk_layout = QVBoxLayout(self.bulk_container)
        self.bulk_layout.setContentsMargins(8, 8, 8, 8)
        self.bulk_layout.setSpacing(4)
        self.bulk_scroll.setWidget(self.bulk_container)
        ec.addWidget(self.bulk_scroll)

        self.selected_count_lbl = QLabel(t("selected_count", count=0))
        self.selected_count_lbl.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        ec.addWidget(self.selected_count_lbl)
        left.addWidget(emp_card)
        main.addLayout(left, 3)

        # Right sidebar
        right = QVBoxLayout()
        right.setSpacing(16)
        right.setAlignment(Qt.AlignTop)

        # Category impact info
        impact_card = QFrame()
        impact_card.setStyleSheet("QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #eff6ff,stop:1 #f5f3ff); border-radius: 8px; border: 1px solid #bfdbfe; } QLabel { background: transparent; border: none; }")
        ic = QVBoxLayout(impact_card)
        ic.setContentsMargins(30, 28, 30, 28)
        ic.setSpacing(14)

        impact_head = QHBoxLayout()
        impact_icon = QLabel()
        impact_icon.setPixmap(qta.icon("fa5s.stopwatch", color="#2563eb").pixmap(18, 18))
        ic_title = QLabel(t("promotion_track_impact"))
        ic_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #1e40af; background: transparent;")
        impact_head.addWidget(impact_icon)
        impact_head.addWidget(ic_title)
        impact_head.addStretch()
        ic.addLayout(impact_head)
        intro = QLabel(t("commendation_impact_intro"))
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 13px; color: #1d4ed8; background: transparent;")
        ic.addWidget(intro)

        for cat_id, cat in CATEGORIES.items():
            row = QFrame()
            row.setStyleSheet(f"QFrame {{ background: white; border-radius: 7px; border: 1px solid {cat['color']}40; }} QLabel {{ background: transparent; border: none; }}")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(16, 14, 16, 14)
            top = QHBoxLayout()
            name = QLabel(t(cat["label_key"]))
            name.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {cat['color']}; background: transparent;")
            badge = QLabel(f"-{abs(cat['months'])} mo")
            badge.setText(t("negative_month_count", count=abs(cat["months"])))
            badge.setStyleSheet(f"background: {cat['bg']}; color: {cat['color']}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
            desc = QLabel(t(cat["desc_key"]))
            desc.setStyleSheet(f"font-size: 12px; color: {cat['color']}; background: transparent;")
            top.addWidget(name)
            top.addStretch()
            top.addWidget(badge)
            rl.addLayout(top)
            rl.addWidget(desc)
            ic.addWidget(row)

        right.addWidget(impact_card)

        actions_card = QFrame()
        actions_card.setObjectName("Card")
        actions_card.setStyleSheet(CARD_SS)
        ac = QVBoxLayout(actions_card)
        ac.setContentsMargins(30, 28, 30, 28)
        ac.setSpacing(16)
        actions_title = QLabel(t("actions"))
        actions_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        ac.addWidget(actions_title)
        ac.addSpacing(24)
        issue_btn = QPushButton("  " + t("issue_commendation"))
        issue_btn.setIcon(qta.icon("fa5s.award", color="white"))
        issue_btn.setIconSize(QSize(14, 14))
        issue_btn.setCursor(Qt.PointingHandCursor)
        issue_btn.setFixedHeight(50)
        issue_btn.setStyleSheet("QPushButton { background: #030213; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 800; } QPushButton:hover { background: #111827; }")
        issue_btn.clicked.connect(self._issue)
        ac.addWidget(issue_btn)
        clear_btn = QPushButton(t("clear_form"))
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedHeight(44)
        clear_btn.setStyleSheet("QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; font-weight: 700; } QPushButton:hover { background: #f3f4f6; }")
        clear_btn.clicked.connect(self._clear)
        ac.addWidget(clear_btn)
        right.insertWidget(0, actions_card)

        # Rules card
        rules_card = QFrame()
        rules_card.setStyleSheet("QFrame { background: #fefce8; border-radius: 8px; border: 1px solid #fde047; } QLabel { background: transparent; border: none; }")
        rc = QVBoxLayout(rules_card)
        rc.setContentsMargins(30, 28, 30, 28)
        rc.setSpacing(12)
        rule_head = QHBoxLayout()
        rule_icon = QLabel()
        rule_icon.setPixmap(qta.icon("fa5s.award", color="#d97706").pixmap(18, 18))
        rc_title = QLabel(t("important_rules"))
        rc_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #854d0e; background: transparent;")
        rule_head.addWidget(rule_icon)
        rule_head.addWidget(rc_title)
        rule_head.addStretch()
        rc.addLayout(rule_head)
        for rule in [
            t("commendation_rule_max"),
            t("commendation_rule_unique_id"),
            t("commendation_rule_visible"),
            t("commendation_rule_reviews"),
        ]:
            lbl = QLabel("&bull; " + rule)
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size: 14px; color: #92400e; background: transparent;")
            rc.addWidget(lbl)
        right.addWidget(rules_card)

        main.addLayout(right, 2)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._set_mode("single")
        self.checkboxes = []

    def _set_mode(self, mode):
        self.mode = mode
        active = (
            "QPushButton { background: #eff6ff; color: #2563eb; border: 2px solid #2563eb;"
            " border-radius: 8px; font-size: 17px; font-weight: 800; padding: 0 14px; }"
        )
        inactive = (
            "QPushButton { background: white; color: #111827; border: 1px solid #e5e7eb;"
            " border-radius: 8px; font-size: 17px; font-weight: 800; padding: 0 14px; }"
            "QPushButton:hover { background: #f9fafb; }"
        )
        self.single_btn.setStyleSheet(active if mode == "single" else inactive)
        self.single_btn.setIcon(qta.icon("fa5s.user", color="#2563eb" if mode == "single" else "#6b7280"))
        self.bulk_btn.setStyleSheet(active if mode == "bulk" else inactive)
        self.bulk_btn.setIcon(qta.icon("fa5s.users", color="#2563eb" if mode == "bulk" else "#6b7280"))
        self.single_combo.setVisible(mode == "single")
        self.bulk_scroll.setVisible(mode == "bulk")
        self.selected_count_lbl.setVisible(mode == "bulk")
        self.emp_card_title.setText(t("select_employee") if mode == "single" else t("select_employees"))

    def refresh_employees(self):
        session = get_session()
        try:
            emps = [
                emp for emp in session.query(Employee).filter_by(status="active").all()
                if not is_other_employee(emp)
            ]
            emp_data = [{
                "id": e.id,
                "label": f"{e.employee_id} - {e.full_name} ({e.title.name if e.title else '?'})",
                "can": can_receive_commendation(e, session),
                "count": count_commendations_in_current_role(e, session),
            } for e in emps]
        finally:
            session.close()

        self.single_combo.clear()
        self.single_combo.addItem(t("choose_employee"), None)
        for e in emp_data:
            suffix = f"  [{e['count']}/3]" + (f"  {t('max_reached')}" if not e["can"] else "")
            self.single_combo.addItem(e["label"] + suffix, e["id"] if e["can"] else None)
            item = self.single_combo.model().item(self.single_combo.count() - 1)
            if item and not e["can"]:
                item.setEnabled(False)
                item.setForeground(QColor("#9ca3af"))

        # Bulk checkboxes
        while self.bulk_layout.count():
            item = self.bulk_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.checkboxes = []
        self.selected_employees = set()

        for e in emp_data:
            cb = QCheckBox(e["label"] + f"  [{e['count']}/3 {t('commendations').lower()}]")
            cb.setStyleSheet("font-size: 12px; color: #111827; padding: 4px;")
            if not e["can"]:
                cb.setEnabled(False)
                cb.setStyleSheet("font-size: 12px; color: #9ca3af; padding: 4px;")
            cb.setProperty("emp_id", e["id"])
            cb.stateChanged.connect(self._on_checkbox_change)
            self.bulk_layout.addWidget(cb)
            self.checkboxes.append(cb)

        self.bulk_layout.addStretch()

    def _on_checkbox_change(self):
        self.selected_employees = {
            cb.property("emp_id") for cb in self.checkboxes
            if cb.isChecked() and cb.isEnabled()
        }
        self.selected_count_lbl.setText(t("selected_count", count=len(self.selected_employees)))

    def _clear(self):
        self.title_input.clear()
        self.desc_input.clear()
        self.cat_combo.setCurrentIndex(0)
        self.single_combo.setCurrentIndex(0)
        for cb in self.checkboxes:
            cb.setChecked(False)
        self.selected_employees = set()

    def _issue(self):
        title_text = self.title_input.text().strip()
        desc_text  = self.desc_input.toPlainText().strip()
        cat_id     = self.cat_combo.currentData()

        if not title_text:
            _warning(self, t("warning"), t("award_title_required"))
            return
        if not cat_id:
            _warning(self, t("warning"), t("select_commendation_category_warning"))
            return
        if not desc_text:
            _warning(self, t("warning"), t("description_required"))
            return

        if self.mode == "single":
            emp_id = self.single_combo.currentData()
            if not emp_id:
                _warning(self, t("warning"), t("please_select_employee"))
                return
            target_ids = [emp_id]
        else:
            if not self.selected_employees:
                _warning(self, t("warning"), t("please_select_at_least_one_employee"))
                return
            target_ids = list(self.selected_employees)

        cat = CATEGORIES[cat_id]

        session = get_session()
        try:
            skipped_names = []

            if self.mode == "single":
                emp = session.query(Employee).filter_by(id=target_ids[0]).first()
                if not can_receive_commendation(emp, session):
                    _warning(self, t("warning"), t("max_commendations_reached"))
                    return
            else:
                # Team award: skip maxed employees, award the rest
                eligible_ids = []
                for eid in target_ids:
                    emp = session.query(Employee).filter_by(id=eid).first()
                    if can_receive_commendation(emp, session):
                        eligible_ids.append(eid)
                    else:
                        skipped_names.append(emp.full_name)

                if not eligible_ids:
                    _warning(self, t("warning"),
                        t("all_selected_max_commendations"))
                    return
                target_ids = eligible_ids

            ref = generate_commendation_ref(session)
            comm = Commendation(
                commendation_ref=ref,
                title=title_text,
                description=desc_text,
                category=cat_id,
                months_impact=cat["months"],
                is_team_award=(len(target_ids) > 1),
                issued_by_id=self.user.id,
            )
            session.add(comm)
            session.flush()

            names = []
            for eid in target_ids:
                session.add(CommendationEmployee(commendation_id=comm.id, employee_id=eid))
                emp = session.query(Employee).filter_by(id=eid).first()
                names.append(emp.full_name)

            log_action(
                session, action="commendation.issue", performed_by_id=self.user.id,
                target_table="commendation", target_id=comm.id,
                description=f"Commendation issued [{ref}]: '{title_text}' (Cat {cat_id}, {cat['months']}mo) to {', '.join(names)}"
            )

            session.commit()

            msg = t(
                "commendation_issued_success",
                ref=ref,
                category=t(cat["label_key"]),
                months=cat["months"],
                count=len(target_ids),
            )
            if skipped_names:
                msg += "\n\n" + t("skipped_max_reached", names=", ".join(skipped_names))
            _information(self, t("success"), msg)

            self._clear()
            self.refresh_employees()
            self.on_issued()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()


# History Tab
class CommendationHistoryTab(QWidget):
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
        card.setObjectName("Card")
        card.setStyleSheet(CARD_SS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background: transparent; border: none; border-bottom: 1px solid #e5e7eb;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(30, 28, 30, 28)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.award", color="#d97706").pixmap(18, 18))
        title = QLabel(t("recent_commendations"))
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827; background: transparent;")
        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addStretch()
        cl.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            t("commendation_id"), t("title"), t("category"), t("promotion_impact"),
            t("recipients"), t("issued_by"), t("date")
        ])
        self.table.setStyleSheet(TABLE_SS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        cl.addWidget(self.table)
        layout.addWidget(card)

    def refresh(self):
        session = get_session()
        try:
            comms = session.query(Commendation).order_by(Commendation.issued_at.desc()).all()
            rows = []
            for c in comms:
                recipient_rows = (
                    session.query(Employee)
                    .join(CommendationEmployee, CommendationEmployee.employee_id == Employee.id)
                    .filter(CommendationEmployee.commendation_id == c.id)
                    .order_by(Employee.first_name, Employee.last_name)
                    .all()
                )
                recipients = ", ".join(e.full_name for e in recipient_rows) or "-"
                issuer = c.issued_by
                if issuer is None and c.issued_by_id:
                    issuer = session.query(SystemUser).filter_by(id=c.issued_by_id).first()
                cat = CATEGORIES.get(c.category, {})
                rows.append({
                    "ref": c.commendation_ref,
                    "title": c.title,
                    "category": t(cat.get("label_key", "category")) if cat else f"Cat {c.category}",
                    "impact": t("negative_month_count", count=abs(c.months_impact)),
                    "recipients": recipients,
                    "issued_by": issuer.full_name if issuer else "-",
                    "date": c.issued_at.strftime("%Y-%m-%d") if c.issued_at else "-",
                    "cat_id": c.category,
                })
        finally:
            session.close()

        self.table.setRowCount(len(rows))
        self.table.setMinimumHeight(112 + (56 * max(1, len(rows))))
        for i, row in enumerate(rows):
            self.table.setRowHeight(i, 52)

            ref_item = QTableWidgetItem(row["ref"])
            ref_item.setForeground(QColor("#6b7280"))
            ref_item.setToolTip(row["ref"])
            self.table.setItem(i, 0, ref_item)
            title_item = QTableWidgetItem(row["title"])
            title_item.setToolTip(row["title"])
            self.table.setItem(i, 1, title_item)

            cat = CATEGORIES.get(row["cat_id"], {})
            cat_item = QTableWidgetItem(row["category"])
            cat_item.setBackground(QColor(cat.get("bg", "#f9fafb")))
            cat_item.setForeground(QColor(cat.get("color", "#374151")))
            cat_item.setToolTip(row["category"])
            self.table.setItem(i, 2, cat_item)

            impact_item = QTableWidgetItem(row["impact"])
            impact_item.setIcon(qta.icon("fa5s.clock", color="#10b981"))
            impact_item.setForeground(QColor("#10b981"))
            impact_item.setToolTip(row["impact"])
            self.table.setItem(i, 3, impact_item)

            for col, key in [(4, "recipients"), (5, "issued_by"), (6, "date")]:
                item = QTableWidgetItem(row[key])
                item.setToolTip(row[key])
                self.table.setItem(i, col, item)


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


def _note_line(text, color):
    lbl = QLabel("&bull; " + text)
    lbl.setTextFormat(Qt.RichText)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"font-size: 14px; color: {color}; background: transparent;")
    return lbl


def _polish_combo(combo):
    combo.setMaxVisibleItems(12)
    view = combo.view()
    view.setStyleSheet("""
        QListView {
            background: white;
            color: #111827;
            border: 1px solid #d1d5db;
            border-radius: 0;
            outline: none;
            padding: 4px;
        }
        QListView::item {
            min-height: 30px;
            padding: 6px 10px;
            background: white;
            color: #111827;
        }
        QListView::item:selected,
        QListView::item:hover {
            background: #eff6ff;
            color: #111827;
        }
    """)
    view.window().setStyleSheet("background: white; border: none;")
