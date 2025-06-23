# AgriFlow Nexus: System Architecture & Documentation

**Version:** 2.1
**Last Updated:** June 23, 2025

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [System Components (Agent Layer)](#3-system-components-agent-layer)
4. [Execution Flow](#4-execution-flow)
5. [Setup & Installation](#5-setup--installation)

---

## 1. Overview

AgriFlow Nexus is an advanced, **agent‑based AI system** designed for supply‑chain optimisation and *what‑if* scenario simulation within the Southern African Development Community (SADC) agricultural sector.

By orchestrating multiple specialised AI agents, AgriFlow Nexus delivers a holistic, data‑driven view of agricultural supply chains. **Users configure a scenario** (country, commodity mix, transport routes), and the platform automatically produces:

* 📈 **Multi‑commodity price forecasts** (12‑month horizon)
* 🚚 **Optimised two‑truck logistics plans**
* 🌾 **Field risk assessments** (drought/flood)
* 🔐 **Route‑specific conflict analysis** (ACLED)
* 🌍 **Sustainability metrics** (carbon & water usage)
* 🤝 **Dynamic negotiation simulations**

---

## 2. System Architecture

AgriFlow Nexus follows a **modular, multi‑agent architecture** with four primary layers:

1. **User Interface** – a Streamlit web app (`streamlit_app.py`)
2. **Orchestration Layer** – the Orchestrator (`orchestrator.py`) that schedules agents
3. **Agent Layer** – domain‑specific Python classes (⚙️ below)
4. **Data Layer** – Google BigQuery datasets

### Architecture Diagram

```mermaid
graph TD
    subgraph User Interface
        A[Streamlit Web App\n(streamlit_app.py)]
    end

    subgraph Orchestration Layer
        B[Orchestrator\n(orchestrator.py)]
    end

    subgraph Agent Layer
        C[PricePredictor]
        D[FieldSentinel]
        E[WeatherOracle]
        F[ConflictGuard]
        G[LogisticsMaster]
        H[SustainabilityAgent]
        I[NegotiationAgent]
        J[AdaptiveLearningAgent]
    end

    subgraph Data Layer
        K[Google BigQuery\n\n**Tables:**\n- commodity_prices_sadc\n- fuel_price_sadc\n- acled_events_sadc\n- precip_sadc\n- soil_moist_sadc\n- road_network_sadc]
    end

    %% Connections
    A -- 1. User Input --> B;
    B -- 2. Runs PricePredictor Loop --> C;
    C -- 2a. Queries Data --> K;
    B -- 3. Runs Parallel Agents --> D & E & F;
    D & E & F -- 3a. Query Data --> K;
    B -- 4. Runs Sequential Agents --> I & G & H & J;
    G & H & I -- 4a. Use Data from Previous Agents --> B;
    B -- 5. Returns Final JSON --> A;
    A -- 6. Displays Visualisations --> A;
```

---

## 3. System Components (Agent Layer)

Each agent is a **self‑contained Python class** tackling a single domain. Key methods: `process_data()` and (optionally) `communicate_with_agent()`.

| Agent                     | Purpose                                            | Core Logic                                                                        |
| ------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------- |
| **FieldSentinel**         | Assess near‑term agricultural risk (drought/flood) | Pull 30‑day precipitation & soil‑moisture → risk level `normal / drought / flood` |
| **WeatherOracle**         | 7‑day weather forecast                             | Historical weather → statistical forecast with graceful fallback                  |
| **PricePredictor**        | 12‑month commodity price forecast                  | 5‑yr rolling mean trended with diesel; fallbacks: spot → random stub              |
| **ConflictGuard**         | Security risk along routes                         | Scan 90‑day ACLED events near route buffer                                        |
| **LogisticsMaster**       | Two‑truck routing & cost                           | Solve VRP via **Google OR‑Tools**; return path, fuel, rest stops                  |
| **SustainabilityAgent**   | Carbon & water impact                              | CO₂ ≈ distance × fuel efficiency; water use by commodity                          |
| **NegotiationAgent**      | Simulated buyer–seller deal                        | Mid‑point between min seller & max buyer, respecting forecast bands               |
| **AdaptiveLearningAgent** | Continuous improvement                             | Collect feedback → confidence score; schedule model retraining                    |

---

## 4. Execution Flow

1. **User Input** → Streamlit UI collects scenario parameters.
2. **Price Forecast Loop** → Orchestrator runs `PricePredictor` per commodity.
3. **Parallel Data Gathering** → `FieldSentinel`, `WeatherOracle`, `ConflictGuard` execute concurrently.
4. **Dynamic Negotiation Setup** → UI builds constraints for `NegotiationAgent` (if enabled).
5. **Sequential Processing**

   1. `LogisticsMaster` (routes)
   2. `NegotiationAgent`
   3. `SustainabilityAgent`
6. **Learning Cycle** → `AdaptiveLearningAgent` scores run & schedules retraining.
7. **Return & Display** → Aggregated JSON → Streamlit dashboards (KPIs, charts, tables).

---

## 5. Setup & Installation

> **Prerequisites:** Python ≥ 3.11, Google Cloud SDK, BigQuery API enabled.

```bash
# 1. Clone the repo
$ git clone https://github.com/ThobekaD/agriflow-nexus.git
$ cd agriflow-nexus

# 2. Authenticate with Google Cloud
$ gcloud auth application-default login
$ gcloud config set project fieldsense-optimizer

# 3. Create & activate a virtual environment
$ python3 -m venv .venv
$ source .venv/bin/activate

# 4. Install dependencies
$ pip install -r requirements.txt

# 5. Launch the Streamlit app
$ streamlit run streamlit_app.py
```

---

### 💡 Need Help?

Open an issue or start a discussion on GitHub — contributions & suggestions are welcome!
