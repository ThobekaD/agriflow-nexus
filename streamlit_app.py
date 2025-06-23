
#!/usr/bin/env python
# agriflow-nexus/streamlit_app.py
"""
🌾 AgriFlow Nexus 2.0 – SADC Supply-Chain What-If Simulator
----------------------------------------------------------
Pick a country, 1-3 commodities, origin / destination and let the
orchestrator run the full AI-agent chain.  Results include:
 • field-risk flag (drought / flood / normal)
 • 7-day weather outlook
 • 12-month price forecast (ML → rolling mean → spot fallback)
 • conflict hot-spots & route risk levels
 • truck-level logistics plan with fuel / rest stops / cost-to-serve
 • sustainability metrics and (optional) price negotiation outcome
"""
from __future__ import annotations
import sys, json, altair as alt
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
from google.cloud import bigquery

# ── local libs ────────────────────────────────────────────────────────
sys.path.append(str(Path(__file__).parent))
from config.config import Config
from orchestrator import Orchestrator
from utils.country_meta import COUNTRIES         # {ISO: "Pretty name"}
from utils.farm_locations import FARMS_BY_COUNTRY
from utils.negotiation_logic import get_dynamic_negotiation_parties # Import the new function

PROJECT     = Config.PROJECT_ID
DATASET_RAW = Config.BIGQUERY_DATASET           # ag_flow
REGION      = Config.CLOUD_REGION

SADC_ISO: List[str] = [
    "AGO","BWA","COM","COD","SWZ","LSO","MDG","MWI",
    "MUS","MOZ","NAM","SYC","ZAF","TZA","ZMB","ZWE"
]

# ── helper look-ups ───────────────────────────────────────────────────
def get_sadc_countries() -> List[str]:
    """Return ISO-3 codes for the 16 SADC members (guaranteed order)."""
    return [iso for iso in COUNTRIES if iso in SADC_ISO]

def get_all_commodities() -> List[str]:
    """
    Distinct list straight from the price table – always in sync with BQ.
    Falls back to a static list if BigQuery isn’t reachable.
    """
    try:
        client = bigquery.Client(location=REGION)
        rows = client.query(f"""
            SELECT DISTINCT commodity
            FROM `{PROJECT}.{DATASET_RAW}.commodity_prices_sadc`
            ORDER BY commodity
        """).result()
        return [r.commodity for r in rows]
    except Exception as exc:
        print("[streamlit] commodity lookup failed –", exc)
        # minimal fallback – UI will still work
        return ["Maize (corn)", "Sorghum", "Wheat"]

# ── page set-up ───────────────────────────────────────────────────────
st.set_page_config("AgriFlow Nexus", "🌐", layout="wide")
st.title("🌾 AgriFlow Nexus – SADC supply-chain optimiser")

# ── sidebar – scenario configuration ─────────────────────────────────
st.sidebar.header("⚙️ Scenario Configuration")

iso = st.sidebar.selectbox(
    "Country",
    get_sadc_countries(),
    format_func=lambda k: COUNTRIES.get(k, k),  
    index=get_sadc_countries().index("BWA"),
)

commodities = st.sidebar.multiselect(
    "Commodities (pick 1–3)",
    get_all_commodities(),
    default=["Maize (corn)"],
    max_selections=3,
)

payload_t = st.sidebar.number_input(
    "Total payload (tonnes)", 1.0, 120.0, 20.0, step=1.0
)

st.sidebar.subheader("Route")
orig_in = st.sidebar.text_input("Origin (lat,lon)", "-24.65,25.91")
dest_in = st.sidebar.text_input("Destination (lat,lon)", "-25.90,28.20")

st.sidebar.subheader("Advanced")
run_sustainability = st.sidebar.toggle("Enable Sustainability agent", True)
run_negotiation    = st.sidebar.toggle("Enable Negotiation agent", True)
price_shift_pct    = st.sidebar.slider("Manual price shift (%)", -25, 25, 0, 5)

# ―― show all agents wired into the orchestrator ――――――――――――――――――――
with st.sidebar.expander("🤖 Active AI Agents"):
    registry_preview = Orchestrator().registry       # keys = agent-ids
    for k in registry_preview:
        st.write("•", k.replace("_", " ").title())

run_btn = st.sidebar.button("🚀 Run optimisation", use_container_width=True)

def run_full_process(payload: Dict[str, Any]) -> Dict[str, Any]:
    orch = Orchestrator()

    # --- Step 1: Get Price Forecasts First ---
    price_predictor_agent = orch.registry["price_predictor"]
    all_forecasts = {}
    for comm in payload.get("commodities", []):
        price_payload = payload.copy()
        price_payload["commodity"] = comm
        price_result = price_predictor_agent.process_data(price_payload)
        if "forecast" in price_result:
            all_forecasts[comm] = price_result["forecast"]
    
    # Add forecasts to the main payload
    payload["commodity_forecasts"] = all_forecasts

    # --- Step 2: Generate Dynamic Negotiation Constraints ---
    if payload.get("negotiation_parties"):
        payload["negotiation_parties"] = get_dynamic_negotiation_parties(all_forecasts)

    # --- Step 3: Run the Rest of the Agents ---
    # Remove price predictor from the main run as it has already been executed
    agents_to_run = [
        "weather_oracle", "conflict_guard", "field_sentinel",
        "logistics_master", "sustainability_agent", "adaptive_learning_agent"
    ]
    if run_negotiation:
        # Dynamically add negotiation agent if toggled
        from agents.negotiation_agent import NegotiationAgent
        orch.registry["negotiation_agent"] = NegotiationAgent()
        agents_to_run.insert(4, "negotiation_agent") # Insert before logistics

    result = payload
    for agent_name in agents_to_run:
        if agent_name in orch.registry:
             result.update(orch._exec(agent_name, result))

    return result


