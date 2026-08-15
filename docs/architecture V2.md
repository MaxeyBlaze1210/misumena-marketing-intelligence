# MMI Architecture

## Purpose

Misumena Marketing Intelligence is a release-centered marketing intelligence and campaign management system for independent music.

MMI connects four major activities:

1. planning
2. execution
3. measurement
4. intelligence

The database preserves the relationships between these activities so that marketing knowledge can accumulate across releases.

The architecture therefore needs to support both directions of information flow:

```text
External platforms → MMI
```

and:

```text
MMI → External platforms
```

---

# Architectural Overview

MMI is organized around music releases.

At a high level:

```text
                         ┌───────────────────┐
                         │      Release      │
                         └─────────┬─────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
             ▼                     ▼                     ▼
         Planning              Execution             Ingestion
             │                     │                     │
             │                     ▼                     │
             │              External Platforms           │
             │                     │                     │
             └──────────────┬──────┴──────────────┬─────┘
                            │                     │
                            ▼                     ▼
                         Database             Metrics
                            │                     │
                            └──────────┬──────────┘
                                       ▼
                                 Intelligence
                                       │
                                       ▼
                            Evidence / Recommendations
                                       │
                                       ▼
                                Human Decisions
```

This is not a single linear pipeline.

MMI contains several related flows that share the same historical data model.

---

# Core Application Flows

## 1. Planning Flow

Planning converts human campaign decisions into structured MMI objects.

```text
User / Release Workspace
          ↓
FastAPI Route
          ↓
Planning / Application Logic
          ↓
Campaign Plan
Campaign Variants
Selected Assets
Campaign Cells
          ↓
Database
```

Planning objects describe intended campaign behavior before external platform execution occurs.

Examples include:

- objective
- optimization goal
- conversion event
- destination URL
- call to action
- countries
- age range
- total budget
- schedule
- targeting hypotheses
- selected creative assets
- advertising copy

---

## 2. Campaign Construction Flow

Campaign construction translates an MMI campaign specification into external Meta objects.

```text
MMI Campaign Plan
        ↓
Application / Launch Service
        ↓
Platform Service
        ↓
Meta Marketing API
        ↓
External Object
        ↓
Readback / Validation
        ↓
Local Mapping
```

For the current Meta implementation:

```text
Campaign Plan
      ↓
Meta Campaign
      ↓
Campaign Variants × Creative Assets
      ↓
Campaign Cells
      ↓
Meta Ad Sets
      ↓
Dropbox Creative Asset
      ↓
Meta Video
      ↓
Meta Ad Creative
      ↓
Meta Ad
```

External IDs are stored in MMI so later operations can reconcile existing objects rather than create duplicates.

---

## 3. Execution Flow

Execution changes external campaign state after construction.

Conceptually:

```text
Desired MMI State
        ↓
Execution Preview
        ↓
Difference Calculation
        ↓
Human Review / Authorization
        ↓
Execution Apply
        ↓
External Platform
        ↓
Readback
        ↓
Updated Local State
```

Construction and execution are deliberately separated.

Creating campaign infrastructure does not imply permission to start spending money.

---

## 4. Measurement / Ingestion Flow

External performance data is imported into MMI.

```text
External Platform
        ↓
Platform Service
        ↓
Importer / Sync Logic
        ↓
Normalized Database Models
        ↓
Historical Metrics
```

Example:

```text
Meta Marketing API
        ↓
meta_service.py
        ↓
Meta import / synchronization
        ↓
meta_campaigns
meta_ads
meta_ad_metrics
        ↓
Intelligence
```

Importers should preserve historical data and avoid accidental duplication.

---

## 5. Intelligence Flow

The intelligence layer operates primarily on normalized MMI data.

```text
Campaign Plans
      +
Experiments
      +
Execution History
      +
Performance Metrics
      +
Streaming Outcomes
      +
Revenue Data
        ↓
Intelligence Layer
        ↓
Observations
Comparisons
Evidence
Recommendations
        ↓
Human Decision
        ↓
Future Experiment / Execution
```

