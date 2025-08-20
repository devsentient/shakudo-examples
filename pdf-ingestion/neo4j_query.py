create_query = """
    CREATE (f:File {file_name: $file_name, text: $text})
    SET f.text = $text
    RETURN f

    """

chunk_query = """
    MATCH (f:File {file_name: $file_name})
    UNWIND $children AS chunk
    CREATE (c:Chunk {id: chunk.id})
    SET c.text = chunk.text,
        c.chunk_n = chunk.chunk_n,
        c.is_last = chunk.is_last,
        c.file_name = $file_name
    MERGE (f)-[:HAS_CHUNK]->(c)
    WITH c, chunk
    CALL db.create.setNodeVectorProperty(c, 'embedding', chunk.embedding)


    """


NEO4J_QUERY_GENERAL = """
    MATCH (f:File)-[:HAS_CHUNK]->(c:Chunk)
    WITH c, vector.similarity.cosine(c.embedding, $prompt_embedding) AS score
    ORDER BY score DESC
    LIMIT $inner_K 
    WITH c, score
    MATCH (f:File)-[:HAS_CHUNK]->(c)
    WITH f, MAX(score) AS max_score ,c
    RETURN c.text AS text, c.file_name AS file_name, max_score AS score, c.chunk_n AS chunk_n, c.is_last AS is_last
    ORDER BY score DESC
"""



NEO4J_QUERY_SIBLING = """
    MATCH (c:Chunk {file_name: $file_name})  
    WHERE c.chunk_n IN $ns
    RETURN c.text AS text, c.chunk_n AS chunk_n
    ORDER BY chunk_n DESC
"""
