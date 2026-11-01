"""Capture reproducible MyHR screenshots using only synthetic demo records."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "docs" / "media" / "screenshots",
    )
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import src.database.connection as db
    from src.database.models import Base, Employee, SystemUser

    with tempfile.TemporaryDirectory(prefix="myhr_tdk_screenshot_") as directory:
        database_path = Path(directory) / "synthetic_demo.db"
        engine = create_engine(f"sqlite:///{database_path}", echo=False)
        session_factory = sessionmaker(bind=engine)
        db.engine = engine
        db.SessionLocal = session_factory
        Base.metadata.create_all(engine)

        import scripts.seed_demo_company as demo

        demo.engine = engine
        demo.SessionLocal = session_factory
        demo.main()
        with session_factory() as session:
            db._seed_demo_performance_reviews(session)
            session.commit()
            admin = session.query(SystemUser).filter_by(username="admin").one()
            employee = session.query(Employee).filter_by(employee_id="EMP-0034").one()
            user = SimpleNamespace(
                id=admin.id,
                username=admin.username,
                role=admin.role,
                full_name=admin.full_name,
            )
            employee_db_id = employee.id

        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QScrollArea, QTabWidget
        from src.ui.main_window import MainWindow
        from src.ui.theme import apply_theme, theme_manager

        app = QApplication.instance() or QApplication([])
        app.setStyle("Fusion")
        theme_manager.set_theme(args.theme, persist=False)
        apply_theme(app)
        window = MainWindow(user)
        window.showNormal()
        window.resize(args.width, args.height)
        window.show()
        QTest.qWait(250)

        employees_page = window._get_page("employees")
        window.stack.setCurrentWidget(employees_page)
        window.sidebar._set_active("employees")
        employees_page._show_profile(employee_db_id)
        tabs = employees_page.profile_page.findChild(QTabWidget)
        if tabs is None or tabs.count() < 2:
            raise RuntimeError("Employee performance tab was not constructed")
        tabs.setCurrentIndex(1)
        QTest.qWait(350)

        employee_name = "employee.png" if args.theme == "light" else "employee_dark.png"
        image_path = args.output_dir / employee_name
        if not window.grab().save(str(image_path), "PNG"):
            raise RuntimeError(f"Could not save screenshot: {image_path}")

        anomaly_page = window._get_page("anomaly_review")
        window.stack.setCurrentWidget(anomaly_page)
        window.sidebar._set_active("anomaly_review")
        # Capture is deterministic and synchronous; the interactive QThread path
        # is exercised separately by the end-to-end UI smoke test.
        from src.services.anomaly_detection import run_demo_scenario

        result = run_demo_scenario(0, employee_count=120)
        anomaly_page._on_completed(result)
        app.processEvents()
        QTest.qWait(300)

        anomaly_paths = []
        anomaly_scroll = anomaly_page.findChild(QScrollArea)
        for tab_index, name in (
            (0, "queue"),
            (1, "evidence"),
            (2, "comparison"),
            (3, "evaluation"),
        ):
            anomaly_page.tabs.setCurrentIndex(tab_index)
            QTest.qWait(120)
            if anomaly_scroll is not None:
                anomaly_scroll.verticalScrollBar().setValue(285 if tab_index == 1 else 0)
            QTest.qWait(180)
            path = args.output_dir / f"anomaly_{name}_{args.theme}.png"
            if not window.grab().save(str(path), "PNG"):
                raise RuntimeError(f"Could not save screenshot: {path}")
            anomaly_paths.append(path)
        window.close()
        app.processEvents()
        engine.dispose()

    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    digest = sha256(image_path.read_bytes()).hexdigest()
    provenance = {
        "capture_type": "reproducible_offscreen_application_window",
        "source_revision": revision,
        "database": "temporary synthetic dataset from scripts/seed_demo_company.py",
        "employee": "EMP-0034",
        "view": "Employees > employee profile > Performance",
        "viewport": {"width": args.width, "height": args.height},
        "theme": args.theme,
        "contains_private_data": False,
        "sha256": digest,
    }
    employee_provenance_name = (
        "employee.provenance.json"
        if args.theme == "light"
        else "employee_dark.provenance.json"
    )
    provenance_path = args.output_dir / employee_provenance_name
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )
    anomaly_provenance = {
        "capture_type": "reproducible_offscreen_application_window",
        "source_revision": revision,
        "database": "none; fixed synthetic research scenario generated in memory",
        "scenario": anomaly_page.result.scenario.scenario_id,
        "view": (
            "Anomaly Review > queue, evidence, equal-capacity comparison, "
            "and synthetic evaluation"
        ),
        "viewport": {"width": args.width, "height": args.height},
        "theme": args.theme,
        "contains_private_data": False,
        "holdout_accessed": False,
        "files": {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in anomaly_paths
        },
    }
    anomaly_provenance_path = args.output_dir / f"anomaly_{args.theme}.provenance.json"
    anomaly_provenance_path.write_text(
        json.dumps(anomaly_provenance, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "employee_image": str(image_path),
        "anomaly_images": [str(path) for path in anomaly_paths],
        "anomaly_provenance": anomaly_provenance,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
