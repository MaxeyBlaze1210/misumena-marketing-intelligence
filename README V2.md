# Misumena Marketing Intelligence (MMI)

MMI (Misumena Marketing Intelligence) is an AI-assisted marketing intelligence and campaign management platform for independent music.

It connects release planning, campaign construction, marketing execution, analytics and long-term learning in one release-centered system.

Rather than treating every release as an isolated marketing project, MMI preserves the relationship between:

- what was planned
- what was executed
- what happened
- what was learned

The objective is to build a growing marketing knowledge base in which every release can benefit from evidence collected during previous releases.

---

## Vision

Most marketing knowledge disappears after a release ends.

Performance data becomes fragmented across Meta Ads, YouTube Studio, Spotify for Artists, distributors, spreadsheets and personal notes. Marketing decisions are often based on intuition, while the reasoning behind successful or unsuccessful campaigns is rarely preserved.

MMI aims to solve this problem.

The goal is **not** to automate creativity or replace human decision-making.

The goal is to preserve evidence, structure experiments, explain outcomes and help every new release benefit from everything learned previously.

The core learning cycle is:

```text
PLAN
What are we trying to achieve or test?
        ↓
BUILD
What campaign structure should represent that plan?
        ↓
EXECUTE
What actually ran?
        ↓
OBSERVE
What happened?
        ↓
LEARN
What does the evidence suggest?
        ↓
NEXT RELEASE
What should we do differently?
```

---

## Project Status

🚧 Active MVP Development

### Core Platform

- ✅ FastAPI backend
- ✅ SQLite database
- ✅ SQLAlchemy ORM
- ✅ Release workspace
- ✅ Release management
- ✅ Asset management
- ✅ Release-centered campaign planning
- ✅ Explainable recommendation foundation

### Meta Campaign Management

- ✅ Meta Marketing API integration
- ✅ Campaign planning
- ✅ Audience and targeting variants
- ✅ Interest discovery and selection
- ✅ Creative selection
- ✅ Per-creative advertising copy
- ✅ Campaign-cell experiment model
- ✅ Campaign creation
- ✅ Ad-set creation
- ✅ Video upload to Meta
- ✅ Meta-generated video thumbnail retrieval
- ✅ Ad Creative creation
- ✅ Ad creation
- ✅ Safe PAUSED-state creation
- ✅ Local ↔ Meta object mappings
- ✅ Readback and safety validation
- ✅ Reconciliation of previously created Meta objects
- 🚧 Campaign execution and optimization

### Platform Integrations

- ✅ Meta Marketing API
- ✅ YouTube Data API
- ✅ YouTube Analytics API
- ✅ Spotify Web API
- ✅ Dropbox API
- ⏳ Distributor reporting
- ⏳ GEMA import

---

## Current Focus

The current development focus is the transition from **campaign construction** to **campaign execution and experimentation**.

Key areas include:

- safe Meta campaign execution
- campaign monitoring
- budget management
- experiment measurement
- creative comparison
- audience comparison
- optimization decisions
- preserving campaign decisions and outcomes
- cross-release learning

Campaign construction is now sufficiently developed to create real Meta campaign objects from an MMI campaign plan while keeping newly created objects paused until execution is explicitly authorized.

---

## Core Concept

MMI is organized around music releases.

A release connects:

```text
Release
    │
    ├── Assets
    │
    ├── Promotion
    │     ├── Campaign plans
    │     ├── Audiences
    │     ├── Creatives
    │     ├── Experiments
    │     └── Execution
    │
    ├── Analytics
    │     ├── Meta
    │     ├── YouTube
    │     ├── Spotify
    │     └── future platforms
    │
    ├── Revenue
    │
    └── Intelligence
          ├── Observations
          ├── Comparisons
          ├── Recommendations
          └── Cross-release knowledge
```

The release is therefore more than a database entity.

It is the unit around which planning, execution, measurement and learning are connected.

---

## Campaign Experiments

MMI treats marketing campaigns as structured experiments.

A campaign plan can define:

