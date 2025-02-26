# Shakudo POC Graph RAG Financial 10K (INTERNAL DOCS)

# Preparation
### Stack components
1. LLM endpoint (Any of):
  a. Ollama (GPU) -> With Model <>.
  b. OpenAI API key.
2. Ollama (CPU) -> With Model <>.
3. Neo4J: As GraphRag database.
4. OpenWebUI: As Frontend of the Chatbot.
5. Minio: As objects storage.

##### Commands:
```sh
helm pull oci://us-docker.pkg.dev/shakudo-417723/charts/open-webui \
          oci://us-docker.pkg.dev/shakudo-417723/charts/ollama \
          oci://us-docker.pkg.dev/shakudo-417723/charts/neo4j \
          oci://us-docker.pkg.dev/shakudo-417723/charts/minio \
          --untar
```
This readme is based on this versions:
```
Pulled: us-docker.pkg.dev/shakudo-417723/charts/open-webui:1.0.7
Digest: sha256:f29946d61842697f2e6fe6b4872ddb8603edb8893215ad2c847cf66a29b9cf9a
Pulled: us-docker.pkg.dev/shakudo-417723/charts/ollama:1.0.14
Digest: sha256:b720ae9863c324d30d0f4f8c17dcf80416329e3d90ef75f798c2304284fa34e1
Pulled: us-docker.pkg.dev/shakudo-417723/charts/neo4j:0.0.3
Digest: sha256:e330dee46e6fb846aeb7b9306b90b084340066634fef73cc65de83e594102f66
Pulled: us-docker.pkg.dev/shakudo-417723/charts/minio:1.0.4
Digest: sha256:216a8e4afc39345feeea03194bd7030eb41fe48b15e121b5ce4477e9ac08e8db
```

### Create Shakudo secret
1. Create secret named:
poc-minio-key -> contains access key and access secret
<image src='./readme_imgs/neo4j_node.png'/>

2. Create secret named:
neo4j-access-secret -> contains NEO4J connection string.
<image src='./readme_imgs/neo4j_node.png'/>

### Copy the PDF extracted MarkDown file into Minio.
1. Copy the files into `shakudo-poc/rag-chat-financial10k/md/*`
<image src='./readme_imgs/neo4j_node.png'/>

## Step 1 Load the extracted MD into Neo4J
This step will extract the md file into blocks, create node in neo4j for GraphRag to use.

## Step 2 Show the data node and 
<image src='./readme_imgs/neo4j_node.png'/>
