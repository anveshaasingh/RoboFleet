"""RoboFleet live educational simulation: robot movement, task execution and telemetry.

All motion/telemetry here is simulated. No physical robot or external robot API is connected.
"""
import json
import time
from collections import deque

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from db import fetch_all, execute

# Warehouse grid. Rows A-D, columns 1-4; each adjacent cell is a traversable aisle.
ROWS = ["A", "B", "C", "D"]
COLS = [1, 2, 3, 4]
LOCATIONS = [f"{r}{c}" for r in ROWS for c in COLS]
COLORS = ["#22d3ee", "#a3e635", "#f59e0b", "#c084fc", "#fb7185", "#60a5fa"]


def _xy(location):
    location = (location or "A1").upper().strip()
    if len(location) >= 2 and location[0] in ROWS:
        try:
            col = int(location[1:])
            if col in COLS:
                return col, len(ROWS) - ROWS.index(location[0])
        except ValueError:
            pass
    return 1, 4


def _nearest_location(location):
    loc = (location or "A1").upper().strip()
    return loc if loc in LOCATIONS else "A1"


def _route(source, destination):
    """Return a simple aisle-safe Manhattan route from source to destination."""
    source, destination = _nearest_location(source), _nearest_location(destination)
    sr, sc = ROWS.index(source[0]), int(source[1:])
    dr, dc = ROWS.index(destination[0]), int(destination[1:])
    result = [source]
    while sc != dc:
        sc += 1 if dc > sc else -1
        result.append(f"{ROWS[sr]}{sc}")
    while sr != dr:
        sr += 1 if dr > sr else -1
        result.append(f"{ROWS[sr]}{sc}")
    return result


def ensure_simulation_tables():
    execute("""
        CREATE TABLE IF NOT EXISTS robot_motion_state (
            robot_id INT PRIMARY KEY,
            task_id INT NULL,
            route_json TEXT NOT NULL,
            step_index INT NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_motion_robot FOREIGN KEY (robot_id)
                REFERENCES robots(robot_id) ON DELETE CASCADE
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS robot_telemetry_history (
            telemetry_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            robot_id INT NOT NULL,
            battery INT NOT NULL,
            status VARCHAR(20) NOT NULL,
            health_score INT NOT NULL,
            location VARCHAR(50),
            source VARCHAR(40) NOT NULL DEFAULT 'simulated',
            captured_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_robot_captured (robot_id, captured_at),
            CONSTRAINT fk_telemetry_robot FOREIGN KEY (robot_id)
                REFERENCES robots(robot_id) ON DELETE CASCADE
        )
    """)


