# MyHR: Policy-Aware Machine Learning for Anomaly Detection in Workforce Progression

MyHR is an offline desktop HR application (Python, PySide6, SQLite) and the
platform for a BME VIK TDK 2026 research project. The research asks whether
explicit workforce-progression policy context helps rank administrative errors
for human review better than raw administrative features, without raising
false alerts on unusual but lawful histories.

**Current result.** No policy-aware advantage has been demonstrated. In the
audited 12-scenario development artifact the policy-aware minus raw recall
difference was +0.0278 (95% CI −0.0278 to +0.1019), and in a later
900-scenario diagnostic wrong-policy features reproduced about 82% of the
apparent gain. All evidence is development evidence; the protocol is a draft
and the final holdout is locked and has never been generated or accessed.
Anomaly scores support human review only and never change personnel records.

![MyHR demo: employee performance page, then Anomaly Review queue, evidence, method comparison and synthetic evaluation](docs/media/demo/myhr_demo.gif)

*27.7-second recording of the real application with synthetic data
([MP4](docs/media/demo/myhr_demo.mp4), [provenance](docs/media/demo/myhr_demo.provenance.json)).*

> **Video walkthrough:** _placeholder, to be added by the author._

## Paper and research materials

| Material | Link |
| --- | --- |
| Paper source (English, supervisor review draft) | [docs/TDK_PAPER_DRAFT.md](docs/TDK_PAPER_DRAFT.md) |
| Figures (PDF/SVG/PNG) and their data provenance | [docs/figures/](docs/figures/README.md), [FIGURE_MANIFEST.json](docs/figures/FIGURE_MANIFEST.json) |
| LaTeX booktabs tables | [docs/tables/](docs/tables/README.md) |
| Experiment protocol (draft) | [docs/TDK_EXPERIMENT_PROTOCOL.md](docs/TDK_EXPERIMENT_PROTOCOL.md) |
| Research handover | [docs/RESEARCH_HANDOVER.md](docs/RESEARCH_HANDOVER.md) |
| Roadmap and decision log | [docs/TDK_AUTONOMOUS_RESEARCH_ROADMAP.md](docs/TDK_AUTONOMOUS_RESEARCH_ROADMAP.md) |
| Supervisor brief | [docs/TDK_SUPERVISOR_BRIEF_2026-10-30.md](docs/TDK_SUPERVISOR_BRIEF_2026-10-30.md) |
| Package verification record | [docs/TDK_SUPERVISOR_PACKAGE_VERIFICATION_2026-11-01.md](docs/TDK_SUPERVISOR_PACKAGE_VERIFICATION_2026-11-01.md) |
| Citation audit and bibliography | [docs/TDK_CITATION_AUDIT_2026-11-01.md](docs/TDK_CITATION_AUDIT_2026-11-01.md), [docs/TDK_REFERENCES.bib](docs/TDK_REFERENCES.bib) |
| Submission requirements | [docs/TDK_2026_SUBMISSION_REQUIREMENTS.md](docs/TDK_2026_SUBMISSION_REQUIREMENTS.md) |

The rendered PDF and Word versions of the paper are built by
`scripts/generate_tdk_supervisor_package.py` into a dated folder outside the
repository (`../TDK/final/`), so earlier versions are never overwritten.

## Screenshots

All screenshots are captures of the running application with synthetic data.
Provenance (revision, window size, theme, SHA-256) is stored next to each image.

| Review Queue | Employee Evidence |
| --- | --- |
| ![Review queue](docs/media/screenshots/anomaly_queue_light.png) | ![Employee evidence](docs/media/screenshots/anomaly_evidence_light.png) |
| **Method Comparison** | **Synthetic Evaluation** |
| ![Method comparison](docs/media/screenshots/anomaly_comparison_light.png) | ![Synthetic evaluation](docs/media/screenshots/anomaly_evaluation_light.png) |

Employee profile (Performance tab): [light](docs/media/screenshots/employee.png),
[dark](docs/media/screenshots/employee_dark.png). Dark-theme Anomaly Review
captures are in [docs/media/screenshots/](docs/media/screenshots/).

## Run the demonstration

