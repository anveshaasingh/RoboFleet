import mysql.connector
import streamlit as st


def get_connection():
    return mysql.connector.connect(
        host=st.session_state.get("db_host", "localhost"),
        user=st.session_state.get("db_user", "root"),
        password=st.session_state.get("db_password", ""),
        database="robofleet"
    )


def fetch_all(query, params=None):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(query, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def execute(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    conn.close()
    return last_id
