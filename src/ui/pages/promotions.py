"""Promotions Page - eligible tracker, history, configurable rules."""

from datetime import datetime
import qtawesome as qta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QDialog, QFormLayout, QGridLayout,
    QProgressBar, QMessageBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor
from sqlalchemy.orm import joinedload

from src.core.i18n import t
from src.database.connection import (
    get_session, log_action, calculate_months_remaining,
    calculate_months_remaining_batch, calculate_sub_race, display_title_name
)
from src.database.models import Employee, Title, PromotionRule, PromotionHistory, SalaryIncrementHistory
from src.ui.animations import install_tab_transition
from src.ui.styles import (
    btn_primary, btn_outline, input_style, message_box_ss, pager_button_ss,
    pill_tab_ss, card_ss, enable_table_row_selection, prepare_table_cell_widget,
    scroll_ss, table_style, primary_button_fg, sync_table_widget_cells,
    level_badge_colors, race_color, race_soft_color, race_progress_bar_ss,
)
from src.ui.theme import THEME_DARK, tokens

_ICO = QSize(16, 16)

def PROMO_TABLE_SS():
    return table_style()

def PROMO_CARD_SS():
    return card_ss("QFrame#PromoCard")


def PROMO_SCROLL_SS():
    return scroll_ss(tokens().canvas)


def INPUT_SS():
    return input_style()


def MESSAGE_BOX_SS():
    return message_box_ss()


def _level_badge_colors():
    return level_badge_colors()


def _success_badge_colors():
    tkn = tokens()
    return tkn.success_soft, tkn.success


def _target_badge_colors():
    return race_soft_color("eligible"), race_color("eligible")


def _status_color(kind):
    return race_color(kind)


def _soft_panel_ss(kind):
    tkn = tokens()
    if kind == "warning":
        bg, fg, border = tkn.warning_soft, tkn.warning, tkn.warning
    elif kind == "reset":
        bg = tkn.surface_muted if tkn.name == THEME_DARK else "#f4f0ff"
        fg = "#c4b5fd" if tkn.name == THEME_DARK else "#5b21b6"
        border = tkn.border_strong if tkn.name == THEME_DARK else "#ddd6fe"
    else:
        bg, fg, border = tkn.selected, tkn.brand, tkn.brand
    return (
        f"QFrame {{ background: {bg}; border: 1px solid {border}; border-radius: 8px; }}"
        f"QLabel {{ background: transparent; border: none; color: {fg}; }}"
    )


def _info_panel_ss(object_name):
    return (
        f"QFrame#{object_name} {{ background: {tokens().selected}; border-radius: 8px; border: 1px solid {tokens().brand}; }}"
        f"QFrame#{object_name} QLabel {{ background: transparent; border: none; }}"
    )