The intelligence layer should not require direct external API calls to reason about historical evidence.

---

# Architectural Layers

## `app/api`

FastAPI routes and HTTP-facing application entry points.

Responsibilities:

- receive HTTP requests
- validate request parameters
- resolve release/workspace context
- call application services
- return responses or render templates
- perform redirects after mutations

Routes should remain thin where practical.

They should not contain low-level Meta, Dropbox, Spotify or YouTube HTTP logic.

---

## `app/services`

The services directory currently contains two conceptually different types of service.

These should be distinguished architecturally even if they remain in the same physical directory during the MVP.

---

### Platform Services

Platform services communicate with external systems.

Examples include:

```text
meta_service.py
dropbox_service.py
spotify_service.py
youtube_service.py
youtube_analytics_service.py
```

Responsibilities:

- authenticate with external platforms
- construct external API requests
- perform API calls
- handle platform-specific errors
- return raw or lightly normalized responses
- expose small platform-specific operations

Examples:

```text
upload video
create Meta ad
read Meta ad set
download Dropbox asset
retrieve Spotify data
retrieve YouTube analytics
```

Platform services should not decide campaign strategy.

They should not contain recommendation rules.

They should avoid owning broader application workflows.

---

### Application / Orchestration Services

Application services coordinate MMI business operations.

Current examples include services such as:

```text
meta_campaign_launch_service.py
meta_adset_launch_service.py
meta_ad_launch_service.py
meta_execution_preview_service.py
meta_execution_diff_service.py
meta_execution_apply_service.py
asset_sync_service.py
intelligence_reporting_service.py
```

Responsibilities may include:

- reading database state
- applying application rules
- coordinating multiple models
- calling platform services
- persisting external object mappings
- reconciling local and external state
- enforcing safety invariants
- coordinating multi-step workflows

Unlike platform services, application services **may write to the database**.

For example:

```text
Campaign Cell
      ↓
Application Launch Service
      ├── reads campaign plan
      ├── reads creative mapping
      ├── calls Meta platform service
      ├── validates response
      └── stores Meta object ID
```

This distinction replaces the earlier blanket rule that services should never write to the database.

---

## `app/importers`

Importers are responsible for historical or analytical data ingestion.

Responsibilities:

- call platform services
- transform external data
- normalize platform-specific fields
- create or update database records
- avoid duplicates
- preserve historical observations

Examples include:

```text
meta_importer.py
```

Potential future importers include:

```text
youtube_importer.py
spotify_importer.py
distributor_importer.py
gema_importer.py
```

Importers are one subsystem of MMI rather than the central architecture of the entire application.

---

## `app/models`

SQLAlchemy database models.

Models represent persistent application state.

Domains currently or increasingly represented include:

```text
Release
Track
Artist
Assets

Campaign Plans
Campaign Variants
Campaign Cells
Campaign Plan Assets

Meta Campaigns
Meta Ad Sets
Meta Ads
Meta Metrics

YouTube Data
Spotify Data

Experiments
Recommendations
```

Models should define persistence and relationships.

They should not perform external API calls or contain platform orchestration.

---

## `app/intelligence`

Decision and analysis logic.

Responsibilities:

- read normalized historical data
- compare experiments
- identify patterns
- apply transparent rules
- calculate confidence where appropriate
- generate explainable recommendations
- accumulate cross-release knowledge

The intelligence layer should be largely platform-independent.

It should reason about MMI concepts rather than depend directly on Meta, Spotify or YouTube API response structures.

Potential future components include:

- creative comparison
- audience comparison
- country comparison
- trend detection
- anomaly detection
- confidence scoring
- downstream listener-value estimation
- cross-release learning

---

## `app/database`

Database configuration and initialization.

Current responsibilities include:

- SQLAlchemy engine
- session management
- database initialization

The database is MMI's historical source of truth for:

- internal plans
- mappings to external objects
- historical measurements
- experiment structure
- decisions
- accumulated knowledge

External platforms remain authoritative for their current external state.

MMI preserves the historical relationship between that state and its own plans and decisions.

---

## `app/core`

