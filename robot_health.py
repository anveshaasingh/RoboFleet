import streamlit as st
from db import fetch_all, execute

def robot_health():
    st.header("❤️ Robot Health Metrics")

    robots = fetch_all("SELECT * FROM robots ORDER BY health_score ASC")
    for r in robots:
        st.metric(r["name"], f"{r['health_score']} / 100",
                  "Healthy" if r["health_score"] >= 70 else "Needs attention")

    rid = st.selectbox("Robot", [r["robot_id"] for r in robots])
    score = st.slider("Set health score", 0, 100, 80)
    if st.button("Update Health"):
        execute("UPDATE robots SET health_score=%s WHERE robot_id=%s", (score, rid))
        st.success("Health metric updated.")
        st.rerun()
