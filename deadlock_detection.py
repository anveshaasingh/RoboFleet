import streamlit as st
from db import fetch_all, execute_transaction


def get_waiting_relationships(cur=None):
    query = """
        SELECT
            req.request_id,
            waiting_robot.robot_id AS waiting_robot_id,
            waiting_robot.name AS waiting_robot_name,
            holder.robot_id AS holder_robot_id,
            holder.name AS holder_robot_name,
            res.resource_id,
            res.resource_name
        FROM resource_requests req
        JOIN resources res ON req.resource_id = res.resource_id
        JOIN robots waiting_robot ON req.robot_id = waiting_robot.robot_id
        JOIN robots holder ON res.occupied_by = holder.robot_id
        WHERE req.status = 'Waiting'
          AND res.status = 'Occupied'
          AND res.occupied_by IS NOT NULL
          AND req.robot_id <> res.occupied_by
    """
    if cur is not None:
        cur.execute(query)
        return cur.fetchall()
    return fetch_all(query)


def find_cycle_edges(graph):
    visited = set()
    path_nodes = []
    path_positions = {}
    path_edges = []

    def dfs(robot):
        visited.add(robot)
        path_positions[robot] = len(path_nodes)
        path_nodes.append(robot)

        for next_robot, edge in graph.get(robot, []):
            if next_robot in path_positions:
                return path_edges[path_positions[next_robot]:] + [edge]

            if next_robot not in visited:
                path_edges.append(edge)
                cycle = dfs(next_robot)
                if cycle:
                    return cycle
                path_edges.pop()

        path_nodes.pop()
        path_positions.pop(robot)
        return None

    for robot in graph:
        if robot not in visited:
            cycle = dfs(robot)
            if cycle:
                return cycle

    return None


def build_graph(rows):
    graph = {}

    for row in rows:
        waiting_id = row["waiting_robot_id"]
        holder_id = row["holder_robot_id"]

        graph.setdefault(waiting_id, [])
        graph.setdefault(holder_id, [])
        graph[waiting_id].append((holder_id, row))

    return graph


def live_database_detection():
    st.subheader("1. Live Database Detection")
    st.write(
        "Reads waiting requests and current resource ownership from MySQL."
    )

    if st.button("Check Database for Deadlock"):
        rows = get_waiting_relationships()

        if not rows:
            st.info("No waiting-for relationships found.")
            return

        graph = build_graph(rows)

        st.write("Wait-for Relationships")
        st.dataframe(rows, use_container_width=True)

        graph_display = {
            f"Robot ID {robot}": [
                f"Robot ID {other}" for other, edge in edges
            ]
            for robot, edges in graph.items()
        }

        st.write("Wait-for Graph")
        st.json(graph_display)

        cycle = find_cycle_edges(graph)

        if cycle:
            st.error(
                "DEADLOCK DETECTED: A cycle exists in the database records."
            )
        else:
            st.success("No cycle found in the current database records.")


def recover_deadlock():
    def recovery_transaction(cur):
        rows = get_waiting_relationships(cur)
        graph = build_graph(rows)
        cycle = find_cycle_edges(graph)

        if not cycle:
            return None

        # Cancel one waiting request that belongs to the detected cycle.
        request = cycle[-1]

        cur.execute(
            """
            UPDATE resource_requests
            SET status = 'Cancelled'
            WHERE request_id = %s AND status = 'Waiting'
            """,
            (request["request_id"],)
        )

        if cur.rowcount != 1:
            raise RuntimeError(
                "The waiting request changed. Run detection again."
            )

        return request

    try:
        recovered = execute_transaction(recovery_transaction)

        if recovered:
            st.success(
                f"Recovery completed: waiting request "
                f"{recovered['request_id']} for "
                f"{recovered['waiting_robot_name']} was cancelled. "
                "Run detection again to verify the cycle is gone."
            )
        else:
            st.info(
                "No deadlock cycle was found. No request was cancelled."
            )

    except Exception as error:
        st.error(f"Recovery failed: {error}")


def simulated_deadlock_demo():
    st.subheader("3. Controlled Deadlock Demonstration")
    st.write("This example is simulated and does not change MySQL records.")

    if st.button("Run Simulated Deadlock Demo"):
        demo_graph = {
            2: [(3, {})],
            3: [(2, {})]
        }

        st.json({
            "Robot-2": ["Robot-3"],
            "Robot-3": ["Robot-2"]
        })

        if find_cycle_edges(demo_graph):
            st.error("DEADLOCK DETECTED: A circular wait exists.")


def deadlock_detection():
    st.header("🚨 Deadlock Detection")
    live_database_detection()

    st.divider()
    st.subheader("2. Deadlock Recovery")
    st.write(
        "Cancels one waiting request in a detected cycle. "
        "The database transaction is rolled back if an error occurs."
    )

    if st.button("Recover Deadlock"):
        recover_deadlock()

    st.divider()
    simulated_deadlock_demo()