class PromotionsPage(QWidget):
    def __init__(self, user, navigate_to_employee=None):
        super().__init__()
        self.user = user
        self.navigate_to_employee = navigate_to_employee
        self.setObjectName("PromotionsPage")
        self.setStyleSheet(f"QWidget#PromotionsPage {{ background: {tokens().canvas}; }}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("promotions_title"))
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {tokens().text}; background: transparent;")
        subtitle = QLabel(t("promotions_subtitle"))
        subtitle.setStyleSheet(f"font-size: 16px; color: {tokens().text_muted}; background: transparent;")
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(40)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(pill_tab_ss())

        self.eligible_tab = EligibleTab(self.user, navigate_to_employee=self.navigate_to_employee)
        self.history_tab  = HistoryTab(self.user)

        self.tabs.addTab(self.eligible_tab, t("eligible_employees"))
        self.tabs.addTab(self.history_tab,  t("promotion_history"))
        self.tabs.currentChanged.connect(self._on_tab_change)
        install_tab_transition(self.tabs)
        layout.addWidget(self.tabs, 1)

    def _on_tab_change(self, index):
        if index == 0: self.eligible_tab.refresh()
        elif index == 1: self.history_tab.refresh()

    def showEvent(self, event):
        self.eligible_tab.refresh()
        super().showEvent(event)


# Eligible tab
class EligibleTab(QWidget):
    def __init__(self, user, navigate_to_employee=None):
        super().__init__()
        self.user = user
        self.navigate_to_employee = navigate_to_employee
        self.rows = []
        self.page_size = 50
        self.current_page = 1
        self.total_pages = 1
        self.setObjectName("EligibleTab")
        self.setStyleSheet(f"QWidget#EligibleTab {{ background: {tokens().canvas}; }}")
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(PROMO_SCROLL_SS())
        content = QWidget()
        content.setStyleSheet(f"background: {tokens().canvas};")

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
        banner.setStyleSheet(_info_panel_ss("PromoBanner"))
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(12)
        bico = QLabel()
        bico.setPixmap(qta.icon("fa5s.info-circle", color=tokens().brand).pixmap(18, 18))
        btxt = QLabel(t("promotion_tracker_filter_hint"))
        btxt.setStyleSheet(f"font-size: 14px; color: {tokens().brand}; background: transparent;")
        btxt.setWordWrap(True)
        bl.addWidget(bico)
        bl.addWidget(btxt, 1)
        layout.addWidget(banner)

        # Table card
        table_card = QFrame()
        table_card.setObjectName("PromoCard")
        table_card.setStyleSheet(PROMO_CARD_SS())
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(0, 0, 0, 0)
        tcl.setSpacing(0)

        card_hdr = QFrame()
        card_hdr.setStyleSheet(f"background: transparent; border: none; border-bottom: 1px solid {tokens().border};")
        chl = QHBoxLayout(card_hdr)
        chl.setContentsMargins(32, 28, 32, 28)
        ch_title = QLabel(t("promotion_tracker"))
        ch_title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {tokens().text};")
        chl.addWidget(ch_title)
        chl.addStretch()
        tcl.addWidget(card_hdr)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            t("employee"), t("level"), t("target"),
            t("elapsed_short"), t("commendation"), t("sanction"),
            t("race_status_short"), t("actions")
        ])
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                if col == 7:
                    header_item.setTextAlignment(Qt.AlignCenter)
                else:
                    header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setStyleSheet(PROMO_TABLE_SS())
        self.table.setWordWrap(False)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setFixedHeight(50)
        header.setStretchLastSection(False)
        for col in (0, 6):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        for col in (1, 2, 3, 4, 5, 7):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.table)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tcl.addWidget(self.table)

        pager = QFrame()
        pager.setStyleSheet(f"background: {tokens().surface}; border: none; border-top: 1px solid {tokens().border};")
        pager_layout = QHBoxLayout(pager)
        pager_layout.setContentsMargins(16, 10, 16, 10)
        pager_layout.setSpacing(10)

        self.page_lbl = QLabel("")
        self.page_lbl.setStyleSheet(f"font-size: 13px; color: {tokens().text_muted}; background: transparent;")
        self.prev_btn = QPushButton(t("previous_page"))
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(pager_button_ss())
        self.prev_btn.clicked.connect(self._previous_page)

        self.next_btn = QPushButton(t("next_page"))
        self.next_btn.setFixedHeight(34)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet(pager_button_ss())
        self.next_btn.clicked.connect(self._next_page)

        pager_layout.addStretch()
        pager_layout.addWidget(self.page_lbl)
        pager_layout.addWidget(self.prev_btn)
        pager_layout.addWidget(self.next_btn)
        tcl.addWidget(pager)
        layout.addWidget(table_card)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        QTimer.singleShot(0, self._resize_columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            self._resize_columns()

    def _resize_columns(self):
        if not hasattr(self, "table"):
            return
        try:
            width = max(760, self.table.viewport().width())
        except RuntimeError:
            return
        compact = width < 980
        fixed = {
            1: 64 if compact else 76,
            2: 78 if compact else 88,
            3: 90 if compact else 108,
            4: 156 if compact else 164,
            5: 104 if compact else 112,
            7: 128 if compact else 138,
        }
        for col, col_width in fixed.items():
            try:
                self.table.setColumnWidth(col, col_width)
            except RuntimeError:
                return

    def refresh(self):
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        session = get_session()
        try:
            employees = session.query(Employee).filter_by(status="active").all()
            titles_by_id = {title.id: title for title in session.query(Title).all()}
            races = calculate_months_remaining_batch(employees, session)
            rows = []
            eligible_count = soon_count = progress_count = 0

            for emp in employees:
                race = races.get(emp.id)
                if not race:
                    continue
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
                    nt = titles_by_id.get(race["next_title_id"])
                    if nt:
                        next_title_name = nt.name

                if status in ("eligible", "soon"):
                    rows.append({
                        "id": emp.id,
                        "name": emp.full_name,
                        "emp_id": emp.employee_id,
                        "current": display_title_name(titles_by_id.get(emp.title_id)),
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
        self.rows = rows
        self.current_page = 1

        # Stat cards
        for label, val, status, icon_name in [
            (t("eligible_now"), eligible_count, "eligible", "fa5s.check-circle"),
            (t("eligible_soon"), soon_count, "soon", "fa5s.clock"),
            (t("in_progress"), progress_count, "progress", "fa5s.chart-line"),
        ]:
            card = QFrame()
            card.setObjectName("PromoCard")
            card.setStyleSheet(PROMO_CARD_SS())
            card.setFixedHeight(96)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(22, 0, 22, 0)
            cl.setSpacing(14)
            ico_box = QLabel()
            ico_box.setFixedSize(48, 48)
            ico_box.setAlignment(Qt.AlignCenter)
            if status == "eligible":
                bg, color = race_soft_color("eligible"), race_color("eligible")
            elif status == "soon":
                bg, color = race_soft_color("soon"), race_color("soon")
            else:
                bg, color = race_soft_color("progress"), race_color("progress")
            ico_box.setStyleSheet(f"background: {bg}; border-radius: 8px;")
            ico_box.setPixmap(qta.icon(icon_name, color=color).pixmap(22, 22))
            txt = QVBoxLayout()
            txt.setSpacing(0)
            txt.setAlignment(Qt.AlignVCenter)
            ll = QLabel(label)
            ll.setStyleSheet(f"font-size: 14px; color: {tokens().text_muted}; background: transparent;")
            vl = QLabel(str(val))
            vl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {tokens().text}; background: transparent;")
            txt.addWidget(ll)
            txt.addWidget(vl)
            cl.addWidget(ico_box)
            cl.addLayout(txt)
            cl.addStretch()
            self.stats_row.addWidget(card)
        self.stats_row.addStretch()

        self._populate_page()

    def _populate_page(self):
        total = len(self.rows)
        self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        start = (self.current_page - 1) * self.page_size
        page_rows = self.rows[start:start + self.page_size]

        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(0)
            self.table.clearContents()
            self.table.setRowCount(len(page_rows))
            self.table.setFixedHeight(50 + (64 * max(1, len(page_rows))) + 4)
            self._resize_columns()
            for ri, row in enumerate(page_rows):
                self._set_eligible_row(ri, row)
            sync_table_widget_cells(self.table)
        finally:
            self.table.setUpdatesEnabled(True)

        self.page_lbl.setText(t("page_status", page=self.current_page, pages=self.total_pages))
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)

    def _set_eligible_row(self, ri, row):
        self.table.setRowHeight(ri, 64)

        # Employee name + ID
        name_w = prepare_table_cell_widget(QWidget())
        nl = QVBoxLayout(name_w)
        nl.setContentsMargins(0, 4, 4, 4)
        nl.setSpacing(1)
        n1 = QLabel(row["name"])
        n1.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {tokens().text};")
        n2 = QLabel(row["emp_id"])
        n2.setStyleSheet(f"font-size: 11px; color: {tokens().text_muted};")
        nl.addWidget(n1)
        nl.addWidget(n2)
        name_w.setToolTip(f"{row['name']} ({row['emp_id']})")
        self.table.setCellWidget(ri, 0, name_w)

        level_bg, level_fg = _level_badge_colors()
        target_bg, target_fg = _target_badge_colors()
        self.table.setItem(ri, 1, self._badge_item(row["current"], level_bg, level_fg))
        self.table.setItem(ri, 2, self._badge_item(row["next"], target_bg, target_fg))
        self._set_text_item(ri, 3, f"{row['elapsed']} mo")
        self._set_text_item(ri, 4, f"-{row['comm']} mo")
        self._set_text_item(ri, 5, f"+{row['sanction']} mo")

        # Progress cell
        mr = row["mr"]
        bm = max(row["base_months"], 1)
        pct = max(0, min(100, int(100 - (mr / bm * 100))))
        prog_w = prepare_table_cell_widget(QWidget())
        prog_w.setMinimumWidth(172)
        prog_l = QVBoxLayout(prog_w)
        prog_l.setContentsMargins(0, 8, 12, 8)
        prog_l.setSpacing(3)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setFixedHeight(8)
        bar.setTextVisible(False)
        bar_status = "eligible" if mr == 0 else "soon" if mr <= 6 else "progress"
        bar.setStyleSheet(race_progress_bar_ss(bar_status, radius=4))
        prog_l.addWidget(bar)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        status_icon = QLabel()
        status_icon.setFixedSize(14, 14)
        if mr == 0:
            lbl_txt = t("eligible_now")
            lbl_color = _status_color("eligible")
            status_icon.setPixmap(qta.icon("fa5s.check-circle", color=lbl_color).pixmap(13, 13))
        elif mr <= 6:
            lbl_txt = t("months_remaining_count", count=mr)
            lbl_color = _status_color("soon")
            status_icon.setPixmap(qta.icon("fa5s.clock", color=lbl_color).pixmap(13, 13))
        else:
            lbl_txt = t("months_remaining_count", count=mr)
            lbl_color = _status_color("progress")
            status_icon.setPixmap(qta.icon("fa5s.chart-line", color=lbl_color).pixmap(13, 13))
        p_lbl = QLabel(lbl_txt)
        p_lbl.setStyleSheet(f"font-size: 12px; color: {lbl_color};")
        p_lbl.setMinimumWidth(96)
        status_row.addWidget(status_icon)
        status_row.addWidget(p_lbl)
        status_row.addStretch()
        prog_l.addLayout(status_row)
        prog_w.setToolTip(lbl_txt)
        self.table.setCellWidget(ri, 6, prog_w)

        # Action button
        act_w = prepare_table_cell_widget(QWidget())
        act_l = QHBoxLayout(act_w)
        act_l.setContentsMargins(2, 8, 2, 8)
        act_l.setAlignment(Qt.AlignCenter)
        if row["status"] == "eligible":
            btn = QPushButton(t("approve"))
            btn.setIcon(qta.icon("fa5s.check", color=primary_button_fg()))
            btn.setIconSize(QSize(13, 13))
            btn.setFixedSize(112, 38)
            btn.setStyleSheet(btn_primary(38))
            btn.clicked.connect(lambda _, eid=row["id"]: self._approve_promotion(eid))
        else:
            btn = QPushButton(t("view"))
            btn.setIcon(qta.icon("fa5s.eye", color=tokens().text_muted))
            btn.setIconSize(QSize(13, 13))
            btn.setFixedSize(86, 38)
            btn.setStyleSheet(btn_outline(32))
            btn.setToolTip(t("view_profile"))
            if self.navigate_to_employee:
                btn.clicked.connect(lambda _, eid=row["id"]: self.navigate_to_employee(eid))
            else:
                btn.setEnabled(False)
        act_l.addWidget(btn)
        self.table.setCellWidget(ri, 7, act_w)

    def _previous_page(self):
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self._populate_page()

    def _next_page(self):
        if self.current_page >= self.total_pages:
            return
        self.current_page += 1
        self._populate_page()

    def _badge_item(self, text, bg, fg):
        item = QTableWidgetItem(text)
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))
        item.setTextAlignment(Qt.AlignCenter)
        item.setToolTip(text)
        return item

    def _set_text_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item.setToolTip(text)
        self.table.setItem(row, col, item)

    def _approve_promotion(self, employee_id):
        session = get_session()
        try:
            emp = session.query(Employee).filter_by(id=employee_id).first()
            race = calculate_months_remaining(emp, session)
            if not race["eligible"]:
                _warning(self, t("warning"), t("employee_not_eligible"))
                return
            sub_race = calculate_sub_race(emp, session)
            next_title = session.query(Title).filter_by(id=race["next_title_id"]).first()
            old_title  = emp.title
            salary_before = emp.base_salary
            salary_pct = next_title.promotion_salary_increase_pct if next_title else 0
            salary_after = round(salary_before * (1 + salary_pct / 100), 2)
            confirm = _question(
                self, t("confirm_promotion"),
                t(
                    "confirm_promotion_body",
                    name=emp.full_name,
                    from_level=old_title.name,
                    to_level=next_title.name,
                    salary_pct=f"{salary_pct:.1f}",
                    salary_before=f"EUR {salary_before:,.2f}",
                    salary_after=f"EUR {salary_after:,.2f}",
                ),
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
                notes=(
                    f"Sub-race completed from {sub_race['current_step_label']} to {next_title.name}. "
                    f"Commendation: -{race['commendation_reduction']}mo, Sanction: +{race['sanction_addition']}mo"
                ),
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
                t("promoted_success", name=emp.full_name, level=next_title.name))
            self.refresh()
        except Exception as e:
            session.rollback()
            _critical(self, t("error"), str(e))
        finally:
            session.close()


