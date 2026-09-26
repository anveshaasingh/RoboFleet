import streamlit as st
from db import fetch_all, execute


def smart_assignment():
    st.header("🎯 Smart Task Assignment")

    tasks = fetch_all(
        "SELECT * FROM tasks WHERE status='Pending' "
        "ORDER BY priority DESC, deadline ASC"
    )
    robots = fetch_all(
        "SELECT * FROM robots "
        "WHERE status='Available' AND battery >= 20"
    )

    if not tasks:
        st.info("No pending tasks.")
        return

    if not robots:
        st.warning("No available robots with enough battery.")
        return

    task_map = {
        f"Task {t['task_id']} - {t['task_name']}": t
        for t in tasks
    }
    robot_map = {
        f"Robot {r['robot_id']} - {r['name']}": r
        for r in robots
    }

    task_label = st.selectbox("Select task", list(task_map.keys()))
    robot_label = st.selectbox("Select robot", list(robot_map.keys()))

    if st.button("Assign Task"):
        task = task_map[task_label]
        robot = robot_map[robot_label]

        execute(
            "UPDATE tasks SET assigned_robot=%s,status='Assigned' "
            "WHERE task_id=%s",
            (robot["robot_id"], task["task_id"])
        )

        execute(
            "UPDATE robots SET status='Busy',current_task_id=%s "
            "WHERE robot_id=%s",
            (task["task_id"], robot["robot_id"])
        )

        execute(
            "INSERT INTO task_logs(task_id,robot_id,action) "
            "VALUES(%s,%s,%s)",
            (
                task["task_id"],
                robot["robot_id"],
                "Task manually assigned"
            )
        )

        st.success(
            f"{task['task_name']} assigned to {robot['name']}."
        )
        st.rerun()
