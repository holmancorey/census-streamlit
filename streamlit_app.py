"""
Census Explorer - Streamlit version.

Same three Census queries as the Lambda version, but rendered by Streamlit.
Run locally:   streamlit run streamlit_app.py
On EC2:        run as a systemd service (see setup steps).

Needs the CENSUS_API_KEY environment variable.
"""

import os
from urllib.parse import urlencode

import requests  # installed automatically with streamlit
import streamlit as st

BASE = "https://api.census.gov/data/2023/acs/acs5"
API_KEY = os.environ.get("CENSUS_API_KEY", "")

QUERIES = {
    "Population by state": {"get": "NAME,B01003_001E", "for": "state:*"},
    "Median household income by state": {"get": "NAME,B19013_001E", "for": "state:*"},
    "Population by Maryland county": {
        "get": "NAME,B01003_001E", "for": "county:*", "in": "state:24"
    },
}

LABELS = {
    "NAME": "Name",
    "B01003_001E": "Population",
    "B19013_001E": "Median household income ($)",
    "state": "State FIPS",
    "county": "County FIPS",
}


@st.cache_data(ttl=3600)  # remember results for an hour so repeat clicks are instant
def fetch_census(label: str) -> list[dict]:
    params = {**QUERIES[label], "key": API_KEY}
    # Build the query string ourselves and leave : * , unencoded.
    # requests would turn "state:24" into "state%3A24", which the Census API
    # rejects for the "in" parameter (400 error).
    query = urlencode(params, safe=":*,")
    resp = requests.get(f"{BASE}?{query}", timeout=10)
    if not resp.ok:
        # Don't use raise_for_status(): its message includes the full URL,
        # which would put the API key on the page and in the logs.
        raise RuntimeError(f"Census returned HTTP {resp.status_code}: {resp.text[:200]}")
    header, *rows = resp.json()
    header = [LABELS.get(h, h) for h in header]
    return sorted((dict(zip(header, r)) for r in rows), key=lambda d: d["Name"])


st.set_page_config(page_title="Census Explorer", layout="wide")
st.title("Census Explorer v2")
st.caption("Source: ACS 5-year estimates, 2023")

if not API_KEY:
    st.error("CENSUS_API_KEY environment variable is not set.")
    st.stop()

# Three buttons side by side; remember which one was clicked last
cols = st.columns(len(QUERIES))
for col, label in zip(cols, QUERIES):
    if col.button(label, width="stretch"):
        st.session_state["choice"] = label

choice = st.session_state.get("choice")
if choice:
    st.subheader(choice)
    try:
        data = fetch_census(choice)
        st.write(f"{len(data)} rows")
        st.dataframe(data, hide_index=True, width="stretch")
    except Exception as e:
        print(f"Census call failed: {e!r}")  # goes to the service log on EC2
        st.error(f"Census API call failed: {e}")
else:
    st.info("Pick a button.")
