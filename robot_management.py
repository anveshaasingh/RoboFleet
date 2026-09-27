import streamlit as st
from db import fetch_all, execute

def robot_management():
    st.header("🤖 Robot Management")

    with st.form("add_robot"):
        name = st.text_input("Robot name", "Robot-4")
        location = st.text_input("Starting location", "A1")
        battery = st.slider("Battery %", 0, 100, 80)
        health = st.slider("Health score", 0, 100, 100)
        if st.form_submit_button("Add Robot"):
            execute("""INSERT INTO robots(name,location,battery,status,health_score)
                       VALUES(%s,%s,%s,'Available',%s)""",
                    (name, location, battery, health))
            st.success("Robot added.")

    robots = fetch_all("SELECT * FROM robots ORDER BY robot_id")
    st.dataframe(robots, use_container_width=True)

    if robots:
        rid = st.selectbox("Select robot", [r["robot_id"] for r in robots])
        new_status = st.selectbox("Change status",
                                  ["Available","Busy","Charging","Offline","Failed"])
        if st.button("Update Robot Status"):
            execute("UPDATE robots SET status=%s WHERE robot_id=%s", (new_status, rid))
            st.success("Status updated.")
            st.rerun()
