# 🧠 Neo4j Streamlit Microservice

This microservice provides a simple Streamlit interface to query and visualize data from a Neo4j graph database. It is designed for rapid prototyping and interactive exploration of graph data.

---

## 🚀 Features

- Connects to a Neo4j instance using the official Python driver
- Executes Cypher queries and displays graph nodes
- Interactive Streamlit UI for real-time querying and feedback
- Easily configurable via environment variables
- 🎥 **Screen recording included** for setup and usage guidance

---

## 🛠️ Setup on Shakudo

### 1. Add the Git repo to the Shakudo platform

Clone or import this repository into your Shakudo workspace.

---

### 2. Create the Microservice

While creating the microservice in Shakudo:
- Set the working directory to where your `main.py` is located (e.g., `/frontend`)
- Choose a Python environment with `streamlit` and `neo4j` installed (or include a `requirements.txt`)

**Add the following environment variables in the _Parameters_ tab:**

| Variable         | Description                     | Example                                                      |
|------------------|---------------------------------|--------------------------------------------------------------|
| `NEO4J_URI`       | Bolt connection URI for Neo4j   | `bolt://neo4j.hyperplane-neo4j.svc.cluster.local:7687`       |
| `NEO4J_USER`      | Neo4j username                  | `neo4j`                                                      |
| `NEO4J_PASSWORD`  | Neo4j password                  | `your_secure_password`                                       |

---

### 3. Confirm Microservice Health

After deployment, go to the **Kubernetes dashboard** or use `kubectl` to verify that all pods are running:

```bash
kubectl get pods -n <your-namespace>