# LOVABLE_CONTEXT.md

## 1. Executive Summary

**TalentRank AI** is an advanced, AI-powered recruitment intelligence platform built for the **India Runs Hackathon – Data & AI Challenge: Intelligent Candidate Discovery**. 

Traditional Applicant Tracking Systems (ATS) rely on simple keyword matching, leaving recruiters to manually sift through thousands of noisy resumes, often missing high-potential candidates who lack specific buzzwords. TalentRank AI solves this by introducing a **Core Intelligence Layer** that deeply understands candidate profiles semantically, structurally, and behaviorally. 

Our **Product Vision** is to provide an *Explainable AI* (XAI) platform. Recruiters shouldn't just see a score; they need to understand *why* a candidate was recommended, what risks they carry, and how they behave. 

**Primary Users**: Technical Recruiters, Hiring Managers, and HR Leads.
**Success Criteria**: A fast, premium, highly interactive dashboard that allows judges and recruiters to upload a Job Description (JD), instantly surface the top 100 best-fit candidates out of 100,000, understand the AI's reasoning, and export the shortlist—all under 5 minutes.

---

## 2. Product Vision

TalentRank AI is **NOT merely a ranking dashboard**; it is an **Explainable AI Recruitment Intelligence Platform**.

When a recruiter uses this platform, they aren't just querying a database. They are collaborating with an AI assistant that has read, analyzed, and deeply considered every candidate's career trajectory, skills, and behavioral signals. 

**The Recruiter Experience**:
- **Instant Clarity**: The UI highlights top candidates immediately.
- **Deep Trust**: The AI explains every decision using structured Evidence Objects.
- **Actionable Insights**: Recruiters see behavioral multipliers (e.g., "Is this candidate likely to respond?") and risk flags (e.g., "Is this profile inflating their experience?").

Explainability is a first-class feature. The frontend must visually surface the *Why*—translating complex AI scores into clear, human-readable strengths, weaknesses, and risk factors.

---

## 3. System Overview

TalentRank AI is built on a clean, layered architecture designed for speed and modularity.

```text
       [ Technical Recruiter / Judge ]
                    |
                    v
          [ Frontend (Lovable) ]
                    | (REST API / JSON)
                    v
         [ FastAPI Production Backend ]
                    |
      +-------------+-------------+
      |                           |
[ Config Manager ]       [ Analytics / Export ]
      |                           |
      +-------------+-------------+
                    |
        [ Core Intelligence Layer ]
                    |
  +-----------------+-----------------+
  |                 |                 |
[ Feature Store ] [ Hybrid Retrieval] [ Ranking & Explainability Engine ]
  (Parquet/DF)      (FAISS / BM25)      (Evidence Generation)
```

- **Frontend**: The visual layer (to be built) that consumes REST APIs to display data.
- **FastAPI Backend**: Orchestrates the ML layers, handles HTTP requests, and shapes data.
- **Feature Store**: High-performance in-memory pandas DataFrame storing engineered features.
- **Hybrid Retrieval**: Combines Semantic (FAISS) and Lexical (BM25) search using Reciprocal Rank Fusion (RRF).
- **Ranking Engine**: Computes the final authoritative score.
- **Explainability Engine**: Translates mathematical features into human-readable Evidence Objects.

---

## 4. Existing Backend

The entire intelligence and backend infrastructure is **100% complete, tested, and frozen**. 

The following modules are fully implemented:
- **Core Intelligence Layer**: Parses 100,000 candidates and constructs the data pipeline.
- **Feature Engineering**: Extracts 62+ numeric features spanning Semantic, Career, Behavioral, Education, Risk, and Honeypots.
- **Embeddings**: Uses `sentence-transformers/all-MiniLM-L6-v2` for dense semantic representations.
- **FAISS & BM25**: Pre-computed indices for blazing-fast retrieval.
- **Hybrid Retrieval**: Fuses semantic meaning with exact keyword matching.
- **Behavioral Engine**: Modulates scores based on candidate activity, response rates, and availability.
- **Ranking**: Computes scores using dynamically configurable weights.
- **Evidence Generation**: Extracts positive, neutral, and negative signals for XAI.
- **Analytics**: Aggregates distributions and dashboard metrics.
- **FastAPI**: The REST API layer securely exposing all of the above.
- **Validation**: CSV export tailored to Hackathon requirements.

> [!IMPORTANT]
> **Constraint**: The frontend **MUST** consume the backend and **never** duplicate business logic. Do not compute scores, filter honeypots, or generate explanations in the UI.

