# MyHR UI Redesign Spec — For Claude Code
# Created from Figma mockup screenshots and user feedback
# Date: April 29, 2026


This file ONLY defines UI/UX rules.
For logic, always refer to context.md.
## CRITICAL RULES
- Use `qtawesome` for ALL icons (already installed)
- NO emoji icons anywhere — only qtawesome
- ALL text must be visible (color: #111827 on white backgrounds)
- NO colored card backgrounds (no yellow/green/pink fills) — use subtle left-border accents only
- Labels must sit DIRECTLY above their inputs with 4px gap max
- Cards use `background: white; border-radius: 10px; border: 1px solid #e5e7eb;` — no double borders
- QMessageBox must have dark text on white background (handled in main.py global stylesheet)
- Currency inputs: UPPERCASE only, max 3 characters (e.g. EUR, HUF, INR)
- Back buttons: "← Back to Employees" style breadcrumb with qtawesome arrow icon, not a floating text
- Sidebar icons: use qtawesome icons matching the Figma mockup exactly

## GLOBAL STYLESHEET (main.py)
```
QWidget { color: #111827; }
QLabel  { color: #111827; background: transparent; }
QLineEdit, QTextEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    color: #111827; background: white;
    border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 0 12px; font-size: 13px; min-height: 38px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border-color: #2563eb;
}
QTableWidget { color: #111827; background: white; border: none; }
QTableWidget::item { border-bottom: 1px solid #f3f4f6; padding: 10px 14px; }
QHeaderView::section {
    background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb;
    padding: 10px 14px; font-size: 12px; font-weight: 600; color: #6b7280;
}
QMessageBox { background: white; color: #111827; }
QMessageBox QLabel { color: #111827; }
QTabWidget::pane { border: none; background: #f9fafb; }
QTabBar::tab {
    background: white; color: #6b7280; padding: 10px 20px;
    border: 1px solid #e5e7eb; border-bottom: none;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-size: 13px; margin-right: 2px;
}
QTabBar::tab:selected { color: #111827; font-weight: 600; background: white; border-bottom: 2px solid white; }
QTabBar::tab:!selected { background: #f9fafb; }
```

## SIDEBAR (main_window.py)
Icons to use (qtawesome):
- Dashboard:     fa5s.th-large
- Employees:     fa5s.users
- Org Hierarchy: fa5s.sitemap
- Promotions:    fa5s.chart-line
- Commendations: fa5s.award
- Sanctions:     fa5s.exclamation-triangle
- Audit Log:     fa5s.clipboard-list
- Import Data:   fa5s.cloud-upload-alt
- Settings:      fa5s.cog
- Logout:        fa5s.sign-out-alt

Bottom of sidebar:
- User avatar circle with initials (already done by Claude Code)
- "Admin User" bold, "Administrator" subtitle below
- Logout button with icon

Active nav item: left-3px blue accent bar + light blue background (#eff6ff) + blue text (#2563eb)
Inactive: transparent background, #6b7280 text

## LOGIN PAGE
- Clean centered card, max-width 420px
- Logo: blue rounded square with clipboard icon (qtawesome fa5s.clipboard-list)
- "MyHR" title, "Employee Management" subtitle
- Language selector: dropdown with flag labels (🇬🇧 English, 🇭🇺 Magyar, 🇸🇦 العربية)
- Username field with user icon (fa5s.user) as left addon
- Password field with lock icon (fa5s.lock) as left addon  
- "Sign In" button: black background (#030213), white text, full width
- Footer: "Authorized Personnel Only" + Admin/HR Officer indicators

## DASHBOARD PAGE
Layout from top to bottom:
1. Header: "Dashboard" title + "Organization overview" subtitle
2. Quick action buttons: [+ Add Employee] black filled, [Import Data] outline
3. Salary increment alert banner (yellow) if employees are due — with "Review Increments" button
4. Stat cards row (4 cards):
   - Total Employees — blue icon (fa5s.users) on right side in colored circle
   - Pending Promotions — green icon (fa5s.chart-line)
   - Commendations (This Month) — yellow icon (fa5s.award)  
   - Active Sanctions — red icon (fa5s.exclamation-triangle)
   - Each card: label on top, big number below, icon circle on RIGHT side
5. Two-column section:
   Left: "Recent Activities" card
   - Each entry: bold action title, description line, "by Username" line, timestamp on right
   - Blue dot indicator on left
   Right: "Upcoming Eligible Promotions" card  
   - Each entry: employee name, "L7 → L6" transition, progress bar, "X days" badge, "XX% complete" text
   - Pull from actual DB data using calculate_months_remaining()

## EMPLOYEES LIST PAGE
Header: "Employee Management" + "Manage and view all employee records"
Filter bar: Search input with magnifier icon | Department filter | Status filter | [Export] outline button | [+ Add Employee] black button
Table columns: Employee ID | Name | Email | Department (badge) | Position | Level (colored badge) | Status (colored badge) | Actions (icon buttons)
Action buttons: eye icon (view), pencil icon (edit), trash icon (delete) — all as small icon-only buttons
Show "Showing X of Y employees" count above table

## EMPLOYEE PROFILE PAGE
Breadcrumb: "← Back to Employees" (qtawesome fa5s.arrow-left + text, looks like a link)
Profile header card:
- Blue circle avatar with initials (large, 80px)
- Name (large bold) + Active badge (green) + Level badge (blue)
- Position title below name
- Info row: email icon + email, phone icon + phone, location icon + address, calendar icon + join date
- "Edit Profile" button top right (black, with pencil icon)

Tab bar below profile card: Personal Details | Promotion History | Commendations | Sanctions

Personal Details tab (default):
- Two column layout:
  Left card: "Employment Information" — Employee ID, Department, Position, Level, Base Salary, Reporting To, Join Date
  Right card: "Personal Information (Admin Only)" with red badge — Full Name, Email, Phone, Address, Degree, Base Salary
- Each field: label above, value in read-only input-like container with bottom border only

Promotion History tab:
- List of promotion entries as cards
- Each: green trend icon, "Promoted from LX to LY", reason text, date on right
- Bottom entry: "Initial Position" with "Initial hire (degree)" text

Commendations tab:
- Show commendation cards for this employee only
- Award title, category badge, date, impact months

Sanctions tab:
- Show sanctions for this employee only
- Type badge (colored), reason, delay months, status

## ORG HIERARCHY PAGE
Header: "Organization Hierarchy" + "View and manage the organizational structure"
Controls: Search input | [Add Department] outline button | [+ Add Unit] blue button
Legend bar: colored dots for Organization (purple), Division (orange), Department (blue), Unit (green), Team (gray)
Tree view:
- Each node is a card with subtle colored left border matching its type
- Node content: type icon + name + [type] badge + "Head: Name" + "XX employees"
- On hover: show +, edit, delete icon buttons on the right
- Indentation with vertical connecting lines
- Expandable/collapsible with chevron icons

## PROMOTIONS PAGE
Header: "Promotion Management" + "Manage promotion rules and track employee eligibility"
Tabs: Eligible Employees | Promotion History | Promotion Rules

Eligible Employees tab:
- 3 stat cards: Eligible Now (green check icon), Eligible Soon (yellow clock), In Progress (blue chart)
- "Employee Promotion Tracker" table:
  Columns: Employee (name + EMP-ID), Current Level (badge), Next Level (badge), Years in Level, Commendations, Eligible Date, Progress (bar with %), Actions
  - If eligible: green "Approve" button + gray "Defer" button
  - If not: "View Details" text button
  - Progress bar colors: green (100%), yellow (60-99%), blue (<60%)

Promotion History tab:
- Table: Employee | Promotion (L7 → L6 with trend icon) | Date | Approved By | Reason
- Clean simple table

Promotion Rules tab:
- "Promotion Track Configuration" title + "Edit Rules" button top right
- Blue info card: "How the Promotion Race Works" with bullet points
- For each level transition (L7→L6, L6→L5, etc):
  - Clean card with trend icon + "LX → LY" title
  - Two fields side by side: "Base Track Duration (months)" and "Base Salary Increase"
  - Subtitle hints under each field

## COMMENDATIONS PAGE
Tabs: Issue Commendation | Commendation History

Issue Commendation tab:
Layout: left form (70%) + right sidebar (30%)

Left side:
- "Commendation Type" card with two big selectable boxes:
  - Single Employee (person icon, "Issue to one employee")
  - Team Award (people icon, "Issue to multiple employees")
  - Selected = blue border, unselected = gray border
- "Commendation Details" card:
  - Award Title* input
  - Commendation Category* dropdown with hint "Higher categories accelerate promotion race more"
  - Description* textarea
- "Select Employee" / "Select Employees" card:
  - Single mode: dropdown
  - Team mode: checkbox list with "X selected" badge top right
  - Each employee: Name bold + "Position - Department" subtitle

Right sidebar:
- "Promotion Track Impact" card (blue left border):
  - Category 1: green text, "−1 month" badge
  - Category 2: blue text, "−3 months" badge  
  - Category 3: purple text, "−6 months" badge
  - Description under each
- "Actions" card:
  - "Issue Commendation" primary button (blue)
  - "Clear Form" outline button
- "Important Rules" card (yellow left border):
  - Max 3 commendations per employee per role
  - Each gets unique auto-generated ID
  - Visible in employee profile & audit log
  - Can be used for performance reviews

Commendation History tab:
- NOT a table — card-based layout
- Each commendation as a card:
  - Award icon (yellow) + Title bold + COM-ID badge (gray)
  - Description text
  - Calendar icon + date + "Issued by Name"
  - Badges: Team/Individual (blue/green) + Category X (colored) + "−X months" (green with clock icon)
  - "Recipients:" section with name badges

## SANCTIONS PAGE  
Tabs: Active Sanctions | Sanction History | Issue Sanction

Active Sanctions tab:
- 3 stat cards: Active Sanctions (red icon), Expiring Soon (yellow), Resolved This Month (green)
- "Current Active Sanctions" table:
  Columns: Sanction ID | Employee (name + EMP-ID) | Type (colored badge) | Reason | Issue Date | Promotion Delay (red "+X months" with clock icon) | Issued By | Actions
  - "Mark Resolved" outline button in actions

Issue Sanction tab:
Layout: left form (65%) + right sidebar (35%)
Left:
- "Issue New Sanction" card:
  - Select Employee* dropdown
  - Sanction Type* dropdown
  - Reason/Description* textarea
  - Issue Date* + Promotion Delay (months)* side by side
Right sidebar:
- "Actions" card: Issue Sanction (red button) + Clear Form
- "Promotion Race Impact" card (red left border): bullet points about how sanctions work
- "Important Notes" card (yellow left border): audit log, notification, documentation notes
- "Sanction Guidelines" card: verbal warning 1-2mo, written 3-6mo, suspension 6-9mo, final 9-12mo

## AUDIT LOG PAGE
Header: "Audit Log" + "Complete record of all system activities and changes"
Stat cards (4): Total Logs (blue) | Today's Activities (green) | This Week (blue) | Most Active User (yellow, shows name)
Filter bar: Search input with magnifier | Category filter dropdown | User filter dropdown | [Export] button
Table columns: Timestamp | User (with person icon) | Action | Target | Details | Category (colored badge)
Category badge colors:
- Employee Management: blue
- Promotions: green  
- Commendations: yellow
- Sanctions: red
- Data Import: teal
- Settings: gray
- Hierarchy: indigo
Footer note: lock icon + "Audit logs are immutable — they cannot be modified or deleted."

## IMPORT DATA PAGE
Header: "Import Employee Data" + "Bulk import employee records from CSV or Excel files"
Step wizard bar: [1. Upload File] → [2. Validate Data] → [3. Complete] — active step = blue circle + blue text
Layout: left content (70%) + right sidebar (30%)
Left:
- Upload area: dashed border card, upload cloud icon (large, in blue circle), "Upload Employee Data File", "Supported formats: CSV, XLSX", [Choose File] button
- Separator line
- [Download Template File] outline button + "Use our template to ensure proper formatting"
Right sidebar:
- "Required Columns" info card (blue left border): First Name, Last Name, Email, Department, Position, Degree, Join Date
- "Data Cleaning Guide" card (yellow left border): tips list

After upload — show preview table with valid/error status per row, then Import button

## SETTINGS PAGE
Tabs: General | Salary Ranges | Promotion Rules | Notifications | Security

General tab:
- "Organization Information" card with building icon
- Fields: Company Name, Company Address (side by side), Fiscal Year Start (MM-DD), Timezone (side by side)
- "Save General Settings" button bottom right

Salary Ranges tab:
- "Salary Range Configuration" card with dollar icon
- Currency field at top (single input, uppercase, 3 char max)
- "Annual Salary Increment" section with green left border:
  - Increment Type dropdown + Percentage/Fixed value input side by side
  - Example text in italic
- For each level (L7-L3):
  - Card with colored level badge (L7 blue, L6 green, L5 yellow, L4 purple, L3 red) + "Entry Level (BSc)" label
  - Min Salary input + EUR badge + Max Salary input + EUR badge
- "Save Salary Ranges" button

Promotion Rules tab:  
- "Promotion Eligibility Rules" card with trend icon
- For each transition (L7→L6, L6→L5, L5→L4):
  - Card with subtle colored left border
  - Title: "LX → LY Promotion" in color
  - Two fields: "Years Required in Level" + "Commendations Required" 
  NOTE: We use BASE MONTHS not years, and commendations are NOT required — they're optional modifiers
  So use: "Base Track Duration (months)" and remove "Commendations Required" — show note that commendations/sanctions are optional modifiers
- "Auto-Reset Commendations After Promotion" toggle with explanation
- "Save Promotion Settings" button

Security tab:
- "Change Password" section
- "Security Information" bullets

Database tab (within Security or separate):
- Database Backup card with button
- Export All Data card with button

## LOGIC FIXES TO APPLY DURING REDESIGN
1. Dashboard "Upcoming Eligible Promotions" must pull real data from DB
2. Commendation: selecting maxed-out employee in single mode should say "This employee has reached max 3 commendations" not "Please select an employee"
3. Audit log: action column must show human-readable text like "Employee Added" not "1"
4. Settings page must not have colored card backgrounds — use left-border accents only
5. Currency input must force uppercase and limit to 3 characters
6. All back buttons must be breadcrumb-style with arrow icon
7. Employee delete must exist with confirmation dialog
8. All dialog boxes must have dark text (handled by global stylesheet)

## RECENT CORRECTIONS
- Do not use unsupported alpha hex colors like `#dbeafe40` in Qt stylesheets; they render badly. Use white cards with subtle borders and small colored badges/left accents.
- `QFrame QLabel { border: none; }` is required globally to avoid child labels inheriting card borders.
- Spinbox arrows are hidden globally; salary/increment inputs should look like clean text fields.
- Company branding comes from `src/core/app_settings.py` and must appear on login + sidebar.
- Org hierarchy uses card rows with qtawesome icons and inline plus/edit/delete icon buttons.
- Avoid textual arrows like `->` in user-facing UI; use words like "to" or qtawesome icons.

## QTAWESOME ICON REFERENCE
```python
import qtawesome as qta

# Usage in buttons:
btn.setIcon(qta.icon("fa5s.arrow-left", color="#2563eb"))

# Usage in labels:
lbl.setPixmap(qta.icon("fa5s.users", color="#2563eb").pixmap(20, 20))

# Common icons needed:
# fa5s.th-large (dashboard)
# fa5s.users (employees/team)  
# fa5s.user (single person)
# fa5s.user-plus (add employee)
# fa5s.sitemap (hierarchy)
# fa5s.chart-line (promotions/trends)
# fa5s.award (commendations)
# fa5s.exclamation-triangle (sanctions/warnings)
# fa5s.clipboard-list (audit log)
# fa5s.cloud-upload-alt (import)
# fa5s.cog (settings)
# fa5s.sign-out-alt (logout)
# fa5s.arrow-left (back)
# fa5s.eye (view)
# fa5s.edit (edit/pencil)
# fa5s.trash-alt (delete)
# fa5s.plus (add)
# fa5s.search (search)
# fa5s.filter (filter)
# fa5s.download (download/export)
# fa5s.save (save)
# fa5s.check-circle (success/approve)
# fa5s.times-circle (decline/defer)
# fa5s.info-circle (info)
# fa5s.lock (password/security)
# fa5s.database (database)
# fa5s.file-csv (csv)
# fa5s.building (organization)
# fa5s.envelope (email)
# fa5s.phone (phone)
# fa5s.map-marker-alt (location)
# fa5s.calendar-alt (date)
# fa5s.graduation-cap (degree)
# fa5s.dollar-sign (salary/money)
# fa5s.clock (time/expiring)
```

## FILE LIST TO MODIFY
1. main.py — global stylesheet update
2. src/ui/main_window.py — sidebar icons + breadcrumb support
3. src/ui/login_window.py — icon inputs + cleaner layout
4. src/ui/pages/dashboard.py — full redesign
5. src/ui/pages/employees.py — table redesign + profile tabs + edit
6. src/ui/pages/hierarchy.py — colored cards + hover actions
7. src/ui/pages/promotions.py — stat cards + tracker + rules
8. src/ui/pages/commendations.py — form layout + card history
9. src/ui/pages/sanctions.py — stat cards + form + guidelines
10. src/ui/pages/audit_log.py — stat cards + category badges
11. src/ui/pages/import_data.py — step wizard + upload area
12. src/ui/pages/settings.py — all tabs redesigned




# MAKE NO MISTAKE, CODEX WILL CHECK YOUR CODE AFTER YOU FIX THIS