# ── run orchestrator ―─────────────────────────────────────────────────
if run_btn:
    if not commodities:
        st.error("Please select at least one commodity.")
        st.stop()

    with st.spinner("Running all agents…"):
        try:
            orig_lat, orig_lon = map(float, orig_in.replace(" ", "").split(","))
            dest_lat, dest_lon = map(float, dest_in.replace(" ", "").split(","))
        except ValueError:
            st.error("⚠️  Coordinates must be 'lat,lon'.")
            st.stop()

        farms = FARMS_BY_COUNTRY.get(iso)
        if not farms:
            st.error(f"No demo farm points for {COUNTRIES[iso]}.")
            st.stop()

        seed_payload = {
            "country_iso": iso,
            "commodities": commodities,
            "horizon": 12,
            "price_shift": price_shift_pct,
            "payload_tonnes": payload_t,
            "start_coord": (orig_lat, orig_lon),
            "end_coord":   (dest_lat, dest_lon),
            "farm_coords": farms,
            "routes": [
                {"truck": "T1", "stops": list(farms)[:len(farms)//2]},
                {"truck": "T2", "stops": list(farms)[len(farms)//2:]},
            ],
        }

        if run_negotiation:
            # Add a placeholder that will be replaced after forecasts are run
            seed_payload["negotiation_parties"] = True 

        # The main change is to call our new function instead of orchestrator.start
        result = run_full_process(seed_payload)

    st.success("✅ All agents completed")

    # ── headline KPIs ―───────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    k1.metric("Field risk (30 d)", result.get("risk", "unknown").title())
    k2.metric("Carbon footprint (kg CO₂)",
              f"{result.get('total_carbon_footprint_kg_co2',0):,.0f}")
    k3.metric("Sustainability score",
              f"{result.get('overall_sustainability_score',0):.2f} / 1.0")

    # ── price forecasts ―─────────────────────────────────────────────
    st.subheader("💰 Price forecasts")
    fcasts = result.get("commodity_forecasts")
    if fcasts:
        all_dfs = []
        for comm, rows in fcasts.items():
            df = pd.DataFrame(rows)
            df['commodity'] = comm
            all_dfs.append(df)

        if all_dfs:
            final_df = pd.concat(all_dfs)
            st.altair_chart(
                alt.Chart(final_df).mark_line(point=True, strokeWidth=3).encode(
                    x="year:O",
                    y=alt.Y("price:Q", title="USD / t", scale=alt.Scale(zero=False)),
                    color=alt.Color("commodity:N", title="Commodity"),
                    tooltip=["year", "price", "commodity"]
                ).properties(
                    title="Commodity Price Forecasts"
                ).interactive(),
                use_container_width=True,
            )
    else:
        st.info("No forecasts produced.")

    # ── logistics plan ―──────────────────────────────────────────────
    st.subheader("🛣️ Logistics plan")
    if "routes" in result:
        df_routes = pd.DataFrame(result["routes"])
        wanted = ["truck", "total_km", "risk_level",
                  "fuel_usd", "cost_per_tonne", "rest_stops"]
        st.dataframe(df_routes[[c for c in wanted if c in df_routes.columns]],
                     use_container_width=True)

    # ── sustainability detail ───────────────────────────────────────
    if run_sustainability and "sustainability_metrics" in result:
        st.subheader("🌱 Sustainability detail")
        for m in result["sustainability_metrics"]:
            truck_tag = m.get("truck_id", "N/A")
            with st.expander(f"Truck {truck_tag}"):
                st.json(m, expanded=False)

    # ── negotiation parties ―────────────────────────────────────────
    if "negotiation_parties" in result and isinstance(result["negotiation_parties"], list):
        st.subheader("👥 Negotiation Parties")
        parties_data = []
        for p in result["negotiation_parties"]:
            party_info = {
                "ID": p.get("id"),
                "Type": p.get("type"),
                "Constraint": "N/A"
            }
            if "constraints" in p:
                constraints = p["constraints"]
                if "min_price" in constraints:
                    party_info["Constraint"] = f"Min Price: ${constraints['min_price']}"
                elif "max_price" in constraints:
                    party_info["Constraint"] = f"Max Price: ${constraints['max_price']} (Quality: {constraints.get('quality', 'any')})"
            parties_data.append(party_info)
        
        st.dataframe(pd.DataFrame(parties_data), use_container_width=True)

    # ── negotiation outcome ―────────────────────────────────────────
    if run_negotiation and "negotiation_agreement" in result:
        st.subheader("🤝 Negotiation")
        na = result["negotiation_agreement"]
        if na.get("status") == "success":
            st.success(f"Agreed price : **${na['agreed_price']} / t** "
                       f"(quality = {na['quality']})")
        else:
            st.warning(f"Negotiation failed – {na.get('reason','unknown')}")

    # ── download full JSON ―─────────────────────────────────────────
    st.download_button(
        "💾 Download full JSON result",
        json.dumps(result, indent=2, default=str),
        file_name=f"agriflow_{iso}_{datetime.now().date()}.json",
        mime="application/json",
    )

    # ── raw JSON expander ―──────────────────────────────────────────
    with st.expander("🔍 Full JSON payload"):
        st.json(result, expanded=False)

else:
    st.info("Configure a scenario on the left and press **Run optimisation**.")