- campaign objective
- optimization goal
- conversion event
- destination
- call to action
- countries
- age range
- total budget
- schedule
- targeting variants
- creative assets
- primary advertising text

Campaign variants represent audience or targeting hypotheses.

Campaign cells connect a targeting variant with a creative asset.

Conceptually:

```text
Campaign Plan
      │
      ├── Variant A
      ├── Variant B
      └── Variant C
              ×
        Creative Assets
              ↓
        Campaign Cells
```

These cells provide the experimental structure required to compare creative and audience performance.

---

## Meta Campaign Construction

MMI can construct a real Meta advertising campaign from its internal campaign specification.

The current construction pipeline is:

```text
MMI Campaign Plan
        ↓
Managed Meta Campaign
        ↓
Campaign Variants
        ↓
Campaign Cells
        ↓
Meta Ad Sets
        ↓
Creative Asset
        ↓
Dropbox Download
        ↓
Meta Video Upload
        ↓
Video Thumbnail
        ↓
Meta Ad Creative
        ↓
Meta Ad
```

External Meta IDs are stored locally so MMI can reconcile existing objects instead of blindly creating duplicates.

New campaign objects are created in a safe paused state.

Campaign construction does **not** automatically start advertising spend.

---

## Safety Model for External Writes

MMI treats writes to external advertising platforms as controlled operations.

Current principles include:

- new Meta campaigns, ad sets and ads are created paused
- external object IDs are persisted locally
- newly created objects are read back from Meta
- important state and ownership assumptions are validated
- existing mappings are reconciled on repeated operations
- external writes should be idempotent wherever practical
- activation is separate from construction
- campaign execution should remain explicit and observable

This separation allows MMI to construct campaign infrastructure without automatically spending money.

---

## Technology Stack

### Backend

- Python 3.14
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Uvicorn

### External APIs

- Meta Marketing API
- YouTube Data API
- YouTube Analytics API
- Spotify Web API
- Dropbox API

### Planned Data Sources

- distributor reports
- GEMA
- additional streaming platforms
- additional social platforms

### Potential Future Analysis

- AI image analysis
- AI video analysis
- AI audio analysis
- creative feature extraction

---

## Project Structure

```text
backend/
    app/
        api/
        core/
        database/
        importers/
        intelligence/
        models/
        schemas/
        services/
        templates/
        main.py

frontend/

data/

reports/

docs/
```

The exact structure will continue to evolve as application services, intelligence components and platform integrations become more mature.

---

## Running the Backend

From the project root:

```bash
cd backend
```

Start the development server:

```bash
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI:

```text
http://127.0.0.1:8000/openapi.json
```

---

## Database

Current development database:

```text
backend/mmi.db
```

Open it with:

```bash
sqlite3 mmi.db
```

The database acts as MMI's historical source of truth.

It connects internal planning objects with external platform objects and their subsequent measurements.

Important domains increasingly include:

```text
Release
    ├── Assets
    ├── Campaign Plans
    ├── Campaign Variants
    ├── Campaign Cells
    ├── External Platform Objects
    ├── Metrics
    ├── Experiments
    ├── Decisions
    └── Knowledge
```

External platforms remain authoritative for their own current platform state, but MMI preserves the historical relationship between plans, actions and outcomes.

---

## Intelligence Philosophy

MMI follows a **data first, AI second** approach.

AI should not invent marketing knowledge from incomplete evidence.

The intended progression is:

```text
structured data
      ↓
experiments
      ↓
observations
      ↓
comparisons
      ↓
evidence
      ↓
recommendations
      ↓
