# 🧠 Neo4j Streamlit Microservice

This microservice provides a simple Streamlit interface to query and visualize data from a Neo4j graph database. It is designed for rapid prototyping and interactive exploration of graph data.

---

## 🚀 Features

- Interactive frontend built with Streamlit
- Connects to Neo4j using the official Python driver
- Visualizes Cypher query results in an intuitive, user-friendly graph interface
- Fully configurable via environment variables (URI, user, password, etc.)
- Includes a setup and usage screen recording

---

## 🛠️ Setup on Shakudo

1. **Add the repository** to your Shakudo workspace.


2. **Create a new Microservice** using either the landing page or the service dashboard.

3. **Set Service Details**:

   - **Name** your service:  
     Example: `neo4j-streamlit`

   - **Subdomain** (optional but recommended):  
     Set it to match the name, e.g. `neo4j-streamlit`, which will expose the service at:  
     `neo4j-streamlit.test-dev.canopyhub.io`

   - **Port**:  
     Use the default port: `8787`

   - **Environment Config**:  
     Select `Basic` (or another appropriate config that includes Python)

   - **Pipeline**:  
     Choose the **Shell** option  
     Provide the relative path to your shell script, for example:  
     `neo4j-microservice/run.sh`  
     This script should exist in your Git repository and be executable.

   - **Git Repository**:
     - Select repository: `shakudo-examples`
     - Branch: `feature/neo4j-streamlit`


---

## Parameters

Add the following **Parameters** (not Secrets unless sensitive):

| Parameter Name   | Description                   | Example Value                                                  |
|------------------|-------------------------------|----------------------------------------------------------------|
| `NEO4J_URI`       | Bolt connection URI for Neo4j | `bolt://neo4j.hyperplane-neo4j.svc.cluster.local:7687`         |
| `NEO4J_USER`      | Neo4j username                | `neo4j`                                                        |
| `NEO4J_PASSWORD`  | Neo4j password                | `your_secure_password` (use a Secret for real deployments)     |

These will be available inside the service as environment variables:  
e.g., `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`


---

## 🔍 Health Check

Once deployed, confirm the microservice is healthy using the Kubernetes dashboard or:

```bash
kubectl get pods -n <your-namespace>
```

---
