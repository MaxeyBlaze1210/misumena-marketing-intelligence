# Misumena Marketing Intelligence (MMI)

MMI (Misumena Marketing Intelligence) is an AI-assisted marketing intelligence platform for independent music.

Its purpose is to help artists collect marketing data from multiple platforms, preserve marketing knowledge across releases, and generate evidence-based recommendations that improve future campaigns.

Rather than treating every release as an isolated project, MMI builds a growing marketing knowledge base.

---

## Vision

Most marketing knowledge disappears after a release ends.

Performance data becomes fragmented across Meta Ads, YouTube Studio, Spotify for Artists, distributors, spreadsheets and personal notes. Marketing decisions are often rely on intuition, while the reasoning behind successful (or unsuccessful) campaigns is rarely documented.

MMI aims to solve this problem.

The goal is **not** to automate creativity or replace human decision-making.

The goal is to preserve evidence, explain outcomes and help every new release benefit from everything learned previously.

---

## Project Status

🚧 Early MVP Development

### Backend

- ✅ FastAPI backend
- ✅ SQLite database
- ✅ SQLAlchemy ORM
- ✅ REST API
- ✅ Release CRUD
- ✅ Recommendation endpoint

### Platform Integrations

- ✅ YouTube Data API
- ✅ YouTube Analytics API
- ✅ Meta Marketing API
- ✅ Spotify Web API
- ⏳ GEMA import

### Current Focus

- Historical Meta imports
- Unified marketing database
- Recommendation engine
- Cross-platform reporting

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

### Planned Integrations

- GEMA
- Distributor reports
- Dropbox API
- AI image analysis
- AI video analysis
- AI audio analysis

---

## Project Structure

```
backend/
    app/
        api/
        database/
        importers/
        models/
        schemas/
        services/
        main.py

frontend/

data/

reports/

docs/
```

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

```
http://127.0.0.1:8000/docs
```

OpenAPI:

```
http://127.0.0.1:8000/openapi.json
```

---

## Database

Current database:

```
backend/mmi.db
```

Current focus:

- Releases
- Marketing data
- Recommendation engine

The database will gradually evolve into a unified marketing database that combines data from multiple platforms around individual music releases.

---

## Development Philosophy

Every release is an experiment.

Every experiment should leave behind evidence.

Every new release should benefit from everything learned previously.

MMI is designed to support marketing decisions—not replace them.

AI should explain recommendations, not make unexplained decisions.

---

## Current Capabilities

MMI currently supports:

- Release management
- Meta campaign retrieval
- Meta campaign insights
- Meta ad retrieval
- Meta ad-level insights
- YouTube metadata
- YouTube Analytics
- Spotify integration
- Rule-based marketing recommendations

---

## Roadmap

### Phase 1 – Unified Marketing Database

- Store Meta campaigns and creatives
- Store YouTube analytics
- Store Spotify analytics
- Organise everything by release

### Phase 2 – Marketing Intelligence

- Creative comparison
- Audience comparison
- Cross-platform reporting
- Experiment tracking
- Explainable recommendations

### Phase 3 – Financial Intelligence

- Distributor reports
- GEMA royalties
- Marketing ROI
- Revenue attribution

### Phase 4 – Creative Intelligence

Future versions of MMI may analyse creative assets directly.

Potential capabilities include:

- Dropbox integration
- Artwork analysis
- Video analysis
- Audio analysis
- Thumbnail comparison
- Creative feature extraction

---

## Long-Term Vision

MMI is designed to become a long-term marketing memory.

Instead of storing analytics in separate dashboards, MMI will connect marketing, streaming and financial data into a single evidence base.

Over time, it should be able to answer questions such as:

- Which creatives consistently outperform?
- Which audiences generate the best long-term ROI?
- Which countries convert best?
- Which optimisation decisions repeatedly improve campaign performance?
- What have we learned from our last ten releases?

The emphasis is not on collecting data for its own sake.

The emphasis is on building knowledge that improves future releases.

---

## Guiding Principle

> **MMI is not another marketing dashboard.**
>
> **It is a marketing memory that grows into a marketing intelligence platform.**

---

## License

Private project.