---

## 5. API Overview

The backend runs on `http://localhost:8000`. All endpoints return a standardized wrapper:
```json
{
  "data": { ... },
  "metadata": { "processing_time_ms": 142.5, "total_results": 100, "version": "1.0.0" },
  "errors": [],
  "success": true
}
```

### 1. `POST /candidates/rank`
- **Purpose**: Submit a Job Description (JD) and get ranked candidates.
- **Input**: `{ "job_description": "...", "top_k": 100, "filters": { "exclude_honeypots": true } }`
- **Output**: Array of `RankedCandidateSchema`.
- **Frontend Usage**: The primary search action on the Dashboard.
- **Expected UX**: Show a sophisticated "AI Analyzing" loading state (e.g., "Embedding JD...", "Retrieving...", "Scoring...").

### 2. `GET /candidates/{candidate_id}/evidence`
- **Purpose**: Fetch explainability data for a specific candidate.
- **Input**: Path parameter `candidate_id`.
- **Output**: `CandidateEvidenceSchema` (Positive/negative signals, summaries, risk flags).
- **Frontend Usage**: The Candidate Detail View.
- **Expected UX**: Slide-out drawer or full-page view highlighting why the candidate matched.

### 3. `POST /candidates/compare`
- **Purpose**: Side-by-side comparison of 2-5 candidates.
- **Input**: `{ "candidate_ids": ["CAND_1", "CAND_2"] }`
- **Output**: Dictionary mapping candidate IDs to their Evidence schemas.
- **Frontend Usage**: Comparison View.

### 4. `GET /analytics/dashboard`
- **Purpose**: High-level system metrics.
- **Output**: Total candidates, honeypots, average experience, etc.
- **Frontend Usage**: Top metric cards on the Landing Dashboard.

### 5. `GET /analytics/distributions`
- **Purpose**: Histogram data for UI charts.
- **Output**: Bins and counts for skills, experience, company size, and education.
- **Frontend Usage**: Radar/Bar charts on the Analytics page.

### 6. `GET /analytics/honeypots`
- **Purpose**: Returns all flagged honeypot candidates.
- **Output**: Array of honeypot profiles and their flagged reasons.
- **Frontend Usage**: The "Wall of Shame" page.

### 7. `GET /config` & `POST /config/weights`
- **Purpose**: Get or set runtime ranking weights (Semantic, Structured, Behavioral, Recency).
- **Frontend Usage**: The "Configuration Sandbox" slider panel.

### 8. `POST /export/csv`
- **Purpose**: Generate the official Hackathon submission CSV.
- **Frontend Usage**: "Export Shortlist" button.
- **Expected UX**: Triggers a file download.

---

## 6. Data Models

### RankedCandidate
```json
{
  "candidate_id": "CAND_0000001",
  "final_score": 0.942,
  "retrieval_score": 0.88,
  "feature_score": 0.91,
  "behavioral_multiplier": 1.0,
  "is_honeypot": false
}
```

### EvidenceObject
```json
{
  "candidate_id": "CAND_0000001",
  "overall_score": 0.942,
  "positive_signals": [
    {
      "signal_name": "years_experience",
      "value": 7.5,
      "impact": "positive",
      "weight": 0.1,
      "description": "Ideal experience range (7.5 years matches 5-9 years requested)"
    }
  ],
  "negative_signals": [],
  "neutral_signals": [],
  "behavioral_summary": {
    "recruiter_response_rate": 0.95,
    "open_to_work": true
  },
  "career_summary": {
    "avg_tenure_months": 24,
    "company_sizes": ["Product/Startup"]
  },
  "risk_flags": [],
  "is_honeypot": false,
  "honeypot_reasons": []
}
```

---

## 7. User Personas

1. **Technical Recruiter**: Wants to paste a JD, quickly get the top 100 candidates, and immediately understand *why* they fit so they can write personalized outreach emails.
2. **Hiring Manager**: Wants to compare the top 3 candidates side-by-side to make an interview decision. Focuses on tech stack and risk flags.
3. **Hackathon Judge**: Wants to see the AI's capabilities, tweak weights in real-time, view analytics, and export the CSV to validate the submission.

---

## 8. User Journey

