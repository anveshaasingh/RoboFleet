import streamlit as st
from db import fetch_all

def deadlock_alert():
    st.header("🚨 Deadlock Detection & Alert System")

    resources = fetch_all("SELECT * FROM resources")
    busy = [r for r in resources if r["status"] == "Occupied"]

    st.write(f"Occupied resources: {len(busy)}")

    # Simple educational simulation:
    # if two or more resources are occupied, show a warning for possible conflict.
    if len(busy) >= 2:
        st.error("⚠️ ALERT: Multiple shared resources are occupied. Check for possible resource conflict/deadlock.")
    else:
        st.success("✅ No possible deadlock detected by the current simplified rule.")

    st.info("This Phase-II version uses a simple resource-conflict rule. A full wait-for graph can be added in the next phase.")
