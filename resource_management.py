import streamlit as st
from db import fetch_all, execute

def resource_management():
    st.header("🧰 Resource Management")

    resources = fetch_all("""SELECT res.*, r.name AS robot_name
                             FROM resources res LEFT JOIN robots r
                             ON res.occupied_by=r.robot_id
                             ORDER BY resource_id""")
    st.dataframe(resources, use_container_width=True)

    if resources:
        resource = st.selectbox("Resource", [r["resource_id"] for r in resources])
        robots = fetch_all("SELECT * FROM robots ORDER BY robot_id")
        robot_options = {"Free": None, **{r["name"]: r["robot_id"] for r in robots}}
        robot_name = st.selectbox("Occupy by", list(robot_options.keys()))

        if st.button("Update Resource"):
            execute("UPDATE resources SET occupied_by=%s,status=%s WHERE resource_id=%s",
                    (robot_options[robot_name],
                     "Occupied" if robot_options[robot_name] else "Free",
                     resource))
            st.success("Resource updated.")
            st.rerun()
