from PySide6.QtCore import QEasingCurve, QPoint, QParallelAnimationGroup, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect


def animate_widget_entry(widget, *, duration=190, offset=8):
    """Subtle page entry animation for stacked pages and tab contents."""
    if widget is None:
        return

    current = getattr(widget, "_myhr_entry_animation", None)
    if current is not None:
        current.stop()

    def start():
        end_pos = widget.pos()
        start_pos = end_pos + QPoint(0, offset)

        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        if offset:
            widget.move(start_pos)

        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(duration)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(widget)
        group.addAnimation(fade)
        if offset:
            slide = QPropertyAnimation(widget, b"pos")
            slide.setDuration(duration)
            slide.setStartValue(start_pos)
            slide.setEndValue(end_pos)
            slide.setEasingCurve(QEasingCurve.OutCubic)
            group.addAnimation(slide)

        def finish():
            widget.move(end_pos)
            widget.setGraphicsEffect(None)
            widget._myhr_entry_animation = None

        group.finished.connect(finish)
        widget._myhr_entry_animation = group
        group.start()

    QTimer.singleShot(0, start)


def install_tab_transition(tab_widget, *, duration=180, offset=7):
    """Attach a restrained entry animation to QTabWidget page changes."""
    if getattr(tab_widget, "_myhr_tab_transition_installed", False):
        return

    tab_widget.currentChanged.connect(
        lambda index: animate_widget_entry(
            tab_widget.widget(index),
            duration=duration,
            offset=offset,
        )
    )
    tab_widget._myhr_tab_transition_installed = True
