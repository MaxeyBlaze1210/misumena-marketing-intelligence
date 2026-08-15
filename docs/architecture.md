# MMI Architecture

## Purpose

Misumena Marketing Intelligence collects release-related data from external platforms, stores it in a unified database, and generates explainable recommendations.

The system is organized around music releases.

---

## Data Flow

```text
External Platform
        ↓
Service
        ↓
Importer
        ↓
Database Models
        ↓
Intelligence Layer
        ↓
FastAPI Endpoint
```

Example:

```text
Meta Marketing API
        ↓
meta_service.py
        ↓
meta_importer.py
        ↓
meta_campaigns
meta_ads
meta_ad_metrics
        ↓
recommendation_engine.py
        ↓
recommendations API
```

---

## Folder Responsibilities

### `app/api`

FastAPI routes.

Responsibilities:

- receive HTTP requests
- validate parameters
- call application functions
- return responses

API files should not contain external API logic, database import logic, or recommendation rules.

Current examples:

- `meta.py`
- `youtube.py`
- `spotify.py`
- `recommendations.py`

---

### `app/services`

External platform connections.

Responsibilities:

- authenticate with platforms
- call external APIs
- handle platform-specific errors
- return raw or lightly normalized data

Current examples:

- `meta_service.py`
- `youtube_service.py`
- `youtube_analytics_service.py`
- `spotify_service.py`

Services should not write directly to the database.

---

### `app/importers`

Data ingestion.

Responsibilities:

- call platform services
- transform external data
- create or update database records
- avoid duplicates
- preserve historical data

Current examples:

- `meta_importer.py`

Planned examples:

- `youtube_importer.py`
- `spotify_importer.py`
- `instagram_importer.py`
- `bandcamp_importer.py`

---

### `app/models`

SQLAlchemy database models.

Current models include:

- `Release`
- `Track`
- `Artist`
- `ReleaseArtist`
- `YouTubeVideo`
- `YouTubeMetric`
- `MetaCampaign`
- `MetaAd`
- `MetaAdMetric`

Models define how data is stored. They should not contain external API calls or recommendation logic.

---

### `app/intelligence`

Decision and analysis logic.

Responsibilities:

- read normalized data
- compare performance
- apply transparent rules
- generate explainable recommendations

Current files:

- `recommendation_engine.py`

Future possibilities:

- trend detection
- confidence scoring
- anomaly detection
- cross-platform comparisons

The intelligence layer should not call Meta, Spotify, YouTube, or other external platforms directly.

---

### `app/database`

Database configuration and initialization.

Current files:

- `database.py`
- `init_db.py`

---

### `app/core`

Application configuration.

Current files:

- `config.py`

Secrets and credentials are loaded from `.env`.

---

## Current Meta Data Flow

```text
Meta Marketing API
        ↓
get_campaigns()
get_ads()
get_ad_insights()
        ↓
meta_importer.py
        ↓
meta_campaigns
meta_ads
meta_ad_metrics
        ↓
recommendation_engine.py
```

The importer stores Meta data in SQLite. The recommendation engine should read from SQLite rather than querying Meta directly.

---

## Initial Recommendation Rules

A creative is considered sufficiently tested when:

```text
impressions >= 2000
```

Rules:

1. Below 2,000 impressions:
   - action: `observe`
   - reason: insufficient evidence

2. Among sufficiently tested creatives:
   - the lowest cost per result becomes the scale candidate

3. A sufficiently tested creative with cost per result at least 50% above the winner:
   - action: `pause_candidate`

4. A sufficiently tested creative within 50% of the winner:
   - action: `keep`

5. A sufficiently tested creative with no results:
   - action: `pause_candidate`

Recommendations are advisory for now.

---

## Planned Data Sources

Future integrations include:

- Instagram Graph API
- Bandcamp
- GEMA
- distributor reports
- Dropbox
- AI image analysis
- AI video analysis
- AI audio analysis

---

## Future Business Domains

MMI may eventually organize data into these release-centered domains:

```text
Release
    ├── Marketing
    ├── Audience
    ├── Streaming
    ├── Revenue
    ├── Experiments
    └── Knowledge
```

Examples:

### Marketing

- Meta Ads
- Instagram
- YouTube campaigns

### Audience

- Instagram followers
- YouTube subscribers
- Spotify followers
- Bandcamp followers

### Streaming

- Spotify
- YouTube Music
- distributor platform data

### Revenue

- Bandcamp sales
- distributor royalties
- GEMA royalties

### Experiments

- budget changes
- paused creatives
- thumbnail changes
- campaign launches
- playlist pitching

### Knowledge

- observations
- conclusions
- repeatable lessons
- recommendations for future releases

---

## Design Principles

- Data first, AI second.
- External platforms are data sources; the MMI database is the historical source of truth.
- Recommendation rules must be explainable.
- Creativity remains human-led.
- Recommendations are advisory before automation is introduced.
- Every release should add knowledge.
- Build one complete vertical feature at a time.
- Keep services, importers, models, and intelligence separate.