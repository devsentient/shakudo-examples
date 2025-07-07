# frontend/main.py

import streamlit as st

from neo4j import GraphDatabase
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j.hyperplane-neo4j.svc.cluster.local:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Shakudo312!")

# --- CONNECTOR ---
@st.cache_resource
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# --- QUERY FUNCTION ---
def fetch_first_three_nodes():
    query = "MATCH (n) RETURN n LIMIT 3"
    driver = get_driver()
    with driver.session() as session:
        results = session.run(query)
        return [record["n"] for record in results]

# --- STREAMLIT UI ---
st.title("Neo4j First 3 Nodes Viewer")

try:
    nodes = fetch_first_three_nodes()
    if nodes:
        for i, node in enumerate(nodes, 1):
            st.subheader(f"Node {i}")
            st.json(dict(node))
    else:
        st.info("No nodes found in the graph.")
except Exception as e:
    st.error(f"Connection/query failed: {e}")

st.set_page_config(
            page_title="Shakudo Streamlit Example",
            page_icon=":shark:"
        )


st.title("This is an example Title")
st.subheader("multiple columns")
col1, col2, col3 = st.columns([2, 4, 5])
with col1:
    st.button("Click me", on_click=lambda: st.balloons())
with col2:
    st.text("this is a text place holder")
with col3:
    st.table([[1, 2, 3], [4, 5, 6]])
    
col4, col5 = st.columns([5, 5])

with col4:
    st.subheader("json content")
    st.json("""{
        "key" : "value",
        "key2" : 123,
        "somelist" : [1, 2, "3"]
    }""")
with col5:
    st.subheader('charts')
    st.bar_chart([1, 4, 5, 3, 2, 6])

st.subheader("Progress bar")
import time
progressbar =  st.empty()
n = 0

with st.expander("expandable"):
    st.text("""This is some text.
            """* 30)

with st.sidebar:
    st.slider("slider", 0, 100, 50)
    st.select_slider("select slider", list(range(10)))
    st.selectbox('select box', ['apple', 'banana', 'pear'])
    st.checkbox('check box 1')
    st.checkbox('check box 2')
    st.checkbox('check box 3')
    st.checkbox('check box 4')
    st.time_input("time")
    st.date_input("Date")
    st.text_input("text")

while 1:
    n += 1
    with progressbar:
        st.progress(n)
    time.sleep(1)
    if n == 100:
        n = 0
