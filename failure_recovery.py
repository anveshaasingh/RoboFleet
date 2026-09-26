import streamlit as st
from db import fetch_all, execute


def failure_recovery():
    st.header("🛠️ Failure Recovery")

    robots = fetch_all(
        "SELECT * FROM robots "
        "WHERE status IN ('Busy','Available','Charging')"
    )

    if not robots:
        st.info("No robots available for failure simulation.")
        return

    rid = st.selectbox(
        "Robot to simulate failure",
        [r["robot_id"] for r in robots]
    )

    if st.button("Simulate Robot Failure"):
        robot = next(r for r in robots if r["robot_id"] == rid)
        task_id = robot["current_task_id"]

        execute(
            "UPDATE robots SET status='Failed', current_task_id=NULL "
            "WHERE robot_id=%s",
            (rid,)
        )

        if task_id:
            execute(
                "UPDATE tasks SET status='Pending', assigned_robot=NULL "
                "WHERE task_id=%s",
                (task_id,)
            )

            execute(
                "INSERT INTO failures(robot_id,reason,recovered_task) "
                "VALUES(%s,%s,%s)",
                (rid, "Robot failed during execution", task_id)
            )
        else:
            execute(
                "INSERT INTO failures(robot_id,reason) "
                "VALUES(%s,%s)",
                (rid, "Robot failure simulation")
            )

        st.warning(
            "Robot marked as Failed and incomplete task returned to Pending."
        )
        st.rerun()

    st.subheader("Failure Records")
    st.dataframe(
        fetch_all(
            "SELECT * FROM failures ORDER BY failure_id DESC"
        ),
        use_container_width=True
    )
