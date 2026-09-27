import streamlit as st
from db import fetch_all, execute

def battery_management():
    st.header("🔋 Battery Management")

    robots = fetch_all("SELECT * FROM robots ORDER BY robot_id")
    st.dataframe([{ "Robot": r["name"], "Battery": r["battery"], "Status": r["status"] } for r in robots],
                 use_container_width=True)

    rid = st.selectbox("Robot", [r["robot_id"] for r in robots])
    action = st.radio("Action", ["Consume battery", "Charge battery"])
    amount = st.slider("Battery change", 5, 50, 10)

    if st.button("Apply"):
        if action == "Consume battery":
            execute("""UPDATE robots
                       SET battery=GREATEST(battery-%s,0),
                           status=CASE WHEN battery-%s <= 20 THEN 'Charging' ELSE status END
                       WHERE robot_id=%s""", (amount, amount, rid))
        else:
            execute("""UPDATE robots
                       SET battery=LEAST(battery+%s,100), status='Available'
                       WHERE robot_id=%s""", (amount, rid))
        st.success("Battery updated.")
        st.rerun()
