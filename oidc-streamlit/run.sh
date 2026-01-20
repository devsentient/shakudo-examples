cd oidc-streamlit

apt-get update -y && apt-get upgrade -y

pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8787