1. **Landing**: User lands on the Dashboard. They see aggregate metrics (Total Candidates, Market Health) and a prominent "Analyze Job Description" text area.
2. **Analysis**: User pastes a JD and clicks "Rank Candidates". A rich loading state plays.
3. **Shortlist**: User is taken to the **Candidate Rankings** page. A table/list of the top 100 candidates is shown with confidence badges.
4. **Deep Dive**: User clicks a candidate. A **Candidate Detail** drawer slides out, presenting the Explainability Evidence (strengths, risks, behavior).
5. **Compare**: User selects 3 candidates and clicks "Compare". The **Comparison** page aligns their traits side-by-side.
6. **Export**: User clicks "Export CSV" to finalize their shortlist.

---

## 9. Complete Page Inventory

### 1. Landing Dashboard
- **Purpose**: Entry point.
- **Widgets**: Analytics metric cards, large JD input area, recent searches (mocked).

### 2. Candidate Rankings (Shortlist)
- **Purpose**: Display the ranked results.
- **Components**: Data Table/List, Confidence Badges, "Compare" checkboxes, Filter Panel (slider to exclude honeypots).

### 3. Candidate Detail (Drawer/Modal)
- **Purpose**: Explain the AI's decision.
- **Layout**: 
  - Header: ID, Final Score, Behavior Badge.
  - Body: Strengths (Green), Weaknesses (Red), Behavioral Radar Chart, Timeline of experience.

### 4. Comparison
- **Purpose**: Side-by-side matrix.
- **Components**: Multi-column table highlighting differences in skills, tenure, and scores.

### 5. Analytics & Insights
- **Purpose**: System-wide data visualization.
- **Charts**: Experience Distribution (Bar), Skills Density (Heatmap/Histogram).

### 6. Honeypot Wall of Shame
- **Purpose**: Showcase the AI's fraud detection.
- **Layout**: Grid of flagged candidates with red warning badges and reasons for flagging.

### 7. Configuration Sandbox
- **Purpose**: Allow judges to tweak AI weights.
- **Components**: Sliders for Semantic, Structured, and Behavioral weights. Real-time re-ranking.

---

## 10. Component Library

The UI should utilize a comprehensive, reusable component system.

- **Metric Cards**: Glassmorphic cards with glowing accents showing KPIs.
- **Decision Card**: Summarizes a candidate's fit in 3 bullet points.
- **Evidence Panel**: Collapsible panels showing `positive_signals` and `negative_signals` with respective green/red icons.
- **Radar Chart**: Visualizes the balance of Semantic vs Feature vs Behavioral scores.
- **Risk Badge**: A pulsing red/orange pill for honeypots or job-hoppers.
- **Confidence Badge**: A gradient pill (e.g., 94% Match) with color scaling based on score.
- **Loading Skeleton**: Shimmering placeholders that match the structure of the incoming data.
- **Toast**: Non-intrusive notifications for "Weights updated" or "Export complete".

---

## 11. Explainability UX

XAI is the core differentiator. 

Evidence objects must not be dumped as raw JSON. They must be translated into a visual narrative:
- **Strengths**: Rendered as checklist items with green checkmarks.
- **Risks/Weaknesses**: Rendered with yellow/red warning triangles.
- **Behavior**: Rendered as a "Recruiter Match Probability" dial or progress bar.
- **Honeypot Warning**: If `is_honeypot` is true, the UI should immediately blur the candidate's profile and display a large, red "FRAUD DETECTED" banner, requiring the recruiter to explicitly click "Reveal Anyway".

---

## 12. Charts & Visualizations

- **Radar Chart**: Inside the Candidate Detail to show candidate balance.
- **Timeline**: Inside Candidate Detail to show career progression visually.
- **Bar/Histogram**: On the Analytics page for `get_distributions` data.
- **Donut Chart**: To show Open to Work vs Passive percentages on the Dashboard.

---

## 13. Design Philosophy

**Vibe**: Premium SaaS, Next-Generation, Trustworthy, Fast, Minimal.
**Inspiration**: Linear, Vercel, Stripe, Cursor.

- **Colors**: Deep dark mode (slate/indigo backgrounds) with vibrant, neon-esque accents (cyan, purple, emerald) for scores and buttons. Avoid pure black.
- **Typography**: `Inter`, `Geist`, or `Outfit`. Highly legible, geometric sans-serif. Use varied font weights to create strict visual hierarchy.
- **Spacing**: Generous padding. Elements should feel breathable.
- **Borders & Elevation**: Subtle 1px borders with low opacity (`rgba(255,255,255,0.1)`). Use soft, diffuse drop shadows for elevation, avoiding harsh lines.
- **Motion**: Micro-animations on hover. Smooth, snappy transitions (200ms ease-out).

