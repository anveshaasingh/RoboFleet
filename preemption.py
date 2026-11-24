import streamlit as st
from db import fetch_all, execute


def preemption():

    st.header("⏸️ Task Preemption")

    busy_tasks = fetch_all("""
        SELECT t.*, r.name AS robot_name
        FROM tasks t
        JOIN robots r
        ON t.assigned_robot = r.robot_id
        WHERE t.status='Assigned'
        AND r.status='Busy'
    """)

    pending_tasks = fetch_all("""
        SELECT *
        FROM tasks
        WHERE status='Pending'
        ORDER BY priority DESC
    """)

    if not busy_tasks:
        st.info("No running tasks available.")
        return

    if not pending_tasks:
        st.info("No higher-priority pending task available.")
        return

    running_map = {
        f"Task {t['task_id']} - {t['task_name']} "
        f"({t['robot_name']})": t
        for t in busy_tasks
    }

    new_task_map = {
        f"Task {t['task_id']} - {t['task_name']} "
        f"(Priority {t['priority']})": t
        for t in pending_tasks
    }

    running_label = st.selectbox(
        "Running Task",
        list(running_map.keys())
    )

    new_label = st.selectbox(
        "New Task",
        list(new_task_map.keys())
    )

    current_task = running_map[running_label]
    new_task = new_task_map[new_label]

    st.write(
        f"Current priority: **{current_task['priority']}**"
    )

    st.write(
        f"New task priority: **{new_task['priority']}**"
    )

    if st.button("Preempt Task"):

        if new_task["priority"] <= current_task["priority"]:
            st.warning(
                "Preemption not required because "
                "the new task does not have higher priority."
            )
            return

        robot_id = current_task["assigned_robot"]

        # Pause current task
        execute("""
            UPDATE tasks
            SET status='Pending',
                assigned_robot=NULL
            WHERE task_id=%s
        """, (
            current_task["task_id"],
        ))

        # Assign new task
        execute("""
            UPDATE tasks
            SET status='Assigned',
                assigned_robot=%s
            WHERE task_id=%s
        """, (
            robot_id,
            new_task["task_id"]
        ))

        execute("""
            UPDATE robots
            SET current_task_id=%s,
                status='Busy'
            WHERE robot_id=%s
        """, (
            new_task["task_id"],
            robot_id
        ))

        # Log event
        execute("""
            INSERT INTO task_logs
            (task_id, robot_id, action)
            VALUES (%s, %s, %s)
        """, (
            current_task["task_id"],
            robot_id,
            "Task preempted by higher priority task"
        ))

        execute("""
            INSERT INTO task_logs
            (task_id, robot_id, action)
            VALUES (%s, %s, %s)
        """, (
            new_task["task_id"],
            robot_id,
            "Higher priority task started after preemption"
        ))

        st.success(
            f"Task {current_task['task_id']} preempted. "
            f"Task {new_task['task_id']} assigned."
        )

        st.rerun()