human decision
```

Recommendations should be explainable.

Where confidence is low, MMI should say so.

Where evidence is insufficient, MMI should prefer observation over premature optimization.

---

## Current Capabilities

MMI currently supports or has working foundations for:

- release management
- release asset management
- Dropbox creative ingestion
- Meta campaign retrieval
- Meta campaign insights
- Meta ad retrieval
- Meta ad-level insights
- Meta campaign planning
- audience experiment construction
- creative experiment construction
- Meta campaign creation
- Meta ad-set creation
- Meta video upload
- Meta Ad Creative creation
- Meta Ad creation
- safe paused campaign construction
- Meta object reconciliation
- YouTube metadata
- YouTube Analytics
- Spotify integration
- rule-based marketing recommendations

---

## Initial MVP Recommendation Rules

The first recommendation engine uses simple, transparent heuristics.

A creative is initially considered sufficiently tested when:

```text
impressions >= 2000
```

Initial rules include:

1. Below 2,000 impressions:
   - action: `observe`
   - reason: insufficient evidence

2. Among sufficiently tested creatives:
   - the lowest cost per result becomes a scale candidate

3. A sufficiently tested creative with cost per result at least 50% above the winner:
   - action: `pause_candidate`

4. A sufficiently tested creative within 50% of the winner:
   - action: `keep`

5. A sufficiently tested creative with no results:
   - action: `pause_candidate`

These rules are an explainable MVP baseline, not a permanent optimization policy.

Future intelligence should incorporate richer experimental evidence, multiple performance signals, downstream listener behavior and cross-release learning.

---

## Roadmap

### Phase 1 — Foundation & Unified Data

Status: substantially implemented

- release-centered data model
- platform integrations
- historical marketing data
- asset management
- external object mappings
- normalized metrics

### Phase 2 — Campaign Planning & Construction

Status: MVP substantially implemented

- campaign plans
- targeting variants
- creative selection
- experiment cells
- budget and schedule configuration
- Meta campaign creation
- Meta ad-set creation
- creative upload
- Ad Creative creation
- Ad creation
- paused-state safety
- reconciliation

### Phase 3 — Campaign Execution & Experimentation

Status: current focus

- pre-launch validation
- controlled campaign activation
- schedule-aware execution
- budget allocation
- performance monitoring
- experiment evaluation
- pause / keep / scale decisions
- budget reallocation
- decision history

### Phase 4 — Marketing Intelligence

- creative comparison
- audience comparison
- country comparison
- trend detection
- anomaly detection
- confidence scoring
- cross-release recommendations
- accumulated marketing knowledge

### Phase 5 — Cross-Platform & Financial Intelligence

- Spotify outcomes
- Apple Music outcomes
- YouTube outcomes
- distributor reports
- GEMA royalties
- marketing ROI
- listener value
- revenue attribution

The goal is to evaluate listener acquisition across platforms rather than treating one streaming service as the sole definition of campaign success.

### Phase 6 — Creative Intelligence

Potential future capabilities include:

- artwork analysis
- video analysis
- audio analysis
- thumbnail comparison
- creative feature extraction
- relationships between creative characteristics and campaign outcomes

---

## Long-Term Vision

MMI is designed to become a long-term marketing memory.

Instead of storing analytics in separate dashboards, MMI connects:

```text
planning
   +
execution
   +
marketing performance
   +
audience behavior
   +
streaming
   +
revenue
   +
decisions
   +
lessons
```

into a single evidence base.

Over time, MMI should be able to answer questions such as:

- Which creatives consistently outperform?
- Which audiences generate the best listeners?
- Which countries convert most efficiently?
- Which campaign structures produce reliable results?
- Which optimization decisions repeatedly improve performance?
- Which marketing channels generate valuable downstream behavior?
- What did we believe before a campaign?
- What actually happened?
- Why did we change the campaign?
- Was that change successful?
- What have we learned from our last ten releases?
- What should we test differently on the next release?

The emphasis is not on collecting data for its own sake.

The emphasis is on turning repeated marketing activity into accumulated knowledge.

---

## Development Philosophy

Every release is an experiment.

Every experiment should leave behind evidence.

Every important decision should have a reason.

Every external action should be observable.

Every new release should benefit from what was learned previously.

Creativity remains human-led.

MMI is designed to support marketing decisions—not replace them.

AI should explain recommendations, not make unexplained decisions.

---

## Guiding Principle

> **MMI is not another marketing dashboard.**
>
> **It is a marketing memory that grows into a marketing intelligence and execution platform.**
>
> It connects what was planned, what was executed, what happened and what was learned—so that each release can improve the next.

---

## License

Private project.