# History tab
class HistoryTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.loaded = False
        self.rows = []
        self.page_size = 50
        self.current_page = 1
        self.total_pages = 1
        self.setObjectName("HistoryTab")
        self.setStyleSheet(f"QWidget#HistoryTab {{ background: {tokens().canvas}; }}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("PromoCard")
        card.setStyleSheet(PROMO_CARD_SS())
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)

        ch = QFrame()
        ch.setStyleSheet(f"background: transparent; border: none; border-bottom: 1px solid {tokens().border};")
        chl = QHBoxLayout(ch)
        chl.setContentsMargins(32, 28, 32, 28)
        chl.addWidget(_bold_label(t("recent_promotions"), size=20, weight=800))
        cl.addWidget(ch)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("employee"), t("promotion"), t("basis"), t("months"), t("approved_by"), t("date")
        ])
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setStyleSheet(PROMO_TABLE_SS())
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setFixedHeight(50)
        header.setStretchLastSection(False)
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        enable_table_row_selection(self.table)
        self.table.setShowGrid(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setMinimumHeight(420)
        cl.addWidget(self.table)

        pager = QFrame()
        pager.setStyleSheet(f"background: {tokens().surface}; border: none; border-top: 1px solid {tokens().border};")
        pager_layout = QHBoxLayout(pager)
        pager_layout.setContentsMargins(16, 10, 16, 10)
        pager_layout.setSpacing(10)

        self.page_lbl = QLabel("")
        self.page_lbl.setStyleSheet(f"font-size: 13px; color: {tokens().text_muted}; background: transparent;")
        self.prev_btn = QPushButton(t("previous_page"))
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.setStyleSheet(pager_button_ss())
        self.prev_btn.clicked.connect(self._previous_page)

        self.next_btn = QPushButton(t("next_page"))
        self.next_btn.setFixedHeight(34)
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setStyleSheet(pager_button_ss())
        self.next_btn.clicked.connect(self._next_page)

        pager_layout.addStretch()
        pager_layout.addWidget(self.page_lbl)
        pager_layout.addWidget(self.prev_btn)
        pager_layout.addWidget(self.next_btn)
        cl.addWidget(pager)
        layout.addWidget(card)
        QTimer.singleShot(0, self._resize_columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            self._resize_columns()

    def _resize_columns(self):
        if not hasattr(self, "table"):
            return
        try:
            width = max(760, self.table.viewport().width())
        except RuntimeError:
            return
        base = [220, 300, 132, 88, 176, 136]
        available = max(760, width - 8)
        total = sum(base)
        widths = list(base)
        if available > total:
            extra = available - total
            widths[0] += int(extra * 0.32)
            widths[1] += int(extra * 0.36)
            widths[4] += int(extra * 0.18)
            widths[5] += extra - int(extra * 0.32) - int(extra * 0.36) - int(extra * 0.18)
        elif available < total:
            scale = available / total
            minimums = [178, 238, 106, 72, 132, 112]
            widths = [max(minimums[i], int(base[i] * scale)) for i in range(len(base))]
        for col, col_width in enumerate(widths):
            try:
                self.table.setColumnWidth(col, col_width)
            except RuntimeError:
                return

    def refresh(self):
        self.loaded = True
        self.current_page = 1
        self._populate_page()

    def _promotion_row(self, h):
        basis = h.basis.replace("_", " ").title()
        if h.basis == "time_based":
            basis = "Time"
        elif h.basis == "accelerated":
            basis = "Accelerated"
        return {
            "sort_date": h.promoted_at or datetime.min,
            "name": h.employee.full_name, "emp_id": h.employee.employee_id,
            "from": display_title_name(h.from_title), "to": display_title_name(h.to_title),
            "basis": basis,
            "months": str(h.months_taken) + " mo" if h.months_taken else "-",
            "by": h.approved_by.full_name if h.approved_by else "System",
            "date": h.promoted_at.strftime("%Y-%m-%d") if h.promoted_at else "-",
            "kind": "promotion",
        }

    def _increment_row(self, inc):
        return {
            "sort_date": inc.applied_at or datetime.min,
            "name": inc.employee.full_name, "emp_id": inc.employee.employee_id,
            "from": t("annual_short"), "to": f"EUR {inc.salary_after:,.2f}",
            "basis": t("annual_short"),
            "months": "-",
            "by": inc.approved_by.full_name if inc.approved_by else "System",
            "date": inc.applied_at.strftime("%Y-%m-%d") if inc.applied_at else "-",
            "kind": "increment",
            "details": inc.notes or "",
        }

    def _load_page_rows(self):
        session = get_session()
        try:
            promo_count = session.query(PromotionHistory.id).count()
            increment_count = session.query(SalaryIncrementHistory.id).count()
            total = promo_count + increment_count
            self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
            self.current_page = max(1, min(self.current_page, self.total_pages))
            start = (self.current_page - 1) * self.page_size
            window = start + self.page_size
            promotions = (
                session.query(PromotionHistory)
                .options(
                    joinedload(PromotionHistory.employee),
                    joinedload(PromotionHistory.from_title),
                    joinedload(PromotionHistory.to_title),
                    joinedload(PromotionHistory.approved_by),
                )
                .order_by(PromotionHistory.promoted_at.desc(), PromotionHistory.id.desc())
                .limit(window)
                .all()
            )
            increments = (
                session.query(SalaryIncrementHistory)
                .options(
                    joinedload(SalaryIncrementHistory.employee),
                    joinedload(SalaryIncrementHistory.approved_by),
                )
                .order_by(SalaryIncrementHistory.applied_at.desc(), SalaryIncrementHistory.id.desc())
                .limit(window)
                .all()
            )
            rows = [self._promotion_row(row) for row in promotions]
            rows.extend(self._increment_row(row) for row in increments)
            rows.sort(key=lambda row: row["sort_date"], reverse=True)
            return rows[start:start + self.page_size], total
        finally:
            session.close()

    def _populate_page(self):
        page_rows, total = self._load_page_rows()

        self.table.setUpdatesEnabled(False)
        try:
            self.table.clearContents()
            self.table.setRowCount(len(page_rows))
            self.table.setMinimumHeight(420)
            for i, row in enumerate(page_rows):
                self._set_history_row(i, row)
            self._resize_columns()
            sync_table_widget_cells(self.table)
        finally:
            self.table.setUpdatesEnabled(True)

        self.page_lbl.setText(t("page_status", page=self.current_page, pages=self.total_pages))
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)

    def _set_history_row(self, i, row):
        self.table.setRowHeight(i, 52)
        # Employee cell
        ew = prepare_table_cell_widget(QWidget())
        el = QVBoxLayout(ew)
        el.setContentsMargins(0, 4, 4, 4)
        el.setSpacing(1)
        e1 = QLabel(row["name"])
        e1.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {tokens().text};")
        e2 = QLabel(row["emp_id"])
        e2.setStyleSheet(f"font-size: 11px; color: {tokens().text_muted};")
        el.addWidget(e1)
        el.addWidget(e2)
        ew.setToolTip(f"{row['name']} ({row['emp_id']})")
        self.table.setCellWidget(i, 0, ew)

        promo_w = prepare_table_cell_widget(QWidget())
        if row["kind"] == "increment":
            pl = QHBoxLayout(promo_w)
            pl.setContentsMargins(8, 5, 8, 5)
            pl.setSpacing(6)
            fl = QLabel(row["from"])
            fl.setFixedHeight(28)
            fl.setMinimumWidth(90)
            fl.setAlignment(Qt.AlignCenter)
            level_bg, level_fg = _level_badge_colors()
            fl.setStyleSheet(f"background: {level_bg}; color: {level_fg}; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 700;")
            arrow = QLabel()
            arrow.setPixmap(qta.icon("fa5s.arrow-right", color=tokens().success).pixmap(12, 12))
            tl = QLabel(row["to"])
            tl.setFixedHeight(28)
            tl.setMinimumWidth(120)
            tl.setAlignment(Qt.AlignCenter)
            success_bg, success_fg = _success_badge_colors()
            tl.setStyleSheet(f"background: {success_bg}; color: {success_fg}; border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 700;")
            promo_w.setToolTip(row.get("details") or f"{row['from']} -> {row['to']}")
            pl.addWidget(fl)
            pl.addWidget(arrow)
            pl.addWidget(tl)
            pl.addStretch()
        else:
            pl = QHBoxLayout(promo_w)
            pl.setContentsMargins(8, 5, 8, 5)
            pl.setSpacing(6)
            fl = QLabel(row["from"])
            fl.setMinimumWidth(44)
            fl.setAlignment(Qt.AlignCenter)
            level_bg, level_fg = _level_badge_colors()
            fl.setStyleSheet(f"background: {level_bg}; color: {level_fg}; border-radius: 6px; padding: 3px 9px; font-size: 12px; font-weight: 700;")
            arrow = QLabel()
            arrow.setPixmap(qta.icon("fa5s.arrow-right", color=tokens().success).pixmap(12, 12))
            tl = QLabel(row["to"])
            tl.setMinimumWidth(44)
            tl.setAlignment(Qt.AlignCenter)
            success_bg, success_fg = _success_badge_colors()
            tl.setStyleSheet(f"background: {success_bg}; color: {success_fg}; border-radius: 6px; padding: 3px 9px; font-size: 12px; font-weight: 700;")
            promo_w.setToolTip(f"{row['from']} -> {row['to']}")
            pl.addWidget(fl)
            pl.addWidget(arrow)
            pl.addWidget(tl)
            pl.addStretch()
        self.table.setCellWidget(i, 1, promo_w)

        _set_table_item(self.table, i, 2, row["basis"])
        _set_table_item(self.table, i, 3, row["months"])
        _set_table_item(self.table, i, 4, row["by"])
        _set_table_item(self.table, i, 5, row["date"])

    def _previous_page(self):
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self._populate_page()

    def _next_page(self):
        if self.current_page >= self.total_pages:
            return
        self.current_page += 1
        self._populate_page()


# Rules tab
class RulesTab(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setObjectName("RulesTab")
        self.setStyleSheet(f"QWidget#RulesTab {{ background: {tokens().canvas}; }}")
        self._build()
        self.refresh()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"border: none; background: {tokens().canvas};")
        content = QWidget()
        content.setStyleSheet(f"background: {tokens().canvas};")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        # Rules configuration card
        card = QFrame()
        card.setObjectName("PromoCard")
        card.setStyleSheet(PROMO_CARD_SS())
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 22, 22, 22)
        cl.setSpacing(22)

        chl = QHBoxLayout()
        chl.setContentsMargins(0, 0, 0, 0)
        header_text = QVBoxLayout()
        header_text.setSpacing(6)
        header_text.addWidget(_bold_label("Promotion Track Configuration", size=20, weight=800))
        sub = QLabel("Configure the promotion race timeline for each level")
        sub.setStyleSheet(f"font-size: 14px; color: {tokens().text_muted}; background: transparent;")
        header_text.addWidget(sub)
        chl.addLayout(header_text)
        chl.addStretch()
        cl.addLayout(chl)

        info = QFrame()
        info.setObjectName("PromoInfo")
        info.setStyleSheet(_info_panel_ss("PromoInfo"))
        il = QVBoxLayout(info)
        il.setContentsMargins(20, 18, 20, 18)
        il.setSpacing(4)
        ih = QHBoxLayout()
        ih.setSpacing(10)
        ico = QLabel()
        ico.setPixmap(qta.icon("fa5s.chart-line", color=tokens().brand).pixmap(18, 18))
        it = QLabel("How the Promotion Race Works")
        it.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {tokens().brand};")
        ih.addWidget(ico); ih.addWidget(it); ih.addStretch()
        il.addLayout(ih)
        il.addWidget(_guide_line("Each promotion level is a <b>race track</b> with a base duration in months"))
        il.addWidget(_guide_line("Employees move forward <b>1 checkpoint per month</b> automatically"))
        il.addWidget(_guide_line("<b>Commendations</b> speed up the race (reduce months remaining)"))
        il.addWidget(_guide_line("<b>Sanctions</b> delay the race (add months to the timeline)"))
        il.addWidget(_guide_line("When the employee reaches the finish line (0 months remaining), they become eligible for promotion"))
        cl.addWidget(info)

        self.rules_list = QVBoxLayout()
        self.rules_list.setSpacing(18)
        cl.addLayout(self.rules_list)

        cl.addWidget(self._modifier_card())
        cl.addWidget(self._reset_policy_card())
        layout.addWidget(card)
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
                "salary_increase": _format_pct(r.to_title.promotion_salary_increase_pct),
            } for r in rules]
        finally:
            session.close()

        while self.rules_list.count():
            item = self.rules_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for row in rows:
            self.rules_list.addWidget(self._rule_card(row))

    def _rule_card(self, row):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {tokens().surface_muted}; border: 1px solid {tokens().border}; border-radius: 8px; }}"
            "QLabel { background: transparent; border: none; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.chart-line", color=tokens().brand).pixmap(17, 17))
        title = QLabel(f"{row['from']} to {row['to']}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {tokens().text};")
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(92, 34)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(btn_outline(34))
        edit_btn.clicked.connect(lambda _, rid=row["id"]: self._edit_rule(rid))
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(edit_btn)
        layout.addLayout(title_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(_field_label("Base Track Duration (months)"), 0, 0)
        grid.addWidget(_field_label("Base Salary Increase"), 0, 1)
        grid.addWidget(_readonly_field(str(row["base_months"])), 1, 0)
        grid.addWidget(_readonly_field(row["salary_increase"]), 1, 1)
        grid.addWidget(_hint_label("Starting point for the promotion race"), 2, 0)
        grid.addWidget(_hint_label("Upon promotion to next level"), 2, 1)
        layout.addLayout(grid)
        return card

    def _modifier_card(self):
        card = QFrame()
        card.setStyleSheet(_soft_panel_ss("warning"))
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.clock", color=tokens().warning).pixmap(20, 20))
        layout.addWidget(icon, alignment=Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(8)
        title = QLabel("Track Modifiers (Optional)")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {tokens().warning};")
        text.addWidget(title)
        text.addWidget(_mini_line("fa5s.award", "Commendations reduce the months remaining in the current race.", tokens().warning))
        text.addWidget(_mini_line("fa5s.exclamation-triangle", "Sanctions add delay months to the promotion timeline.", tokens().warning))
        text.addWidget(_mini_line("fa5s.cog", "Configure awards and sanction impacts on their own pages.", tokens().warning))
        layout.addLayout(text, 1)
        return card

    def _reset_policy_card(self):
        card = QFrame()
        card.setStyleSheet(_soft_panel_ss("reset"))
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        icon = QLabel()
        reset_color = "#c4b5fd" if tokens().name == THEME_DARK else "#5b21b6"
        icon.setPixmap(qta.icon("fa5s.chart-line", color=reset_color).pixmap(20, 20))
        layout.addWidget(icon, alignment=Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(8)
        title = QLabel("Reset Policy")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {reset_color};")
        body = QLabel("After a promotion, the employee starts a new race from month 0. The timer for the next promotion begins from the promotion date.")
        body.setWordWrap(True)
        body.setStyleSheet(f"font-size: 14px; color: {reset_color};")
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
        self.setStyleSheet(f"QDialog {{ background: {tokens().surface}; color: {tokens().text}; }} QLabel {{ background: transparent; color: {tokens().text}; }}")
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        layout.addWidget(_bold_label("Edit Promotion Rule", size=17))

        self.transition_lbl = QLabel("")
        self.transition_lbl.setStyleSheet(f"font-size: 14px; color: {tokens().brand}; font-weight: 600;")
        layout.addWidget(self.transition_lbl)

        self.months_spin = QSpinBox()
        self.months_spin.setRange(1, 120)
        self.months_spin.setStyleSheet(INPUT_SS())
        self.months_spin.setFixedHeight(42)

        self.salary_spin = QDoubleSpinBox()
        self.salary_spin.setRange(0.0, 100.0)
        self.salary_spin.setDecimals(1)
        self.salary_spin.setSingleStep(0.5)
        self.salary_spin.setSuffix("%")
        self.salary_spin.setStyleSheet(INPUT_SS())
        self.salary_spin.setFixedHeight(42)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.addRow("Base Track Duration (months) *", self.months_spin)
        form.addRow("Salary Increase on Promotion *", self.salary_spin)
        layout.addLayout(form)

        note = QLabel("Commendations and sanctions modify the race duration. The salary increase is applied to the employee base salary when this promotion is approved.")
        note.setStyleSheet(f"font-size: 12px; color: {tokens().text_muted};")
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
    item.setToolTip(str(text))
    table.setItem(row, col, item)


def _level_badge(text, bg, fg):
    label = QLabel(text)
    label.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 7px; padding: 4px 10px; font-size: 12px; font-weight: 700;")
    return label


def _guide_line(text):
    row = QWidget()
    row.setStyleSheet("background: transparent; border: none;")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(30, 2, 0, 2)
    layout.setSpacing(6)
    bullet = QLabel()
    bullet.setTextFormat(Qt.RichText)
    bullet.setText("&bull;")
    bullet.setFixedWidth(10)
    bullet.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
    bullet.setStyleSheet(f"font-size: 14px; color: {tokens().brand}; font-weight: 800;")
    label = QLabel(text)
    label.setTextFormat(Qt.RichText)
    label.setWordWrap(True)
    label.setStyleSheet(f"font-size: 14px; color: {tokens().brand};")
    layout.addWidget(bullet, alignment=Qt.AlignTop)
    layout.addWidget(label, 1)
    return row


def _field_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {tokens().text}; background: transparent;")
    return lbl


def _readonly_field(text):
    lbl = QLabel(text)
    lbl.setMinimumHeight(42)
    lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    lbl.setStyleSheet(
        f"background: {tokens().surface_muted}; color: {tokens().text_muted}; border: none; border-radius: 7px;"
        " padding: 0 14px; font-size: 14px;"
    )
    return lbl


def _hint_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: 12px; color: {tokens().text_muted}; background: transparent;")
    return lbl


def _format_pct(value):
    try:
        numeric = float(value)
        return f"{int(numeric)}%" if numeric.is_integer() else f"{numeric:.1f}%"
    except (TypeError, ValueError):
        return f"{value}%"


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
    box.setStyleSheet(MESSAGE_BOX_SS())
    return box.exec()


def _warning(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Warning, title, text)


def _critical(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Critical, title, text)


def _information(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Information, title, text)


def _question(parent, title, text):
    return _styled_message_box(parent, QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)


def _bold_label(text, size=15, weight=600):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: {size}px; font-weight: {weight}; color: {tokens().text}; background: transparent;")
    return lbl
