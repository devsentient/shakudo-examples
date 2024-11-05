import requests


class Tools:
  def __init__(self):
    self.citation = True
    self.url = "" # in-cluster URL mentioned earlier

  def answer(self, rag_query: str, document:str) -> str:
    """
    Query the graph retrieval augmented generation (RAG) with the user question
    :param rag_query: the query to answer using the Graph RAG
    :param rag_query: string
    :param document: the document that the user want to ask about
    :param document: string
    
    """
    params = {"document": document, "query": rag_query}
    response = requests.get(self.url, params=params)

    if response.status_code == 200:
      # Parse the JSON response and pretty print it
      result = response.json()['response']
      return result
    else:
      return f"Error: {response.status_code} - {response.text}"