Okay, balancing simple af + modern looking + sellable + no licensing issues...
I'm switching my answer to CustomTkinter.
Here's why:

DearPyGui is modern and fast but the learning curve will slow you down when you just want to meet requirements cleanly
CustomTkinter is dead simple to build with, looks genuinely modern, pure Python, MIT licensed
For 5000 records with SQLite + SQLAlchemy, it handles it fine
Your professor doesn't care if it's GPU-rendered

For the thesis extension — same stack, just add more features on top. No need to switch anything.
Final simple stack:
LayerChoiceUICustomTkinterDBSQLiteORMSQLAlchemyVersion ControlGitHubLanguagePython
Simple, professional, sellable, zero drama. Done.in 3 different commands, you chose 3 different UI recommendations: now i am confused,.Mar 24Acknowledged flip-flopping, reconciled constraints, settled on CustomTkinterAcknowledged flip-flopping, reconciled constraints, settled on CustomTkinterYou're right, that's on me. Let me be straight with you.
Every time you added a new constraint I switched. That's not helpful. Here's the honest reconciliation of all your constraints together:

Simple af ✅
Modern looking ✅
No licensing issues ✅
Sellable ✅
Python ✅
Thesis-extendable ✅

CustomTkinter wins when ALL constraints are on the table simultaneously.
DearPyGui is better technically but contradicts "simple af." PySide6 has the licensing noise you don't want. CustomTkinter is the only one that satisfies everything at once without trade-offs that hurt you.
I'm not changing this answer again. Go with CustomTkinter.okay, one liner reply please: if i use Custom Tkinter or flet or pyside 6, which will help me in job if i show it in my resume? also i have a job and uni with 30 credits and this is one of the course. so i have 2 months to do all which one would you choose: next sem will be thesis extending this. so consider this also in mind. You can reply to each question in one to 2 linesMar 24Recognized user's preference for concise, structured responsesRecognized user's preference for concise, structured responsesResume value: PySide6 wins on resume, Qt is an industry skill. Neither Flet nor CustomTkinter means anything to a hiring manager.
Given 2 months, job + 30 credits: CustomTkinter — you'll spend zero time fighting the framework and just build.
Thesis extension: Same CustomTkinter stack holds up fine, no need to switch.
My pick for YOUR situation: CustomTkinter. Resume doesn't matter if you don't finish the project.how hard will it be if I choose PySide 6? if i work with you?Mar 24Gauged PySide6 difficulty and collaboration potentialGauged PySide6 difficulty and collaboration potentialHonestly? Not that hard — I can generate the boilerplate, layouts, and components for you. Your job becomes mostly copy-paste, understand, and customize. We can make it look modern too with proper stylesheets.
If you're working with me, PySide6 is back on the table.fuck it we use what industry needs, i am immigrant who have to think of easy + finding a job + managing side jobs and completing the uni at the same timeMar 24Thinking about balancing work, studies, and practical career needs as an immigrantThinking about balancing work, studies, and practical career needs as an immigrantPySide6 it is. We'll build it together, I handle the heavy lifting. Let's get that professor table done first — share what he asked for exactly.so i showed the ppt to him Last Week (the one i gave you above). what are the remarks we should add to the project.
HUSAM SUGGESTED: as we discussed we have two actors: admin and employee
there are few addition points he told me about admin part: 
1. so admin can select for prompotions -> title selection
2. can select the commendation time threshold
3. and we should add a logic like next promotion start from scratch (no commendation or anything)
also we should have an option to import the csv or excel where we can import empoloyee data (for lets say we have a new company where we are selling the data, the were doing this on excel but now they have this so they can import all the data to the software and start using it. (it should also be cleaned before so we can think of something that we need to proivde a guide for admin and a short traininng to admin how to use the system cos it can break if they just put whatver data so they need tyo clean up and provide only necessary data) 
and the software should have a manually add employee button where an admin ca add employee one by one (so this is for when they already start using our a sopftware for longer period), this should ask the admin to add the appropriate details so a new employee could be added to the organization correctly.
an example of an organization could be a hierarchy 
for example: (the hierechay below goes down in every next line)
CEO
(under ceo) Group Managing Diector, CFO, Chief of staff
(under group managing director) Chief operating officer, CCO, Business assistant, Managing director UK, Managing diretor Hungary
(under under chief op operator) Bsniss, analyst, managing directors, heqad of multiple dpets, sr project manager ops,)
(under lets say head of security department) ops system manager, senior security manager, emergency respons eand business, and many more...
(under senior ops portfolio manager) assistant oriject manageement (intern), then bunch of junior managers and managers to diff dept
(under junior managers) superviosr, trainees, analysts
(under analyst could be) outsourced agents 
-> this is what i was thinking out loud, we can show this to professsor by making  a hierarchy diagram that i gave a thought abnout this as well and we can think of how will we divide the organistion, depts, and inside depts, units and people under unit in the same diagram. 
-> when we add the employee, we can add his name, personal details (which will be seen by admin only for prviding the logic and saalaies and for administrator purposes) and for employee then can see the details like: Name, job title, department, work email, w3ork contact, business address (lets say Budapest), and then an organization also maybe (like who he is reporting to and who is working under him and optionally his linkedin if user adds his by his own. 
and there arew few things an employee can add himself like profile picture, linkedin profile, active inactive status and the rest he have to request admin if something is incorrect (lets say his name has a typo, he is not allowed to change himself)Show moreMar 24Synthesized professor feedback into actionable project requirementsSynthesized professor feedback into actionable project requirementsGot it, all noted. Here's what this adds to the system — clean summary:
New from professor:

Admin can manually configure promotion title selection and commendation time thresholds (not hardcoded)
After a promotion, the clock resets — no carryover commendations
CSV/Excel bulk import for onboarding existing companies (with a data guide/template provided to admin)
Manual one-by-one employee add for ongoing use
Two-sided employee profile: admin sees everything (personal, salary logic), employee sees only work-facing info
Employee can self-edit: profile picture, LinkedIn, active/inactive status — everything else requires admin request
Org hierarchy is deep and flexible (CEO → GMD → COO → Department heads → Units → individuals)

What this means for your DB and architecture — things to lock in now:

Org hierarchy needs a self-referencing table (a node can have a parent node — infinitely deep)
Employee profile needs two layers: private (admin) + public (employee view)
Promotion rules must be configurable in DB, not hardcoded
Need an import module with validation + a clean CSV template you provide
Need a change request system (employee flags an error → admin approves)

Ready to build the technology table for next week whenever you are.Analysis Module Reporting_13 Mar 2026.docdoci made this for my second meeting with him. key changes he suggested few things:
1. employees should have unique ID numbers 
2. as normally it happens, any kind of emplyee even normal employee lets say an engineer can be promoted to managarials or any kind of positions as well
3. base salary for each positon could be defined and it could be lets say if someone have:
* bsc degree - join as L7 
* msc degree - join as L6
* phd degree - join as L5 
and for above three, the postion is same so there will be a base salary * %age of some number (we can define accoridng to the current market) or an admin could define it cos in lets say HUngary its different and in Iraq its different but the rule for the degree is same and admin can also define the base salary (2000 -3000 eur) something like that could be recommended in the placeholder for different postions or maybe in the bracketswe also have to define the rule for levels so in normal case without any commendation or anything,  if employee worked lets say 3 years then he gets promote to L7 to L6 for listing commendations or awards -> HR could add it for more than one people for the same awards cos lets say there was a team of 3 people who worked on a same project which gave a company a huge victory, and they want to give commendations or awards to all of them together:so instead of adding them one by one, there should be an option to add more then one before pressing the save button and applying this.IMP key change: The two "actors" with access are the System Admin (who maintains the app) and the HR/Administrative Staff (who manage the records).
and one secondary actor: System
* Offline/Standalone Requirement: The project description explicitly states this must be a "standalone desktop application" using a "local SQL-based database" with "no networking required." This means the software is strictly offline and sits on a single machine or local network.
* The Two Primary Actors: 1. Administrative Users (The "Admins"): These are the primary users. The GUI is explicitly designed for them to perform all data management, rule-based checks, and sanctions. 2. HR / Personnel Officers (The "Gatekeepers"): Since the system is for a "government-like organization" and lacks an employee login, these are the actors who execute the "administrative actions" (like issuing commendation letters or disciplinary sanctions).
* Employee Access: There is no mention of an employee-facing interface. Employees are the subjects of the data, not the users of the software. To see their records, they must physically approach the Administrative/HR actors to have the information retrieved for them.Show moreMar 24Synthesized comprehensive system requirements and user role architectureSynthesized comprehensive system requirements and user role architectureOkay I read everything. Your document is actually really well structured — you've done serious work already. Here's my full picture now combining everything:

What your doc already covers well:

All 10 use cases written out properly (UC01–UC10)
Functional + non-functional requirements table
Actors: Admin, HR Officer, Department Head, Employee, System
Audit log logic (who, what, when — nepotism prevention explicitly mentioned)
Hierarchy management with dependency checks before deletion


What the professor added in meeting 2 that needs updating in your doc/table:

Unique employee IDs
Any employee can be promoted to managerial (not just within a track)
Salary levels tied to degree: BSc → L7, MSc → L6, PhD → L5, same title but different base salary %
Admin can define base salary ranges per position (with placeholder suggestions)
Bulk commendation — apply to multiple employees at once for team awards
Big actor clarification: No employee login at all — employees are just data subjects, only Admin and HR Staff use the software


That last point is important — your doc still has UC06 (Employee Login) and UC08 (Role-Based Access for employees). Based on what the professor said in meeting 2, those need to be simplified or removed for Part 1. Employees don't log in — admin retrieves info for them physically.
Ready to build the technology table for next week?since this will be my 3rd meeting (and since its biweekly) i will have to show him some progress, what did I do?so suggest me ideas what should we work on to show him progress.very short answer bullet pointsMar 24Synthesized progress indicators and actionable project milestonesSynthesized progress indicators and actionable project milestonesBased on everything so far, here's what's realistic to show:

Finalized tech stack table (what he asked for next week)
Updated use-case diagram reflecting meeting 2 changes (no employee login, bulk commendation, salary levels)
Database schema diagram — tables, relationships, hierarchy structure
GitHub repo set up with proper folder structure, README, and a few commits showing progress
Basic UI prototype — just the main window + navigation skeleton in PySide6, nothing functional yet

That's enough to show you've moved from planning to execution. Don't overdo it.okay we can do that, also i am thinking to show UI mockups on Figma or Draw.io to show the blue print?Mar 24Yes, good idea — shows you thought about UX before coding.

Figma — looks more professional, better for presenting to professor
Draw.io — faster, easier, good enough for academic purposes

For a biweekly meeting I'd say Draw.io — don't waste time making it pixel perfect in Figma when you have a job + 30 credits. Professor cares about logic not aesthetics at this stage.okay, lets begin, whats our agenda today to show him updates next week and what will be the step by step apporach to finish the tasks for today. should we start with Github? or something else?Mar 24Prioritized actionable tasks and sequenced workflow efficientlyPrioritized actionable tasks and sequenced workflow efficientlyHere's the agenda and order:
Today's goal: Show proof of life on GitHub + foundation documents

GitHub repo setup — create it, proper structure, README, .gitignore (15 min)
Tech stack table — finalize it as a clean document for professor (20 min)
DB schema diagram — draw the tables and relationships on Draw.io (45 min)
UI mockups — basic screens on Draw.io (45 min)
Update use-case diagram — reflect meeting 2 changes (30 min)


Start with GitHub — it's the backbone everything else gets pushed to, and it takes 15 minutes. Every step after that gets committed so professor sees real activity.
Shall we start with the repo structure?yes pleaseMar 24Architected project structure for Python development frameworkArchitected project structure for Python development frameworkTell me first — do you already have a GitHub account and an empty repo created, or should I walk you through that too?
Also, do you have Python and PySide6 installed locally already?I have a github account, but not initialized with the repo creation. for now, we can add the ppt and module analysis that we had and them later we can keeping pushing the updates and changes. also how can i invite professor to the repo to see changes, tell that part too. 
I am naming this project MyHR. python is probably installed by PySice 6, no for sure.Mar 24Orchestrated setup instructions for repository initialization and collaborationOrchestrated setup instructions for repository initialization and collaborationStep 1 — Create the repo:

Go to github.com → click "New"
Name it MyHR
Set to Public (so professor can see without an account if needed)
Check "Add a README"
Click Create repository


Step 2 — Invite your professor:

Go to repo → Settings → Collaborators → Add people
Add his GitHub username or university email
Give him Read access — he can see everything but can't change anything


Step 3 — Folder structure to create:
MyHR/
├── README.md
├── docs/
│   ├── myHR_presentation.pptx
│   └── Analysis_Module_13_Mar_2026.doc
├── src/
├── database/
├── assets/
└── .gitignore
Upload your PPT and doc inside the docs/ folder.

Step 4 — Install PySide6:
bashpip install PySide6

Start with Step 1, let me know when the repo is created and I'll give you the exact README content to paste in.proceedMar 24Orchestrated professional README framework for MyHR projectOrchestrated professional README framework for MyHR projectPaste this into your README.md on GitHub (edit it directly on GitHub by clicking the pencil icon):
markdown# MyHR — Employee Management System

A standalone desktop application for managing employee records in government-like organizations.

Built with Python + PySide6 + SQLite.

## Project Structure
MyHR/
├── docs/          # Project documentation, presentations, analysis
├── src/           # Application source code
├── database/      # Database schema and migrations
├── assets/        # Icons, images, UI assets
└── README.md

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| UI | PySide6 |
| Database | SQLite |
| ORM | SQLAlchemy |
| Version Control | GitHub |

## Supervisor
Dr. Husam Al-Maghoosi

## Developer
Muhammad Ibrahim Shoeb

## Status
🟡 In Progress — Project Lab Phase

Once you paste that and commit it, do two things:

Upload your PPT and doc into the docs/ folder
Come back here and we move to the tech stack table for the professor

Done?short one line addition, mention figma/draw.io for modelling and mockupsMar 24Add this line to the Tech Stack table:
markdown| UI Mockups | Figma / Draw.io |
Done, commit it and let me know!done, next.Mar 24Thinking about clarifying the user's next request or taskThinking about clarifying the user's next request or taskNow let's build the tech stack table for the professor.
Should I make this as a clean Word doc or just a neat table you can paste into an email/message to him?okayMar 24Thinking about interpreting an ambiguous acknowledgmentThinking about interpreting an ambiguous acknowledgmentWord doc or email/message — which one?i already told him in presentation about the tech stack and we added that in the github repo as well, no?Mar 24You're right, skip it — professor already saw it in the PPT and it's in the README.
Next is DB schema diagram on Draw.io. Ready?yeah, lets do this oneMar 24Architected comprehensive database schema with relational tablesArchitected comprehensive database schema with relational tablesBefore I draw it, let me confirm the tables we need based on everything discussed. Review this quickly:

org_unit — self-referencing hierarchy (org → dept → sub-dept → unit)
employee — all personal + org details, unique ID, degree, level
title — L5/L6/L7, base salary range, salary multiplier
promotion_rule — years required, commendation threshold per title track
promotion_history — who got promoted, when, by whom, basis
commendation — team awards (one commendation → many employees)
sanction — per employee, type, duration
audit_log — who, what, when for every action
system_user — Admin and HR Officer only, no employee login

That's 9 tables. Anything missing or wrong before I draw it?