def _ensure_task_columns():
    # Support older versions of the project database without requiring a reset.
    cols = {r["COLUMN_NAME"] for r in fetch_all("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='tasks'
    """)}
    if "assigned_robot" not in cols:
        execute("ALTER TABLE tasks ADD COLUMN assigned_robot INT NULL")
    if "source" not in cols:
        execute("ALTER TABLE tasks ADD COLUMN source VARCHAR(50) NULL")
    if "destination" not in cols:
        execute("ALTER TABLE tasks ADD COLUMN destination VARCHAR(50) NULL")
    if "priority" not in cols:
        execute("ALTER TABLE tasks ADD COLUMN priority INT DEFAULT 3")


def _assign_pending_tasks():
    """Assign highest-priority pending tasks to available, sufficiently charged robots."""
    robots = fetch_all("""
        SELECT robot_id, location, battery FROM robots
        WHERE status='Available' AND COALESCE(battery,0) > 15
        ORDER BY battery DESC, robot_id
    """)
    for robot in robots:
        pending = fetch_all("""
            SELECT task_id, source, destination, task_name FROM tasks
            WHERE status='Pending'
            ORDER BY priority DESC, task_id ASC LIMIT 1
        """)
        if not pending:
            break
        task = pending[0]
        current_location = _nearest_location(robot.get("location") or "A1")
        source = _nearest_location(task.get("source") or current_location)
        destination = _nearest_location(task.get("destination") or "D4")
        # Travel from current location to pickup/source, then onward to destination.
        to_source = _route(current_location, source)
        to_destination = _route(source, destination)
        route = to_source + to_destination[1:]
        execute("UPDATE robots SET status='Busy', current_task_id=%s WHERE robot_id=%s",
                (task["task_id"], robot["robot_id"]))
        execute("UPDATE tasks SET status='In Progress', assigned_robot=%s WHERE task_id=%s",
                (robot["robot_id"], task["task_id"]))
        execute("""INSERT INTO robot_motion_state(robot_id,task_id,route_json,step_index)
                    VALUES(%s,%s,%s,0)
                    ON DUPLICATE KEY UPDATE task_id=VALUES(task_id),
                    route_json=VALUES(route_json), step_index=0""",
                (robot["robot_id"], task["task_id"], json.dumps(route)))
        execute("INSERT INTO task_logs(task_id,robot_id,action) VALUES(%s,%s,%s)",
                (task["task_id"], robot["robot_id"], "Automatically assigned by live simulator"))


def _advance_simulation():
    """Move every busy robot by one grid cell per refresh and complete tasks at destination."""
    busy = fetch_all("""
        SELECT r.robot_id,r.name,r.location,r.battery,r.health_score,r.current_task_id,
               m.route_json,m.step_index,m.task_id AS motion_task_id
        FROM robots r LEFT JOIN robot_motion_state m ON m.robot_id=r.robot_id
        WHERE r.status='Busy' AND r.current_task_id IS NOT NULL
        ORDER BY r.robot_id
    """)
    for robot in busy:
        task_id = robot.get("current_task_id")
        state_task = robot.get("motion_task_id")
        route_json = robot.get("route_json")
        if not route_json or state_task != task_id:
            task_rows = fetch_all("SELECT source,destination FROM tasks WHERE task_id=%s", (task_id,))
            if not task_rows:
                continue
            route = _route(robot.get("location"), task_rows[0].get("destination"))
            execute("""INSERT INTO robot_motion_state(robot_id,task_id,route_json,step_index)
                        VALUES(%s,%s,%s,0) ON DUPLICATE KEY UPDATE task_id=VALUES(task_id),
                        route_json=VALUES(route_json),step_index=0""",
                    (robot["robot_id"], task_id, json.dumps(route)))
            idx = 0
        else:
            route = json.loads(route_json)
            idx = int(robot.get("step_index") or 0)
        if not route:
            continue
        next_idx = min(idx + 1, len(route) - 1)
        new_location = route[next_idx]
        battery = max(5, int(robot.get("battery") or 0) - 1)
        execute("UPDATE robots SET location=%s,battery=%s WHERE robot_id=%s",
                (new_location, battery, robot["robot_id"]))
        execute("UPDATE robot_motion_state SET step_index=%s WHERE robot_id=%s", (next_idx, robot["robot_id"]))

        if next_idx >= len(route) - 1:
            execute("UPDATE tasks SET status='Completed' WHERE task_id=%s", (task_id,))
            execute("UPDATE robots SET status='Available',current_task_id=NULL WHERE robot_id=%s", (robot["robot_id"],))
            execute("DELETE FROM robot_motion_state WHERE robot_id=%s", (robot["robot_id"],))
            execute("INSERT INTO task_logs(task_id,robot_id,action) VALUES(%s,%s,%s)",
                    (task_id, robot["robot_id"], "Task automatically completed at destination"))
        execute("""INSERT INTO robot_telemetry_history
                    (robot_id,battery,status,health_score,location,source)
                    SELECT robot_id,battery,status,health_score,location,'simulated'
                    FROM robots WHERE robot_id=%s""", (robot["robot_id"],))

    # Automatically start the next queued task after each movement tick.
    _assign_pending_tasks()


def _draw_warehouse_map(robots):
    fig = go.Figure()
    # Grid aisle lines and station labels.
    for x in COLS:
        fig.add_trace(go.Scatter(x=[x, x], y=[0.5, 4.5], mode="lines",
                                 line=dict(color="#cbd5e1", width=2), hoverinfo="skip", showlegend=False))
    for y in range(1, 5):
        fig.add_trace(go.Scatter(x=[0.5, 4.5], y=[y, y], mode="lines",
                                 line=dict(color="#cbd5e1", width=2), hoverinfo="skip", showlegend=False))
    # Warehouse shelves represented as subtle blocks between aisle intersections.
    for x, y in [(1.5, 1.5), (2.5, 1.5), (3.5, 1.5), (1.5, 2.5), (2.5, 2.5), (3.5, 2.5),
                 (1.5, 3.5), (2.5, 3.5), (3.5, 3.5)]:
        fig.add_shape(type="rect", x0=x-0.28, x1=x+0.28, y0=y-0.25, y1=y+0.25,
                      line=dict(color="#94a3b8", width=1), fillcolor="#e2e8f0", layer="below")
    for i, r in enumerate(robots):
        color = COLORS[i % len(COLORS)]
        pos = _xy(r.get("location"))
        state = fetch_all("SELECT route_json,step_index,task_id FROM robot_motion_state WHERE robot_id=%s", (r["robot_id"],))
        if state:
            route = json.loads(state[0]["route_json"] or "[]")
            # Show completed part of route and planned remainder.
            if route:
                pts = [_xy(p) for p in route]
                fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines",
                    line=dict(color=color, width=4, dash="dot"), name=f"{r['name']} route",
                    hovertemplate=f"{r['name']} planned path<extra></extra>"))
                dest = route[-1]
                fig.add_trace(go.Scatter(x=[dest[0]], y=[dest[1]], mode="markers+text",
                    marker=dict(symbol="star", size=15, color=color), text=["DEST"], textposition="top center",
                    name=f"{r['name']} destination", hovertemplate=f"Destination: {route[-1]}<extra></extra>"))
        fig.add_trace(go.Scatter(x=[pos[0]], y=[pos[1]], mode="markers+text",
            marker=dict(symbol="circle", size=22, color=color, line=dict(color="#0f172a", width=2)),
            text=[f"🤖 {r['name']}"], textposition="top center", name=r["name"],
            customdata=[[r.get("battery", 0), r.get("status", "Unknown"), r.get("current_task_id")]],
            hovertemplate="%{text}<br>Battery: %{customdata[0]}%<br>Status: %{customdata[1]}<br>Task: %{customdata[2]}<extra></extra>"))
    # Label all grid cells.
    for loc in LOCATIONS:
        x, y = _xy(loc)
        fig.add_annotation(x=x, y=y-0.22, text=loc, showarrow=False,
                           font=dict(size=10, color="#334155"), bgcolor="rgba(255,255,255,0.8)")
    fig.update_layout(height=520, margin=dict(l=10,r=10,t=30,b=10),
        title="Warehouse live map · robots, routes & destinations", plot_bgcolor="#f8fafc",
        paper_bgcolor="white", legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(range=[0.4,4.6], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[0.4,4.6], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1))
    st.plotly_chart(fig, use_container_width=True, key="robofleet_live_warehouse_map")


def render_live_telemetry():
    """Run one simulation tick per refresh and render movement, routes, tasks and telemetry."""
    ensure_simulation_tables()
    _ensure_task_columns()
    now = time.time()
    last_tick = st.session_state.get("fleet_last_tick", 0)
    # Dashboard autorefresh is every 2.5 seconds. Guard against duplicate ticks on reruns.
    if now - last_tick >= 2.2:
        _assign_pending_tasks()
        _advance_simulation()
        st.session_state["fleet_last_tick"] = now

    robots = fetch_all("""SELECT robot_id,name,location,battery,status,health_score,current_task_id
                         FROM robots ORDER BY robot_id""")
    tasks = fetch_all("""SELECT t.task_id,t.task_name,t.source,t.destination,t.priority,t.status,
                              t.assigned_robot,r.name AS robot_name
                       FROM tasks t LEFT JOIN robots r ON r.robot_id=t.assigned_robot
                       ORDER BY CASE t.status WHEN 'In Progress' THEN 0 WHEN 'Pending' THEN 1 ELSE 2 END,
                                t.priority DESC,t.task_id""")
    if not robots:
        st.info("No robots found. Run database.sql to initialize the fleet.")
        return

    st.subheader("🗺️ Live Warehouse Movement")
    st.caption("Robots move one aisle cell per refresh. Tasks are auto-assigned by priority and completed at their destination. All movement is simulated, not physical robot telemetry.")
    active = sum(r["status"] == "Busy" for r in robots)
    pending = sum(t["status"] == "Pending" for t in tasks)
    completed = sum(t["status"] == "Completed" for t in tasks)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🤖 Robots", len(robots))
    c2.metric("🚚 Moving", active)
    c3.metric("📦 Tasks pending", pending)
    c4.metric("✅ Completed tasks", completed)

    _draw_warehouse_map(robots)

    st.markdown("#### Robot telemetry")
    robot_rows = []
    for r in robots:
        task_name = "—"
        dest = "—"
        progress = "Idle"
        motion = fetch_all("SELECT route_json,step_index FROM robot_motion_state WHERE robot_id=%s", (r["robot_id"],))
        if r.get("current_task_id"):
            tr = fetch_all("SELECT task_name,destination FROM tasks WHERE task_id=%s", (r["current_task_id"],))
            if tr:
                task_name, dest = tr[0]["task_name"], tr[0]["destination"]
            if motion:
                route = json.loads(motion[0]["route_json"] or "[]")
                idx = int(motion[0]["step_index"] or 0)
                progress = f"{min(100, int(idx/max(1,len(route)-1)*100))}%"
        robot_rows.append({"Robot":r["name"],"Location":r["location"],"Destination":dest,
                           "Battery":f"{r['battery']}%","Status":r["status"],"Current task":task_name,"Progress":progress})
    st.dataframe(pd.DataFrame(robot_rows), use_container_width=True, hide_index=True)

    st.markdown("#### Task execution queue")
    if tasks:
        st.dataframe(pd.DataFrame([{"Task ID":t["task_id"],"Task":t["task_name"],"From":t["source"],
            "Destination":t["destination"],"Priority":t["priority"],"Assigned robot":t["robot_name"] or "—",
            "Status":t["status"]} for t in tasks]), use_container_width=True, hide_index=True)
    else:
        st.info("No tasks in the queue yet. Add tasks from the Task Management module.")

    history = fetch_all("""SELECT captured_at,robot_id,battery,status,location FROM robot_telemetry_history
                          ORDER BY captured_at DESC,telemetry_id DESC LIMIT 120""")
    if history:
        st.markdown("#### Recent battery telemetry")
        df = pd.DataFrame(history)
        df["captured_at"] = pd.to_datetime(df["captured_at"])
        df["battery"] = pd.to_numeric(df["battery"])
        pivot = df.pivot_table(index="captured_at", columns="robot_id", values="battery", aggfunc="last").sort_index()
        st.line_chart(pivot)