Application configuration.

Current responsibilities include:

- environment configuration
- credentials
- platform identifiers
- API configuration

Secrets and credentials are loaded from `.env` and must not be committed to source control.

---

## `app/templates`

Server-rendered workspace UI.

Responsibilities include presenting:

- release information
- assets
- campaign planning
- campaign construction status
- analytics
- intelligence

Templates should display application state rather than contain business logic.

---

# Campaign Domain Model

MMI's Meta campaign architecture distinguishes several concepts.

## Campaign Plan

The campaign plan describes the overall intended campaign.

Examples:

- objective
- optimization goal
- conversion event
- destination
- CTA
- geography
- age
- budget
- schedule

---

## Campaign Variant

A campaign variant represents a targeting or audience hypothesis.

Examples:

```text
CONTROL
Broad

COMPARATOR 1
Interest hypothesis A

COMPARATOR 2
Interest hypothesis B
```

Variants allow MMI to compare audience strategies within the same campaign experiment.

---

## Creative Asset

A creative asset is release-related media that may be used in advertising.

Assets may originate from Dropbox or other future asset stores.

Creative metadata may include:

- filename
- source
- external file identifier
- advertising copy
- external video ID
- external creative ID

---

## Campaign Cell

A campaign cell represents the intersection between:

```text
Campaign Variant × Creative Asset
```

For example:

```text
Broad × Creative 1
Broad × Creative 2

Comparator A × Creative 1
Comparator A × Creative 2
```

The campaign cell is the fundamental experimental unit for campaign construction and comparison.

It can map to a Meta ad set and subsequently to an ad.

---

# External Object Mapping

MMI must preserve mappings between internal objects and external platform objects.

Example:

```text
MMI Campaign Plan
      ↕
Meta Campaign ID

MMI Campaign Cell
      ↕
Meta Ad Set ID

MMI Creative Mapping
      ↕
Meta Video ID
      ↕
Meta Ad Creative ID

MMI Ad Record
      ↕
Meta Ad ID
```

These mappings enable reconciliation.

Without them, repeated operations could accidentally create duplicate external objects.

---

# Reconciliation and Idempotency

External platform writes cannot be treated like ordinary database transactions.

Once Meta creates an object, rolling back the local SQLite transaction does not delete the Meta object.

Therefore MMI follows a reconciliation model.

Before creating an external object:

```text
Does MMI already know its external ID?
        │
      yes
        ↓
Read external object
Validate relationship/state
Reuse / reconcile
```

Otherwise:

```text
Create external object
        ↓
Read it back
        ↓
Validate it
        ↓
Persist mapping
```

Where practical, repeated application operations should converge on the same intended state rather than create duplicates.

---

# External Write Safety

Advertising platform mutations can spend real money.

They therefore require stronger safety guarantees than ordinary data retrieval.

Current principles:

### 1. Construction is not activation

New Meta objects are created paused.

```text
Campaign creation ≠ campaign activation
```

### 2. Read after write

Important external objects should be read back after creation.

### 3. Validate relationships

Examples:

- ad set belongs to expected campaign
- ad references expected creative
- external object exists
- newly created object is paused

### 4. Persist external identifiers

Successful writes should create durable local mappings.

### 5. Reconcile before recreating

Existing mappings should be validated and reused.

### 6. Separate desired state from external state

Execution logic should compare:

```text
What MMI wants
        vs.
What Meta currently has
```

before applying mutations.

### 7. Human authorization remains explicit

MMI may generate recommendations or prepare changes, but consequential campaign execution should remain observable and deliberately authorized during the MVP.

---

# Campaign State Lifecycle

Conceptually, a campaign progresses through states such as:

```text
Draft
  ↓
Configured
  ↓
Ready to Build
  ↓
Built / Paused
  ↓
Ready to Execute
  ↓
Active
  ↓
Monitoring
  ↓
Optimizing
  ↓
Completed
  ↓
Analyzed
  ↓
Knowledge Preserved
```

The exact persisted state model may evolve, but the architectural separation between these stages should remain.

---

# Recommendation Architecture

