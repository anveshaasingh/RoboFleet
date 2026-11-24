import streamlit as st
from streamlit_autorefresh import st_autorefresh
from live_telemetry import render_live_telemetry
from db import fetch_all

# Robot & Task modules
from robot_management import robot_management
from task_management import task_management
from battery_management import battery_management
from robot_health import robot_health
from robot_simulation import robot_simulation

# OS modules
from task_scheduler import task_scheduler
from preemption import preemption
from resource_management import resource_management
from synchronization import synchronization
from deadlock_detection import deadlock_detection

# Database & Recovery modules
from failure_recovery import failure_recovery
from smart_assignment import smart_assignment
from activity_logging import activity_logging


st.set_page_config(
    page_title="RoboFleet",
    page_icon="🤖",
    layout="wide"
)


st.title("🤖 RoboFleet")
st.caption(
    "Phase-II: Simulated OS & DBMS-Based Fleet Management Platform"
)


# =========================
# SIDEBAR
# =========================

with st.sidebar:

    st.header("MySQL Connection")

    st.session_state["db_host"] = st.text_input(
        "Host",
        "localhost"
    )

    st.session_state["db_user"] = st.text_input(
        "User",
        "root"
    )

    st.session_state["db_password"] = st.text_input(
        "Password",
        type="password"
    )


    st.divider()

    st.header("Modules")

    menu = st.radio(
        "Select Module",
        [
            "Dashboard",

            # Robot & Task Management
            "Robot Management",
            "Task Management",
            "Battery Management",
            "Robot Health Metric",
            "Robot Simulation",

            # OS
            "Task Scheduler",
            "Preemption",
            "Resource Management",
            "Synchronization",
            "Deadlock Detection",

            # Recovery & DBMS
            "Failure Recovery",
            "Smart Task Assignment",
            "Activity Log"
        ]
    )


# =========================
# MAIN APPLICATION
# =========================

try:

    # -------------------------
    # DASHBOARD
    # -------------------------

    if menu == "Dashboard":

        # Refresh frequently so the simulated robots visibly move and tasks advance automatically.
        st_autorefresh(interval=2_500, key="robofleet_live_refresh")
        render_live_telemetry()
        st.divider()

        robots = fetch_all(
            "SELECT * FROM robots"
        )

        tasks = fetch_all(
            "SELECT * FROM tasks"
        )

        resources = fetch_all(
            "SELECT * FROM resources"
        )


        # Dashboard metrics

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "🤖 Total Robots",
            len(robots)
        )

        c2.metric(
            "🟢 Available",
            sum(
                r["status"] == "Available"
                for r in robots
            )
        )

        c3.metric(
            "📋 Pending Tasks",
            sum(
                t["status"] == "Pending"
                for t in tasks
            )
        )

        c4.metric(
            "🔴 Failed Robots",
            sum(
                r["status"] == "Failed"
                for r in robots
            )
        )


        st.divider()


        # Robot status

        st.subheader("🤖 Robot Status")

        if robots:
            st.dataframe(
                robots,
                use_container_width=True
            )
        else:
            st.info("No robots found.")


        # Task status

        st.subheader("📋 Task Status")

        if tasks:
            st.dataframe(
                tasks,
                use_container_width=True
            )
        else:
            st.info("No tasks found.")


        # Resource status

        st.subheader("🔧 Resource Status")

        if resources:
            st.dataframe(
                resources,
                use_container_width=True
            )
        else:
            st.info("No resources found.")


    # -------------------------
    # ROBOT MANAGEMENT
    # -------------------------

    elif menu == "Robot Management":

        robot_management()


    # -------------------------
    # TASK MANAGEMENT
    # -------------------------

    elif menu == "Task Management":

        task_management()


    # -------------------------
    # BATTERY MANAGEMENT
    # -------------------------

    elif menu == "Battery Management":

        battery_management()


    # -------------------------
    # ROBOT HEALTH
    # -------------------------

    elif menu == "Robot Health Metric":

        robot_health()


    # -------------------------
    # ROBOT SIMULATION
    # -------------------------

    elif menu == "Robot Simulation":

        robot_simulation()


    # =========================
    # OS MODULES
    # =========================

    elif menu == "Task Scheduler":

        task_scheduler()


    elif menu == "Preemption":

        preemption()


    elif menu == "Resource Management":

        resource_management()


    elif menu == "Synchronization":

        synchronization()


    elif menu == "Deadlock Detection":

        deadlock_detection()


    # =========================
    # RECOVERY / DBMS
    # =========================

    elif menu == "Failure Recovery":

        failure_recovery()


    elif menu == "Smart Task Assignment":

        smart_assignment()


    elif menu == "Activity Log":

        activity_logging()


# =========================
# ERROR HANDLING
# =========================

except Exception as e:

    st.error(
        "Could not connect to MySQL "
        "or run the selected module."
    )

    st.code(str(e))

    st.info(
        "Check that MySQL is running, "
        "database 'robofleet' exists, "
        "and the username/password are correct."
    )