```bash
pip install -r requirements.txt -r requirements-research.txt
python scripts/seed_demo_company.py     # optional: reset to the synthetic demo company
python main.py
```

Sign in with the local demo account listed under [Demo accounts](#demo-accounts),
then:

1. **Employees**: search `Peter Ahmed` and open the **Performance** tab.
2. **Anomaly Review** (sidebar): choose a demonstration scenario and select
   **Run analysis**.
3. **Review Queue**: select a row and open **Employee Evidence** to see the
   policy calculation and source history for the same synthetic employee.
4. **Method Comparison**: raw, policy-aware, wrong-policy and shuffled-policy
   representations at the same review capacity, with recall/precision and
   true/false-positive charts derived from the same completed run.
5. **Synthetic Evaluation**: generated truth, shown only here.
6. **Help** opens an optional guide on the right; **Export report** writes CSV or PDF.

The demonstration is not a research experiment: it uses three fixed scenarios
of 120 synthetic employees each and reads no employee database records. Verify
all three scenarios from the command line with:

```bash
python scripts/verify_anomaly_demo.py
```

## Reproduce the research outputs

```bash
python -m unittest discover -s tests                      # full test suite
python scripts/verify_tdk_citations.py --require-local-artifact
python -m scripts.audit_tdk_protocol_artifact research_outputs/independent_development/independent_development_4feea4508de1bb05
python scripts/build_tdk_figures.py                       # figures, tables, manifest
```

`research_outputs/` holds write-once artifacts and is not tracked in Git; the
artifact IDs, checksums and source revisions are recorded in the paper and the
figure manifest. `build_tdk_figures.py` checks the paper's numbers against the
artifact CSVs and needs Graphviz (`MYHR_DOT_EXE` can point to `dot.exe`). The
demo recording is reproduced with `scripts/record_readme_demo.py` and
`scripts/make_readme_demo_media.py` (PyAutoGUI, FFmpeg, gifski).

No holdout command exists. The protocol runner refuses a holdout run until a
human-approved protocol freeze.

## Demo accounts

Local, seeded accounts for the offline demo database only:

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `admin123` |
| HR Officer | `hr_officer` | `hr123` |

## Application features

- Employee records, profiles, rubric-based performance reviews, search and filters.
- Organization hierarchy canvas (organization, division, department, unit, team, position).
- Promotion race calculated from source records: commendations shorten the
  required service, sanctions delay it, promotions reset it.
- Annual salary increments, independent of promotion, with an approval workflow.
- Commendations, sanctions, immutable audit log, CSV/XLSX import, exports,
  yearly PDF reports, SQLite backup.
- Light and dark themes; English, Hungarian and Arabic.
- Role-based access: Settings, user management, export and backup are admin-only.

## Development

```bash
python -m py_compile main.py
python -m unittest discover -s tests
```

New dropdowns must use `src.ui.components.app_select.AppSelect`
(`docs/UI_RULES.md`, enforced by `tests/test_ui_component_policy.py`). Release
checks are in `docs/QA_CHECKLIST.md`; architecture follow-ups in
`docs/ARCHITECTURE_ROADMAP.md`. The `MockUI/` folder is the original React/Vite
design reference and is not needed to run the app.

| Layer | Technology |
| --- | --- |
| Language | Python 3.12+ |
| UI | PySide6 / Qt 6 |
| Data | SQLite, SQLAlchemy 2.0 |
| Research | scikit-learn, pandas, Matplotlib, Graphviz |

## Branches

| Branch | Purpose |
| --- | --- |
| `master` | Project Laboratory submission |
| `thesis` | Verified working application |
| `research` | Research pipeline, working application and Anomaly Review |

## People and licence

Developer: Muhammad Ibrahim Shoeb. Supervisor: Dr. Husam Al-Magsoosi.
Budapest University of Technology and Economics, Faculty of Electrical
Engineering and Informatics.

Academic project, 2025–2026. No open-source licence has been chosen yet; see
[docs/LICENSING_AND_IP.md](docs/LICENSING_AND_IP.md). Citation metadata:
[CITATION.cff](CITATION.cff). Governance: `SECURITY.md`, `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `SUPPORT.md`.
