# MyHR - Employee Management System

A standalone desktop application for managing employee records in government-like organizations.

Built with Python + PySide6 + SQLite.

## Project Structure
```
MyHR/
├── docs/          # Project documentation, presentations, analysis
├── src/           # Application source code
├── database/      # Database schema and migrations
├── assets/        # Icons, images, UI assets
└── README.md
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| UI | PySide6 |
| Database | SQLite |
| ORM | SQLAlchemy |
| UI Mockups and Modeling | Figma / Draw.io |
| Version Control | GitHub |

## Running the MockUI

The MockUI is a React-based interactive prototype of the application interface built with Vite, TypeScript, and Tailwind CSS.

### Prerequisites
- Node.js 16+ and npm/pnpm installed

### Setup & Run

1. Navigate to the MockUI directory:
```bash
cd MockUI
```

2. Install dependencies:
```bash
npm install
# or if using pnpm:
pnpm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser and navigate to `http://localhost:5173` (or the port shown in terminal)

### Build for Production
```bash
npm run build
npm run preview
```

### Project Structure
- `src/app/` - Main React components and page layouts
- `src/app/pages/` - Application pages (Dashboard, Employee Management, etc.)
- `src/app/components/` - Reusable UI components
- `src/styles/` - CSS and Tailwind styling
- `vite.config.ts` - Vite configuration

## Status
In Progress - Project Lab Phase

## Progress Tracker

You can track live development progress here:

**[View Progress Tracker →](https://raw.githack.com/ibrahimify/MyHR/master/docs/myhr-progress.html)**

The tracker shows the 5-day sprint breakdown, completed tasks, and overall progress updated in real time.