import streamlit as st
from db import fetch_all, execute

def task_management():
    st.header("📋 Task Management")

    with st.form("add_task"):
        name = st.text_input("Task name", "Move Package")
        source = st.text_input("Source", "A1")
        destination = st.text_input("Destination", "C3")
        priority = st.slider("Priority (1 = low, 5 = high)", 1, 5, 3)
        deadline = st.number_input("Deadline (simulation minutes)", 1, 1000, 60)
        if st.form_submit_button("Create Task"):
            execute("""INSERT INTO tasks(task_name,source,destination,priority,deadline)
                       VALUES(%s,%s,%s,%s,%s)""",
                    (name, source, destination, priority, deadline))
            st.success("Task created.")

    tasks = fetch_all("""SELECT t.*, r.name AS robot_name
                         FROM tasks t LEFT JOIN robots r
                         ON t.assigned_robot=r.robot_id
                         ORDER BY t.task_id DESC""")
    st.dataframe(tasks, use_container_width=True)
