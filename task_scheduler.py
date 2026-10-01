import streamlit as st
from db import fetch_all, execute

def choose_robot(task):
    robots = fetch_all("""SELECT * FROM robots
                          WHERE status='Available' AND battery >= 20
                          ORDER BY battery DESC""")
    if not robots:
        return None

    # Simple scoring: battery + health + task priority compatibility.
    # Lower location distance is approximated by matching location/source.
    best = None
    best_score = -1
    for r in robots:
        distance_score = 30 if r["location"] == task["source"] else 10
        score = (r["battery"] * 0.4) + (r["health_score"] * 0.3) + distance_score + task["priority"] * 5
        if score > best_score:
            best_score = score
            best = r
    return best

def task_scheduler():
    st.header("⚙️ Smart Task Scheduler")

    tasks = fetch_all("SELECT * FROM tasks WHERE status='Pending' ORDER BY priority DESC, deadline ASC")
    if not tasks:
        st.info("No pending tasks.")
        return

    for task in tasks:
        st.write(f"*Task {task['task_id']} — {task['task_name']}* | Priority: {task['priority']}")
        if st.button(f"Assign best robot to Task {task['task_id']}", key=f"assign{task['task_id']}"):
            robot = choose_robot(task)
            if robot:
                execute("UPDATE tasks SET assigned_robot=%s,status='Assigned' WHERE task_id=%s",
                        (robot["robot_id"], task["task_id"]))
                execute("UPDATE robots SET status='Busy',current_task_id=%s WHERE robot_id=%s",
                        (task["task_id"], robot["robot_id"]))
                execute("INSERT INTO task_logs(task_id,robot_id,action) VALUES(%s,%s,%s)",
                        (task["task_id"], robot["robot_id"], "Task assigned by smart scheduler"))
                st.success(f"Assigned to {robot['name']}.")
                st.rerun()
            else:
                st.warning("No suitable available robot.")
