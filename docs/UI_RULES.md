# MyHR UI Rules

These rules protect the visual consistency of the desktop app.

## Dropdowns

All dropdown-style controls in application pages must use `AppSelect` from:

```python
from src.ui.components.app_select import AppSelect
```

Do not create new `QComboBox` widgets in the UI. Do not create another page-local custom dropdown with its own popup, colors, or animation.

Why:

- `AppSelect` matches the login and audit dropdown behavior.
- It keeps light/dark colors consistent.
- It provides the shared fade/slide popup animation.
- It avoids every page drifting into a different dropdown style.

Allowed:

- Direct `AppSelect(...)` usage.
- Thin compatibility wrappers that subclass `AppSelect`, only when older page code needs extra signals.

Not allowed:

- `QComboBox(...)`
- New standalone `class SomethingSelect(QWidget)` dropdowns.
- Page-local `QListWidget` popup dropdown styling.

The rule is enforced by `tests/test_ui_component_policy.py`.