The recommendation system should operate on stored evidence rather than transient dashboard state.

Initial recommendation logic uses simple rules such as:

```text
impressions >= 2000
```

before considering a creative sufficiently tested.

These rules are deliberately transparent and represent an MVP baseline.

The long-term intelligence model should incorporate additional signals such as:

- creative performance
- audience performance
- country performance
- campaign history
- early engagement signals
- conversion quality
- downstream streaming behavior
- listener retention
- financial outcomes

The intelligence layer should distinguish between:

```text
observation
hypothesis
evidence
recommendation
decision
outcome
```

These concepts should not be collapsed into a single AI-generated judgment.

---

# Release-Centered Knowledge Model

MMI may increasingly organize information into these domains:

```text
Release
    ├── Assets
    ├── Marketing
    ├── Audience
    ├── Streaming
    ├── Revenue
    ├── Experiments
    ├── Decisions
    └── Knowledge
```

### Assets

- advertising videos
- artwork
- thumbnails
- music assets

### Marketing

- Meta campaigns
- Instagram activity
- YouTube campaigns
- other promotional activity

### Audience

- social followers
- subscribers
- listeners
- geographic audiences

### Streaming

- Spotify
- Apple Music
- YouTube
- other platforms

### Revenue

- distributor royalties
- performance royalties
- direct sales

### Experiments

- audience comparisons
- creative comparisons
- budget changes
- campaign changes
- thumbnail tests
- other marketing hypotheses

### Decisions

- campaign launches
- pauses
- budget reallocations
- scaling decisions
- manual overrides

### Knowledge

- observations
- conclusions
- repeatable lessons
- recommendations for future releases

---

# Cross-Platform Intelligence

MMI should not assume that success on one platform is equivalent to overall marketing success.

A listener may choose:

```text
Meta / Marketing
       ↓
Landing Page
       ├── Spotify
       ├── Apple Music
       ├── YouTube
       ├── Tidal
       └── other destinations
```

The long-term goal is to evaluate **qualified listener acquisition** and downstream value across platforms.

Where possible, future models should learn platform value from Misumena's own historical streaming and royalty data rather than relying on generic industry payout assumptions.

---

# Development Principles

## Data first, AI second

AI operates on structured evidence.

It should not substitute for missing data.

---

## Release-centered architecture

Campaigns, assets, analytics, revenue and knowledge should remain traceable to releases.

---

## Separate platform operations from application workflows

Low-level external API communication belongs in platform services.

Multi-step business operations belong in application/orchestration services.

---

## Preserve history

Do not optimize the database solely for current state.

MMI exists partly to remember what happened.

---

## Explain recommendations

Recommendations should contain evidence and reasoning.

---

## Creativity remains human-led

MMI supports creative decisions.

It does not attempt to replace artistic judgment.

---

## Safe external writes

External mutations must be deliberate, observable and reconcilable.

---

## Prefer reconciliation over duplication

Repeated operations should converge toward intended state.

---

## Separate construction from activation

Building an advertising campaign must not automatically start spending.

---

## Preserve decisions as evidence

A campaign change is itself useful historical information.

Where possible, MMI should eventually preserve:

```text
what changed
when it changed
why it changed
who/what recommended it
what happened afterwards
```

---

## Build one complete vertical feature at a time

Prefer complete end-to-end capabilities over many disconnected integrations.

---

# Long-Term Architectural Direction

The long-term MMI learning loop is:

```text
                  ┌──────────────────┐
                  │   Past Releases  │
                  └────────┬─────────┘
                           │
                           ▼
                       Knowledge
                           │
                           ▼
                    New Release Plan
                           │
                           ▼
                       Campaign
                           │
                           ▼
                       Execution
                           │
                           ▼
                      Measurement
                           │
                           ▼
                       Analysis
                           │
                           ▼
                        Lessons
                           │
                           └──────────────┐
                                          │
                                          ▼
                                   Future Releases
```

The ultimate objective is not campaign automation for its own sake.

It is cumulative learning.

Every campaign should leave MMI with more evidence than it had before the campaign began.