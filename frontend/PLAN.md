# Frontend Web Application Plan for AI Job Application Automation System

## Overview
Create a modern, user-friendly web frontend that replaces the command-line interface with a click-based workflow for the entire job application automation pipeline.

## Technology Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + shadcn/ui components
- **State Management**: Zustand (lightweight) + React Query (server state)
- **Backend Communication**: REST API (FastAPI on backend) + WebSocket for real-time updates
- **Charts/Visualization**: Recharts for analytics dashboard
- **File Upload**: react-dropzone for resume uploads
- **Forms**: React Hook Form + Zod validation

## Project Structure
```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── ui/                 # shadcn/ui base components
│   │   ├── layout/             # Layout components (Sidebar, Header, Footer)
│   │   ├── dashboard/          # Dashboard-specific components
│   │   ├── profile/            # Profile management components
│   │   ├── job-search/         # Job discovery components
│   │   ├── job-matching/       # Matching analysis components
│   │   ├── resume/             # Resume customization components
│   │   ├── applications/       # Application tracking components
│   │   └── settings/           # Settings components
│   ├── pages/
│   │   ├── Dashboard.tsx       # Main overview page
│   │   ├── Profile.tsx         # Profile building page
│   │   ├── JobSearch.tsx       # Job discovery page
│   │   ├── JobMatching.tsx     # Matching & scoring page
│   │   ├── ResumeBuilder.tsx   # Resume customization page
│   │   ├── Applications.tsx    # Application tracking page
│   │   ├── Analytics.tsx       # Analytics & reports page
│   │   └── Settings.tsx        # Configuration page
│   ├── hooks/                  # Custom React hooks
│   ├── services/               # API service layer
│   ├── store/                  # Zustand stores
│   ├── types/                  # TypeScript types (matching backend Pydantic models)
│   ├── utils/                  # Utility functions
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
└── .env
```

## Page Layout & User Flow

### 1. **Dashboard (Landing Page)**
- **Sidebar Navigation**: Collapsible sidebar with icons for each phase
- **Header**: User profile, notifications, settings
- **Main Content**:
  - **Stats Cards**: Total Jobs Found, Matched, Resumes Generated, Applications Submitted
  - **Pipeline Progress**: Visual funnel showing DISCOVERED → DEDUPLICATED → MATCHED → QUALIFIED → RESUME_CREATED → READY_TO_APPLY → APPLIED
  - **Recent Activity**: Latest jobs found, matches, resumes created
  - **Quick Actions**: "Start New Search", "Upload Resume", "View Applications"
- **Real-time Updates**: WebSocket connection for live pipeline status

### 2. **Profile Builder (Phase 1)**
- **Step 1: Resume Upload**
  - Drag-and-drop zone for PDF/DOCX resume
  - Progress indicator for parsing
  - Preview extracted information
- **Step 2: Profile Review & Edit**
  - Editable form sections: Personal Info, Skills, Experience, Education, Certifications, Projects
  - AI-suggested improvements (button to trigger)
  - Save as "Master Profile"
- **Step 3: Additional Experience**
  - Add projects, publications, awards not in resume
  - Tag with keywords for matching
- **Output**: Structured CandidateProfile JSON (matches backend schema)

### 3. **Job Discovery (Phase 2)**
- **Search Configuration Panel**:
  - Keywords (multi-select with suggestions from profile)
  - Locations (multi-select, remote option)
  - Job Types (Full-time, Contract, Internship)
  - Experience Levels
  - Date Posted (Last 24h, Week, Month)
  - Sources: Indeed, LinkedIn, Glassdoor, JobBank, Company Careers (checkboxes)
  - Filters: Salary range, Visa sponsorship, Company size
- **Search Execution**:
  - "Start Search" button with progress bar
  - Real-time log panel showing source-by-source progress
  - Cancel button
- **Results Table**:
  - Sortable, filterable, paginated
  - Columns: Title, Company, Location, Source, Match Score (preview), Date, Actions
  - Row actions: View Details, Add to Favorites, Mark as Applied Externally
  - Bulk actions: Export to CSV, Analyze Selected
- **Deduplication View**: Side-by-side comparison of duplicates

### 4. **Job Matching & Scoring (Phase 3)**
- **Queue Panel**: Jobs pending analysis (from discovery)
- **Batch Analysis**:
  - Select jobs (individual or "Select All Qualified")
  - "Analyze Selected" button with progress
  - Configuration: Weight sliders for Skills, Experience, Education, Location, Keywords
