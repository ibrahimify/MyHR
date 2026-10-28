# Temporary Asset Review

Status: **inventory only - no files removed**

Recorded: 2026-10-29

This inventory separates tracked UI-review captures from research evidence. The
directories below predate the research branch, are already covered by the
`tmp_*` ignore rule for new files, and are not referenced by the application,
tests, scripts, or tracked documentation.

| Tracked path | Files | Bytes | Unique file hashes | Tracked references |
| --- | ---: | ---: | ---: | ---: |
| `tmp_audit/` | 15 | 388,842 | 11 | 0 |
| `tmp_chart_audit/` | 80 | 3,998,724 | 78 | 0 |
| `tmp_icon_audit_import/` | 8 | 191,769 | 8 | 0 |
| `tmp_icon_quality_sheet.png` | 1 | 27,174 | 1 | 0 |
| `tmp_profile_audit/` | 36 | 4,032,431 | 35 | 0 |
| `tmp_ui_audit/` | 9 | 562,779 | 9 | 0 |
| `tmp_ui_audit_pages/` | 9 | 961,360 | 9 | 0 |
| `tmp_ui_audit_tabs/` | 15 | 705,704 | 15 | 0 |
| **Total** | **173** | **10,868,783** | **163 across all paths** | **0** |

## Recommendation

1. Keep this maintenance change non-destructive. Do not remove or relocate the
   captures as part of research PR #1.
2. Review the captures visually and nominate any images that remain useful as
   durable UI evidence. Copy only approved examples to `docs/media/` with a
   short provenance note.
3. After explicit maintainer approval, remove the remaining tracked temporary
   files in a separate housekeeping PR. Their Git history will remain
   recoverable, but removal from the current tree is still treated as a
   destructive operation requiring approval.
4. Keep the existing `tmp_*` ignore rule so future visual test output remains
   local unless deliberately promoted to documentation.

This review does not classify or modify `research_outputs/`; research artifacts
follow the stricter preservation process documented separately.
