
import streamlit as st
from db import fetch_all, execute_transaction


def synchronization():
    st.header("🔐 Resource Synchronization")

    # 1. Display resources and their current owners
    resources = fetch_all("""
        SELECT res.resource_id,
               res.resource_name,
               res.occupied_by,
               res.status,
               r.name AS robot_name
        FROM resources res
        LEFT JOIN robots r ON res.occupied_by = r.robot_id
        ORDER BY res.resource_id
    """)

    if not resources:
        st.info("No shared resources available.")
        return

    st.dataframe(resources, use_container_width=True)

    resource_map = {
        f"{r['resource_id']} - {r['resource_name']}": r
        for r in resources
    }

    selected = st.selectbox(
        "Select Resource",
        list(resource_map.keys())
    )
    resource = resource_map[selected]

    # 2. Load eligible robots
    robots = fetch_all("""
        SELECT robot_id, name, status
        FROM robots
        WHERE status IN ('Available', 'Busy')
        ORDER BY robot_id
    """)

    if not robots:
        st.info("No eligible robots available.")
        return

    robot_map = {
        f"{r['robot_id']} - {r['name']} ({r['status']})": r
        for r in robots
    }

    robot_label = st.selectbox(
        "Requesting Robot",
        list(robot_map.keys())
    )
    robot = robot_map[robot_label]

    st.write(f"Resource status: **{resource['status']}**")

    # 3. Request a resource using one database transaction
    if st.button("Request Resource"):
        robot_id = int(robot["robot_id"])
        resource_id = int(resource["resource_id"])

        def request_transaction(cur):
            # Lock the resource first. All requests for this resource
            # must acquire the same lock before checking its status.
            cur.execute("""
                SELECT status, occupied_by
                FROM resources
                WHERE resource_id = %s
                FOR UPDATE
            """, (resource_id,))

            current = cur.fetchone()

            if not current:
                return "missing"

            # Check for an existing active request.
            cur.execute("""
                SELECT request_id
                FROM resource_requests
                WHERE robot_id = %s
                  AND resource_id = %s
                  AND status IN ('Waiting', 'Granted')
                LIMIT 1
                FOR UPDATE
            """, (robot_id, resource_id))

            if cur.fetchone():
                return "duplicate"

            if current["status"] == "Free" and current["occupied_by"] is None:
                cur.execute("""
                    UPDATE resources
                    SET occupied_by = %s,
                        status = 'Occupied'
                    WHERE resource_id = %s
                      AND status = 'Free'
                      AND occupied_by IS NULL
                """, (robot_id, resource_id))

                if cur.rowcount != 1:
                    raise RuntimeError("Resource allocation failed.")

                cur.execute("""
                    INSERT INTO resource_requests
                        (robot_id, resource_id, status)
                    VALUES (%s, %s, 'Granted')
                """, (robot_id, resource_id))

                return "granted"

            # Resource is already occupied. Save the waiting request.
            cur.execute("""
                INSERT INTO resource_requests
                    (robot_id, resource_id, status)
                VALUES (%s, %s, 'Waiting')
            """, (robot_id, resource_id))

            return "waiting"

        try:
            outcome = execute_transaction(request_transaction)

            if outcome == "granted":
                st.success(
                    f"{resource['resource_name']} allocated "
                    f"to {robot['name']} (ID {robot_id})."
                )
            elif outcome == "waiting":
                st.warning(
                    "Resource is occupied. Request saved as Waiting."
                )
            elif outcome == "duplicate":
                st.info(
                    "This robot already has an active request "
                    "for this resource."
                )
            else:
                st.error("Resource not found.")

        except Exception as exc:
            st.error(f"Could not process the request: {exc}")

        st.rerun()

    # 4. Display request history
    st.subheader("Resource Requests")

    requests = fetch_all("""
        SELECT rr.request_id,
               rr.robot_id,
               r.name AS robot_name,
               rr.resource_id,
               res.resource_name,
               rr.status,
               rr.requested_at
        FROM resource_requests rr
        JOIN robots r ON rr.robot_id = r.robot_id
        JOIN resources res ON rr.resource_id = res.resource_id
        ORDER BY rr.requested_at DESC, rr.request_id DESC
    """)

    if requests:
        st.dataframe(requests, use_container_width=True)
    else:
        st.info("No resource requests recorded yet.")

    # 5. Release an occupied resource
    if resource["status"] == "Occupied":
        st.subheader("Release Resource")

        owner_id = resource.get("occupied_by")

        if owner_id is None:
            st.warning(
                "The resource is marked Occupied but has no owner ID. "
                "Check the resource record."
            )
            return

        owner_id = int(owner_id)

        st.caption(f"Currently occupied by Robot ID {owner_id}.")

        # Include the actual owner even if its status is not Available
        # or Busy, so a failed robot's resource can still be released.
        owner_record = fetch_all("""
            SELECT robot_id, name, status
            FROM robots
            WHERE robot_id = %s
        """, (owner_id,))

        if not owner_record:
            st.error("The occupying robot does not exist in the database.")
            return

        owner = owner_record[0]
        owner_label = (
            f"{owner['robot_id']} - {owner['name']} "
            f"({owner['status']})"
        )

        st.text_input(
            "Confirm the occupying robot",
            value=owner_label,
            disabled=True
        )

        if st.button("Release Resource"):
            resource_id = int(resource["resource_id"])

            def release_transaction(cur):
                # Lock the resource and verify its current owner.
                cur.execute("""
                    SELECT status, occupied_by
                    FROM resources
                    WHERE resource_id = %s
                    FOR UPDATE
                """, (resource_id,))

                current = cur.fetchone()

                if (
                    not current
                    or current["status"] != "Occupied"
                    or current["occupied_by"] is None
                    or int(current["occupied_by"]) != owner_id
                ):
                    return "changed"

                # Mark the previous owner's granted request released.
                cur.execute("""
                    UPDATE resource_requests
                    SET status = 'Released'
                    WHERE resource_id = %s
                      AND robot_id = %s
                      AND status = 'Granted'
                """, (resource_id, owner_id))

                # Find the oldest waiting request from an eligible robot.
                cur.execute("""
                    SELECT rr.request_id, rr.robot_id
                    FROM resource_requests rr
                    JOIN robots r ON r.robot_id = rr.robot_id
                    WHERE rr.resource_id = %s
                      AND rr.status = 'Waiting'
                      AND r.status IN ('Available', 'Busy')
                    ORDER BY rr.requested_at, rr.request_id
                    LIMIT 1
                    FOR UPDATE
                """, (resource_id,))

                waiting = cur.fetchone()

                if waiting:
                    new_owner_id = int(waiting["robot_id"])

                    cur.execute("""
                        UPDATE resources
                        SET occupied_by = %s,
                            status = 'Occupied'
                        WHERE resource_id = %s
                    """, (new_owner_id, resource_id))

                    cur.execute("""
                        UPDATE resource_requests
                        SET status = 'Granted'
                        WHERE request_id = %s
                          AND status = 'Waiting'
                    """, (waiting["request_id"],))

                    if cur.rowcount != 1:
                        raise RuntimeError(
                            "Could not update the waiting request."
                        )

                    return "reassigned"

                # No eligible waiting robot: make the resource free.
                cur.execute("""
                    UPDATE resources
                    SET occupied_by = NULL,
                        status = 'Free'
                    WHERE resource_id = %s
                """, (resource_id,))

                return "released"

            try:
                outcome = execute_transaction(release_transaction)

                if outcome == "reassigned":
                    st.success(
                        "Resource transferred to the oldest eligible "
                        "waiting robot."
                    )
                elif outcome == "released":
                    st.success("Resource released and marked Free.")
                else:
                    st.warning(
                        "Resource ownership has changed. "
                        "Refresh and check the current resource status."
                    )

            except Exception as exc:
                st.error(f"Could not release the resource: {exc}")

            st.rerun()
