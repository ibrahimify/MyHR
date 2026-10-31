"""Anomaly Review Page.

Human-in-the-loop decision-support view for the policy-aware anomaly-detection
research pipeline. It runs the detector over a small SYNTHETIC workforce sample
and presents a prioritized review queue:

- Deterministic policy/data contradictions (explained rule findings).
- Isolation Forest ranking of residual histories (when scikit-learn is present).

Scientific and product boundaries (see AGENTS.md):
- Every row is a recommendation for a human reviewer. Nothing here changes a
  real employee record; the page performs no database writes.
- The data shown is synthetic development data generated on demand, never a
  locked holdout and never real employee data.
- Anomaly scores support review only and must never trigger an automatic
  personnel decision.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QAbstractItemView,
)

from src.core.i18n import t
from src.ui.components.app_select import AppSelect
from src.ui.icons import app_pixmap
from src.ui.styles import (
    alert_ss,
    badge_ss,
    card_ss,
    enable_table_row_selection,
    sync_table_widget_cells,
    table_style,
)
from src.ui.theme import tokens

from src.services.anomaly_detection import (
    ExperimentConfig,
    DatasetSplit,
    ValidationSeverity,
    generate_synthetic_dataset,
    validate_record,
    extract_policy_aware_features,
    run_isolation_forest,
    sklearn_is_available,
    IsolationForestUnavailableError,
)


# Review-priority bands derived from the detector signals. These are triage
# labels for a human reviewer, not decisions.
_PRIORITY_META = {
    "rule": ("Rule", "#b91c1c", "#fee2e2"),
    "high": ("High", "#c2410c", "#ffedd5"),
    "medium": ("Medium", "#a16207", "#fef9c3"),
    "low": ("Low", "#15803d", "#dcfce7"),
}


class AnomalyReviewPage(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._rows = []
        self._sample_seed = 2026
        self.setObjectName("AnomalyReviewPage")
        self.setStyleSheet(f"QWidget#AnomalyReviewPage {{ background: {tokens().canvas}; }}")
        self._build()
        self.refresh()

    # ----- construction -------------------------------------------------
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        title = QLabel(t("nav_anomaly_review"))
        title.setStyleSheet(
            f"font-size: 30px; font-weight: 800; color: {tokens().text}; background: transparent;"
        )
        subtitle = QLabel(
            "Policy-aware review queue over a synthetic workforce sample. "
            "Every item is a recommendation for human review only."
        )
        subtitle.setStyleSheet(
            f"font-size: 16px; color: {tokens().text_muted}; background: transparent;"
        )
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(28)

        # Stat cards
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(20)
        self.stat_values = {}
        self._add_stat_card("reviewed", "Histories screened", "fa5s.users", "#2563eb", "#dbeafe")
        self._add_stat_card("rule", "Rule findings", "fa5s.exclamation-triangle", "#b91c1c", "#fee2e2")
        self._add_stat_card("flagged", "ML-flagged for review", "fa5s.search", "#c2410c", "#ffedd5")
        self._add_stat_card("model", "Ranking model", "fa5s.robot", "#9333ea", "#f3e8ff")
        layout.addLayout(self.stats_row)
        layout.addSpacing(26)

        # Filter card
        filter_card = QFrame()
        filter_card.setObjectName("Card")
        filter_card.setStyleSheet(card_ss("QFrame#Card"))
        fl = QHBoxLayout(filter_card)
        fl.setContentsMargins(20, 18, 20, 18)
        fl.setSpacing(14)

        filter_label = QLabel("Show")
        filter_label.setStyleSheet(
            f"font-size: 14px; color: {tokens().text_muted}; background: transparent;"
        )
        fl.addWidget(filter_label)

        self.priority_filter = AppSelect(height=44)
        self.priority_filter.addItem("All review items", None)
        self.priority_filter.addItem("Rule findings only", "rule")
        self.priority_filter.addItem("High priority", "high")
        self.priority_filter.addItem("Medium priority", "medium")
        self.priority_filter.addItem("Low priority", "low")
        self.priority_filter.currentIndexChanged.connect(self._apply_filter)
        fl.addWidget(self.priority_filter, 2)

        self.sample_select = AppSelect(height=44)
        for label, seed in (("Sample A (seed 2026)", 2026), ("Sample B (seed 2027)", 2027), ("Sample C (seed 2028)", 2028)):
            self.sample_select.addItem(label, seed)
        self.sample_select.currentIndexChanged.connect(self._change_sample)
        fl.addWidget(self.sample_select, 2)

        fl.addStretch(1)
        layout.addWidget(filter_card)
        layout.addSpacing(18)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(
            f"font-size: 14px; color: {tokens().text_muted}; background: transparent;"
        )
        layout.addWidget(self.count_lbl)
        layout.addSpacing(14)

        # Review table
        table_card = QFrame()
        table_card.setObjectName("Card")
        table_card.setStyleSheet(card_ss("QFrame#Card"))
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Employee", "Track", "Review reason", "Score", "Priority"]
        )
        self.table.setStyleSheet(table_style())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setMinimumHeight(520)
        enable_table_row_selection(self.table)
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tl.addWidget(self.table)
        layout.addWidget(table_card)
        layout.addSpacing(26)

        # Governance note
        info_card = QFrame()
        info_card.setStyleSheet(alert_ss("info"))
        il = QVBoxLayout(info_card)
        il.setContentsMargins(30, 24, 30, 24)
        il.setSpacing(10)
        info_head = QHBoxLayout()
        info_icon = QLabel()
        info_icon.setPixmap(app_pixmap("fa5s.info-circle", color=tokens().brand, size=18))
        info_title = QLabel("How to read this queue")
        info_title.setStyleSheet(
            f"font-size: 17px; font-weight: 800; color: {tokens().brand}; background: transparent;"
        )
        info_head.addWidget(info_icon)
        info_head.addWidget(info_title)
        info_head.addStretch()
        il.addLayout(info_head)
        for text in [
            "Rule findings are explicit policy or data contradictions with a stated reason.",
            "ML priority ranks residual histories that are unusual without being explicit violations.",
            "Data shown is synthetic development data, not real employees and not a locked holdout.",
            "Scores support a human decision; the system never changes a record automatically.",
        ]:
            item = QLabel("\u2022 " + text)
            item.setStyleSheet(
                f"font-size: 14px; color: {tokens().text_muted}; background: transparent;"
            )
            il.addWidget(item)
        layout.addWidget(info_card)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _add_stat_card(self, key, label, icon_name, color, bg):
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedHeight(96)
        card.setStyleSheet(card_ss("QFrame#Card"))
        cl = QHBoxLayout(card)
        cl.setContentsMargins(30, 0, 30, 0)
        cl.setSpacing(14)
        icon = QLabel()
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background: {bg}; border-radius: 8px;")
        icon.setPixmap(app_pixmap(icon_name, color=color, size=22))
        col = QVBoxLayout()
        col.setSpacing(0)
        col.setAlignment(Qt.AlignVCenter)
        title = QLabel(label)
        title.setStyleSheet(
            f"font-size: 14px; color: {tokens().text_muted}; background: transparent;"
        )
        value = QLabel("-")
        value.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {tokens().text}; background: transparent;"
        )
        col.addWidget(title)
        col.addWidget(value)
        cl.addWidget(icon)
        cl.addLayout(col)
        self.stats_row.addWidget(card)
        self.stat_values[key] = value

    # ----- data ---------------------------------------------------------
    def refresh(self):
        """Recompute the review queue from a fresh synthetic sample.

        All heavy work is intentionally small (a modest synthetic sample) and
        wrapped so a missing optional dependency never breaks the page.
        """
        self._rows = self._compute_review_rows()
        model_label = "Isolation Forest + rules" if sklearn_is_available() else "Rules only (sklearn absent)"
        if "model" in self.stat_values:
            self.stat_values["model"].setText(model_label)
        rule_count = sum(1 for r in self._rows if r["priority"] == "rule")
        ml_count = sum(1 for r in self._rows if r["priority"] != "rule")
        self.stat_values["reviewed"].setText(str(self._screened_count))
        self.stat_values["rule"].setText(str(rule_count))
        self.stat_values["flagged"].setText(str(ml_count))
        self._apply_filter()

    def _compute_review_rows(self):
        # A review-sized synthetic sample. We screen the whole generated sample
        # (not just the held-out test split) because this is decision-support
        # over a sample, not a locked-holdout evaluation. Data is synthetic.
        config = ExperimentConfig(
            seed=self._sample_seed,
            employee_count=240,
            anomaly_rate=0.12,
            rare_legitimate_rate=0.05,
        )
        dataset = generate_synthetic_dataset(config)
        records = list(dataset.records)
        self._screened_count = len(records)
        record_by_id = {r.identity.employee_id: r for r in records}

        rows = []
        rule_flagged_ids = set()

        # 1) Deterministic findings: structural contradictions plus fixed
        #    administrative-interval checks (validate_record), aggregated to one
        #    row per employee with its explained reason.
        reason_by_employee = {}
        for record in records:
            findings = validate_record(record)
            if not findings:
                continue
            # Prefer an ERROR-severity finding's message when present.
            chosen = next(
                (f for f in findings if f.severity is ValidationSeverity.ERROR),
                findings[0],
            )
            reason_by_employee[record.identity.employee_id] = chosen.message
            rule_flagged_ids.add(record.identity.employee_id)

        for employee_id, reason in reason_by_employee.items():
            record = record_by_id.get(employee_id)
            if record is None:
                continue
            rows.append({
                "employee_id": employee_id,
                "track": record.employment_track.value,
                "reason": reason,
                "score": None,
                "priority": "rule",
            })

        # 2) Isolation Forest ranking of residual (non-rule-flagged) records.
        residual = [r for r in records if r.identity.employee_id not in rule_flagged_ids]
        if sklearn_is_available() and len(residual) >= 16:
            try:
                train_records = [
                    r for r in records
                    if r.split is DatasetSplit.TRAIN
                    and r.identity.employee_id not in rule_flagged_ids
                ]
                train_vectors = [extract_policy_aware_features(r) for r in train_records]
                test_vectors = [extract_policy_aware_features(r) for r in residual]
                if train_vectors and test_vectors:
                    feature_names = tuple(test_vectors[0].values.keys())
                    result = run_isolation_forest(
                        train_vectors, test_vectors, feature_names,
                        contamination=0.1, random_state=self._sample_seed,
                    )
                    # decision_function: LOWER score = more anomalous. Rank the
                    # residual records most-anomalous first so the top of the
                    # queue is the highest review priority. predictions[i] is
                    # True when the model flags record i as an outlier.
                    ranked = sorted(
                        zip(residual, result.predictions, result.scores),
                        key=lambda triple: triple[2],
                    )
                    flagged = [t for t in ranked if t[1]]  # model-predicted anomalies
                    cutoff_high = max(1, len(flagged) // 3)
                    for index, (record, _pred, score) in enumerate(flagged):
                        if index < cutoff_high:
                            priority = "high"
                        elif index < 2 * cutoff_high:
                            priority = "medium"
                        else:
                            priority = "low"
                        # Present an intuitive anomaly score where higher means
                        # more suspicious (decision_function is the inverse).
                        rows.append({
                            "employee_id": record.identity.employee_id,
                            "track": record.employment_track.value,
                            "reason": "Unusual progression pattern (policy-aware ranking)",
                            "score": round(-float(score), 3),
                            "priority": priority,
                        })
            except IsolationForestUnavailableError:
                pass  # degrade to rules-only view
            except Exception:
                pass  # never let the research layer break the UI

        # Rule findings first, then by descending model score.
        rows.sort(key=lambda r: (r["priority"] != "rule", -(r["score"] or 0.0)))
        return rows

    # ----- rendering ----------------------------------------------------
    def _change_sample(self, _index):
        seed = self.sample_select.currentData()
        if seed is not None:
            self._sample_seed = int(seed)
            self.refresh()

    def _apply_filter(self, *_args):
        selected = self.priority_filter.currentData()
        if selected is None:
            visible = list(self._rows)
        else:
            visible = [r for r in self._rows if r["priority"] == selected]
        self.count_lbl.setText(
            f"Showing {len(visible)} of {len(self._rows)} review items "
            f"across {self._screened_count} screened histories."
        )
        self._populate(visible)

    def _populate(self, rows):
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        try:
            for row_index, row in enumerate(rows):
                self.table.setRowHeight(row_index, 52)

                emp = QTableWidgetItem(row["employee_id"])
                emp_font = emp.font()
                emp_font.setBold(True)
                emp.setFont(emp_font)
                self.table.setItem(row_index, 0, emp)

                track = QTableWidgetItem(row["track"])
                track.setForeground(QColor(tokens().text_muted))
                self.table.setItem(row_index, 1, track)

                reason = QTableWidgetItem(row["reason"])
                reason.setForeground(QColor(tokens().text_muted))
                reason.setToolTip(row["reason"])
                self.table.setItem(row_index, 2, reason)

                score_text = "-" if row["score"] is None else f"{row['score']:.3f}"
                score = QTableWidgetItem(score_text)
                score.setForeground(QColor(tokens().text_muted))
                self.table.setItem(row_index, 3, score)

                self.table.setCellWidget(row_index, 4, self._priority_badge(row["priority"]))
            sync_table_widget_cells(self.table)
        finally:
            self.table.setUpdatesEnabled(True)

    def _priority_badge(self, priority):
        label, fg, bg = _PRIORITY_META.get(priority, _PRIORITY_META["low"])
        wrap = QWidget()
        wl = QHBoxLayout(wrap)
        wl.setContentsMargins(8, 0, 8, 0)
        wl.setAlignment(Qt.AlignCenter)
        chip = QLabel(label)
        chip.setStyleSheet(badge_ss(bg, fg, radius=10, padding="3px 12px", font_size=12))
        wl.addWidget(chip)
        return wrap
