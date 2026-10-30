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
        from PySide6.QtWidgets import QApplication, QTabWidget
        from src.ui.main_window import MainWindow
        from src.ui.theme import apply_theme

        app = QApplication.instance() or QApplication([])
        app.setStyle("Fusion")
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

        image_path = args.output_dir / "employee.png"
        if not window.grab().save(str(image_path), "PNG"):
            raise RuntimeError(f"Could not save screenshot: {image_path}")
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
        "theme": "light",
        "contains_private_data": False,
        "sha256": digest,
    }
    provenance_path = args.output_dir / "employee.provenance.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"image": str(image_path), "provenance": provenance}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