- **Results View**:
  - Match Score distribution chart (histogram)
  - Table with: Job, Overall Score, Skill Match %, Experience Match %, Education Match, Location Match, Keyword Match, Verdict (QUALIFIED/UNQUALIFIED)
  - Detail modal: Side-by-side requirement vs candidate comparison
  - Filter by verdict, score range
- **Threshold Settings**: Auto-qualify threshold slider

### 5. **Resume Customization & Validation (Phase 4)**
- **Job Selection**: Pick from QUALIFIED jobs
- **Customization Options**:
  - Format: Keep original DOCX / Modern template / ATS-optimized
  - Sections to emphasize: Skills, Experience, Projects
  - Keywords to inject (from job description)
  - Length preference: 1 page / 2 pages / Auto
- **Generation**:
  - "Generate Resume" button with progress
  - Preview: Side-by-side original vs customized
  - Download DOCX / PDF
- **Validation Results**:
  - Truthfulness Score (0-100%)
  - Issues found: Exaggerated claims, Missing keywords, Formatting issues
  - ATS Compatibility Score
  - "Regenerate with fixes" option

### 6. **Application Tracking (Phase 5-7)**
- **Pipeline Board** (Kanban-style):
  - Columns: Ready to Apply → Applying → Submitted → Interview → Offer → Rejected
  - Drag-and-drop between stages
  - Each card: Company, Role, Match Score, Resume Version, Date
- **Application Details Modal**:
  - Job description
  - Customized resume preview
  - Cover letter (if generated)
  - Submission status & timestamps
  - Notes field
  - Follow-up reminders
- **Batch Actions**: "Apply to Selected" (Phase 7 - disabled until implemented)

### 7. **Analytics & Reports (Phase 8)**
- **Overview Metrics**: Funnel conversion rates, Time-to-apply, Source effectiveness
- **Charts**:
  - Applications over time (line)
  - Match score distribution (histogram)
  - Source breakdown (pie)
  - Skill gap analysis (radar)
  - Response rate by company size/type
- **Export**: PDF report, Excel dashboard
- **Scheduled Reports**: Configure email digest

### 8. **Settings**
- **API Configuration**: LLM provider, API keys (encrypted)
- **Job Sources**: Enable/disable, rate limits, credentials
- **Matching Weights**: Default weight configuration
- **Resume Templates**: Upload custom DOCX templates
- **Notifications**: Email, browser, webhook
- **Data Management**: Backup, export, clear database

## API Integration Design

### Backend API Endpoints Needed
```
GET    /api/profile              # Get current profile
POST   /api/profile              # Create/update profile
POST   /api/profile/upload       # Upload & parse resume
GET    /api/jobs                 # List jobs (paginated, filtered)
POST   /api/jobs/search          # Trigger job search
GET    /api/jobs/:id             # Job details
POST   /api/jobs/:id/analyze     # Analyze single job
POST   /api/jobs/batch-analyze   # Batch analyze
GET    /api/matches              # List matches
GET    /api/resumes              # List generated resumes
POST   /api/resumes/generate     # Generate customized resume
GET    /api/resumes/:id/validate # Validate resume
GET    /api/applications         # List applications
POST   /api/applications         # Create application record
PATCH  /api/applications/:id     # Update application status
GET    /api/analytics/overview   # Dashboard metrics
GET    /api/analytics/funnel     # Pipeline funnel data
GET    /api/settings             # Get settings
PATCH  /api/settings             # Update settings
WS     /ws/pipeline              # Real-time pipeline updates
```

## State Management

### Global Stores (Zustand)
- `useProfileStore`: Current candidate profile, loading states
- `useJobStore`: Jobs list, filters, pagination, selected jobs
- `useMatchStore`: Matches, analysis queue, weight settings
- `useResumeStore`: Generated resumes, validation results
- `useApplicationStore`: Applications, kanban board state
- `useUISettingsStore`: Sidebar collapse, theme, notifications

### Server State (React Query)
- All GET endpoints cached with appropriate stale times
- Mutations for POST/PATCH with invalidation

## Component Design System

### Color Palette (Tailwind + Custom)
```css
:root {
  --primary: #3b82f6;      /* Blue-500 */
  --primary-hover: #2563eb; /* Blue-600 */
  --success: #22c55e;       /* Green-500 */
  --warning: #f59e0b;       /* Amber-500 */
  --danger: #ef4444;        /* Red-500 */
  --background: #f8fafc;    /* Slate-50 */
  --surface: #ffffff;       /* White */
  --text-primary: #1e293b;  /* Slate-800 */
  --text-secondary: #64748b; /* Slate-500 */
}
```