---

## 14. Design System

- **Primary Accent**: `#6366F1` (Indigo) or `#06B6D4` (Cyan).
- **Success/Strengths**: `#10B981` (Emerald).
- **Warning/Honeypot**: `#F43F5E` (Rose).
- **Background**: `#0F172A` (Slate 900).
- **Surface**: `#1E293B` (Slate 800).
- **Typography**: White (`#F8FAFC`) for primary text, Gray (`#94A3B8`) for secondary text.
- **Responsiveness**: Mobile-friendly, but optimized for Desktop (1440px width) as recruiters work on large monitors.
- **Accessibility**: Ensure high contrast for text. Use ARIA labels for screen readers on charts.

---

## 15. Animations

- **Loading Pipeline**: When ranking, show a sequence of steps: "Vectorizing JD..." -> "Querying FAISS..." -> "Applying Behavioral Weights..." -> "Done."
- **Page Transitions**: Subtle fade-in and slide-up (Y-axis translation of 10px).
- **Card Hover**: Cards should slightly elevate (`translate-y-[-2px]`) and increase border opacity on hover.
- **Counters**: Numeric scores should rapidly count up from 0 to their final value on load.

---

## 16. Frontend Architecture

**Stack**: React, Vite, TailwindCSS, Framer Motion (for animations), Lucide React (for icons), Recharts (for charts).
- **State Management**: React Context or Zustand for global state (e.g., currently ranked candidates list).
- **Data Fetching**: React Query (TanStack Query) for caching API responses, handling loading states, and automatic retries.
- **Routing**: React Router for clean page navigation.
- **Folder Structure**:
  - `/src/components` (Reusable UI)
  - `/src/pages` (Routable views)
  - `/src/hooks` (Custom API hooks like `useRanking`)
  - `/src/services` (Axios API clients)
  - `/src/types` (TypeScript interfaces matching backend schemas)

---

## 17. Demo Mode (For Judges)

The UI should be designed to give a flawless 2-minute demo to hackathon judges.

1. **Landing**: Show the beautiful dark-mode dashboard. Mention the 100k candidate scale.
2. **Paste JD**: Paste a realistic JD. Hit Rank.
3. **Analyze**: Let the fast loading animation impress them.
4. **Ranking**: Show the list. Immediately point out a candidate with a 95% score.
5. **Candidate Detail**: Open the drawer. Show the *Explainability* (why this person fits, proving it's not a black box).
6. **Honeypot Wall**: Navigate to the Wall of Shame to show the AI catching a fraudster.
7. **Sandbox**: Move the "Behavioral Weight" slider, hit rank, and watch the list dynamically re-order in real-time.
8. **Export**: Export the CSV to prove hackathon compliance.

---

## 18. Engineering Constraints

- **Single Source of Truth**: The backend is the brain. The frontend is the display.
- **No Heavy Compute**: Do not perform complex sorting, filtering, or scoring in the browser. Always rely on the API.
- **Error Handling**: The frontend must gracefully handle 4xx/5xx errors, displaying user-friendly fallback UI (Empty States/Error States) without crashing.
- **Mocking**: If the backend is unreachable during early dev, use the JSON schemas provided in Section 6 to mock the API responses.

---

## 19. Integration Checklist

- [ ] Initialize Vite/React project with TailwindCSS.
- [ ] Set up Axios/TanStack Query with `baseURL: http://localhost:8000`.
- [ ] Build layout shell (Sidebar, Header, Content Area).
- [ ] Implement Dashboard Summary (`GET /analytics/dashboard`).
- [ ] Implement JD Input and `POST /candidates/rank`.
- [ ] Implement Candidate List View.
- [ ] Implement Candidate Detail Drawer (`GET /candidates/{id}/evidence`).
- [ ] Implement Comparison View (`POST /candidates/compare`).
- [ ] Implement Sandbox Config Sliders (`POST /config/weights`).
- [ ] Ensure all loading states (skeletons) are wired.
- [ ] Polish animations and typography.

---

## 20. Final Vision

When a recruiter or judge sits down to use TalentRank AI, they should not feel like they are looking at a 5-day hackathon project. They should feel like they are test-driving a $100k/year enterprise SaaS product. 

The interface must be silent, calm, and immensely powerful. The AI does the heavy lifting, and the UI gently guides the human toward the perfect hire, explaining its reasoning every step of the way. Build it with craftsmanship, attention to detail, and a relentless focus on the user experience.
