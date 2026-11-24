import streamlit as st
from db import fetch_all


def activity_logging():

    st.header("📜 Fleet Activity Log")

    logs = fetch_all("""
        SELECT
            l.log_id,
            l.created_at,
            l.task_id,
            r.name AS robot_name,
            l.action
        FROM task_logs l
        LEFT JOIN robots r
        ON l.robot_id = r.robot_id
        ORDER BY l.created_at DESC
    """)

    if not logs:
        st.info("No activity recorded yet.")
        return

    st.dataframe(
        logs,
        use_container_width=True
    )