### Dark Mode Support
- Full dark mode via `class` strategy in Tailwind
- All components support both themes

## Responsive Breakpoints
- Mobile: < 640px (stacked layout, bottom nav)
- Tablet: 640px - 1024px (collapsible sidebar)
- Desktop: > 1024px (full sidebar)
- Large: > 1280px (multi-column layouts)

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up Vite + React + TypeScript + Tailwind
- [ ] Install and configure shadcn/ui
- [ ] Create layout components (Sidebar, Header, PageWrapper)
- [ ] Set up routing (React Router v6)
- [ ] Configure API service layer with Axios
- [ ] Set up React Query provider
- [ ] Create TypeScript types from backend schemas

### Phase 2: Dashboard & Profile (Week 2)
- [ ] Dashboard page with stats cards and pipeline funnel
- [ ] Profile page with resume upload (drag-drop)
- [ ] Resume parsing progress & preview
- [ ] Profile edit form with all sections
- [ ] Profile save/load API integration

### Phase 3: Job Discovery (Week 3)
- [ ] Job Search configuration panel
- [ ] Search execution with real-time logs
- [ ] Results table with sorting, filtering, pagination
- [ ] Job detail modal
- [ ] Deduplication view
- [ ] Export to CSV

### Phase 4: Job Matching (Week 4)
- [ ] Analysis queue panel
- [ ] Batch analysis with progress
- [ ] Weight configuration sliders
- [ ] Results table with score breakdown
- [ ] Match detail modal (side-by-side comparison)
- [ ] Histogram chart for score distribution

### Phase 5: Resume Builder (Week 5)
- [ ] Job selection for customization
- [ ] Customization options form
- [ ] Resume generation with progress
- [ ] Preview (original vs customized)
- [ ] Validation results display
- [ ] Download DOCX/PDF

### Phase 6: Application Tracking (Week 6)
- [ ] Kanban board with drag-and-drop
- [ ] Application detail modal
- [ ] Status update actions
- [ ] Notes & reminders
- [ ] Batch operations UI (disabled for Phase 7)

### Phase 7: Analytics & Settings (Week 7)
- [ ] Analytics dashboard with charts
- [ ] Funnel visualization
- [ ] Source effectiveness charts
- [ ] Skill gap radar chart
- [ ] Settings pages (API, Sources, Weights, Templates, Notifications)
- [ ] Dark mode toggle

### Phase 8: Polish & Real-time (Week 8)
- [ ] WebSocket integration for live updates
- [ ] Toast notifications
- [ ] Keyboard shortcuts
- [ ] Loading skeletons
- [ ] Error boundaries
- [ ] Accessibility audit (WCAG AA)
- [ ] Performance optimization
- [ ] E2E tests with Playwright

## Backend Changes Required

### New FastAPI Endpoints
Create `backend/api/` folder with:
- `main.py` - FastAPI app with CORS, WebSocket
- `routes/profile.py`
- `routes/jobs.py`
- `routes/matching.py`
- `routes/resumes.py`
- `routes/applications.py`
- `routes/analytics.py`
- `routes/settings.py`
- `websocket/pipeline.py` - Real-time updates

### Database
- Ensure all models have proper indexes for pagination/filtering
- Add `created_at`, `updated_at` timestamps
- Consider adding full-text search for jobs

## File to Create First
1. `package.json` - Dependencies
2. `tsconfig.json` - TypeScript config
3. `vite.config.ts` - Vite config with proxy to backend
4. `tailwind.config.ts` - Tailwind with custom theme
5. `src/main.tsx` - Entry point
6. `src/App.tsx` - Router + providers
7. `src/index.css` - Global styles + Tailwind imports
8. `src/types/index.ts` - All TypeScript interfaces

## Development Workflow
```bash
# Terminal 1: Backend
cd backend && python -m uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Access at http://localhost:5173 (proxies API to :8000)
```

## Deployment Considerations
- Build frontend: `npm run build` → outputs to `dist/`
- Serve via FastAPI StaticFiles or deploy separately to Vercel/Netlify
- Environment variables for API URLs
- Docker compose for local full-stack dev

---

**Next Step**: Begin implementation with Phase 1 - Project setup and foundation.