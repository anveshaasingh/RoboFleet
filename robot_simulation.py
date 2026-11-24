import streamlit as st
from db import fetch_all, execute


def robot_simulation():

    st.header("🤖 Robot Task Simulation")

    robots = fetch_all("""
        SELECT *
        FROM robots
        WHERE status='Busy'
    """)

    if not robots:
        st.info("No robots are currently executing tasks.")
        return

    robot_map = {
        f"{r['name']} - Task {r['current_task_id']}": r
        for r in robots
    }

    selected = st.selectbox(
        "Select Robot",
        list(robot_map.keys())
    )

    robot = robot_map[selected]

    task = fetch_all("""
        SELECT *
        FROM tasks
        WHERE task_id=%s
    """, (robot["current_task_id"],))

    if not task:
        st.warning("No task found.")
        return

    task = task[0]

    st.write(f"**Task:** {task['task_name']}")
    st.write(f"Current Location: {robot['location']}")
    st.write(f"Destination: {task['destination']}")
    st.write(f"Battery: {robot['battery']}%")

    if st.button("Execute Task Step"):

        # Move robot to destination
        execute("""
            UPDATE robots
            SET location=%s
            WHERE robot_id=%s
        """, (
            task["destination"],
            robot["robot_id"]
        ))

        # Consume battery
        new_battery = max(
            0,
            robot["battery"] - 10
        )

        execute("""
            UPDATE robots
            SET battery=%s
            WHERE robot_id=%s
        """, (
            new_battery,
            robot["robot_id"]
        ))

        # Complete task
        execute("""
            UPDATE tasks
            SET status='Completed'
            WHERE task_id=%s
        """, (
            task["task_id"],
        ))

        execute("""
            UPDATE robots
            SET status='Available',
                current_task_id=NULL
            WHERE robot_id=%s
        """, (
            robot["robot_id"],
        ))

        execute("""
            INSERT INTO task_logs
            (task_id, robot_id, action)
            VALUES (%s, %s, %s)
        """, (
            task["task_id"],
            robot["robot_id"],
            "Task completed through simulation"
        ))

        st.success(
            f"{robot['name']} completed the task."
        )

        st.rerun()