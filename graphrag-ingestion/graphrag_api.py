#!/usr/bin/env python3

"""
GraphRAG API Service
Exposes REST endpoints for querying the Neo4j knowledge graph
"""

from flask import Flask, request, jsonify
import ollama
from neo4j import GraphDatabase
from typing import List, Dict
import logging
from graphrag_ingestion import GraphRAGIngestor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class GraphRAGAPI:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://neo4j.hyperplane-neo4j:7687", 
            auth=("neo4j", "Shakudo312!")
        )
        self.embedding_model = "nomic-embed-text:latest"
        self.chat_model = "granite-3.3-8b-instruct-Q6_K_L:latest"
        self.ollama_host = "http://ollama-1.hyperplane-ollama-gpu-1.svc.cluster.local:11434"
        
        logger.info("GraphRAG API initialized")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama"""
        try:
            client = ollama.Client(host=self.ollama_host)
            response = client.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return []
    
    def search_similar_chunks(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar chunks using vector similarity"""
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
        
        with self.driver.session() as session:
            try:
                result = session.run("""
                    CALL db.index.vector.queryNodes('chunk_embedding', $limit, $query_embedding)
                    YIELD node, score
                    MATCH (d:Document)-[:HAS_CHUNK]->(node)
                    RETURN node.text as chunk_text, 
                           d.name as document_name,
                           node.chunk_index as chunk_index,
                           score
                    ORDER BY score DESC
                """, query_embedding=query_embedding, limit=limit)
                
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Error searching chunks: {e}")
                return []
    
    def search_similar_questions(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar questions using vector similarity"""
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
        
        with self.driver.session() as session:
            try:
                result = session.run("""
                    CALL db.index.vector.queryNodes('question_embedding', $limit, $query_embedding)
                    YIELD node, score
                    MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:HAS_QUESTION]->(node)
                    RETURN node.text as question_text,
                           c.text as chunk_text,
                           d.name as document_name,
                           c.chunk_index as chunk_index,
                           score
                    ORDER BY score DESC
                """, query_embedding=query_embedding, limit=limit)
                
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Error searching questions: {e}")
                return []
    
    def generate_ai_response(self, query: str, chunks: List[Dict]) -> str:
        """Generate AI response based on retrieved chunks without altering facts"""
        if not chunks:
            return "No relevant information found in the knowledge base."
        
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks):
            doc_name = chunk.get('document_name', 'Unknown Document')
            chunk_idx = chunk.get('chunk_index', 0)
            chunk_text = chunk.get('chunk_text', '')
            
            context_parts.append(f"Source {i+1} [{doc_name}:{chunk_idx}]:\n{chunk_text}")
        
        context = "\n\n".join(context_parts)
        
        # Generate response that synthesizes but doesn't alter facts
        prompt = f"""Based ONLY on the following retrieved information, provide a comprehensive answer to the user's question. 

CRITICAL RULES:
- Use ONLY the information provided in the sources below
- Do NOT add any external knowledge or make assumptions
- Do NOT alter any facts, numbers, dates, or specific claims
- Synthesize and explain the information to answer the question
- Reference sources using the format [DocumentName:ChunkIndex]
- If the sources don't fully answer the question, clearly state what information is missing

User Question: "{query}"

Retrieved Sources:
{context}

Provide a clear, comprehensive answer based exclusively on these sources:"""
        
        try:
            client = ollama.Client(host=self.ollama_host)
            response = client.chat(
                model=self.chat_model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"Error generating AI response: {e}"
    
    def summarize_chunk(self, chunk_text: str, query: str) -> str:
        """Generate a brief summary of how a chunk relates to the query"""
        if not chunk_text:
            return "Empty chunk"
        
        # Keep it simple - just truncate if too long and indicate relevance
        if len(chunk_text) > 200:
            preview = chunk_text[:200] + "..."
        else:
            preview = chunk_text
        
        return f"Contains information about: {preview}"
    
    def close(self):
        """Close Neo4j driver"""
        self.driver.close()

# Initialize the GraphRAG API
graphrag = GraphRAGAPI()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "GraphRAG API"})

@app.route('/search/chunks', methods=['POST'])
def search_chunks():
    """Search for similar chunks"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = min(data.get('limit', 5), 10)  # Max 10 results
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        results = graphrag.search_similar_chunks(query, limit)
        
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        })
    
    except Exception as e:
        logger.error(f"Error in search_chunks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/search/questions', methods=['POST'])
def search_questions():
    """Search for similar questions"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = min(data.get('limit', 5), 10)  # Max 10 results
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        results = graphrag.search_similar_questions(query, limit)
        
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        })
    
    except Exception as e:
        logger.error(f"Error in search_questions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download_pdfs():
    print("Starting GraphRAG PDF Ingestion...")
    print("=" * 50)
    
    ingestor = GraphRAGIngestor()
    
    bucket_name = "staging"
    download_dir = "./pdfs"

    try:
        # Step 1: Download PDFs from S3
        print(f"Downloading PDFs from bucket '{bucket_name}'...")
        pdf_files = ingestor.download_pdfs(bucket_name, download_dir)
        print(f"Downloaded {len(pdf_files)} PDFs to {download_dir}")
        
        print("Connecting to Neo4j and Ollama...")
        ingestor.ingest_all_pdfs(download_dir)
        print("\n" + "=" * 50)
        print("✅ Ingestion completed successfully!")
        print("\nGraph structure created:")
        print("📄 Document nodes with PDF metadata")
        print("📝 Chunk nodes with text and embeddings")
        print("❓ Question nodes with generated questions and embeddings")
        print("🔗 Relationships: Document -> Chunk -> Question")
        return jsonify({
            "status": "success",
            "message": f"Ingested {len(pdf_files)} PDFs successfully."
        }), 200
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        print("\nPlease check:")
        print("- Neo4j is running at bolt://neo4j.hyperplane-neo4j:7687")
        print("- Ollama is running with models: nomic-embed-text:latest and granite-3.3-8b-instruct-Q6_K_L:latest")
        print("- PDF files are present in the current directory")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        ingestor.close()

@app.route('/query', methods=['POST'])
def query_chunks():
    """Query for relevant chunks based on semantic similarity - no AI generation"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = min(data.get('limit', 5), 20)  # Max 20 chunks
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Get relevant chunks based on semantic similarity
        chunks = graphrag.search_similar_chunks(query, limit)
        
        return jsonify({
            "query": query,
            "chunks": chunks,
            "count": len(chunks)
        })
    
    except Exception as e:
        logger.error(f"Error in query_chunks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_with_ai():
    """Query chunks and generate AI response with source summaries"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = min(data.get('limit', 5), 20)  # Max 20 chunks
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Get relevant chunks
        chunks = graphrag.search_similar_chunks(query, limit)
        
        if not chunks:
            return jsonify({
                "query": query,
                "answer": "No relevant information found in the knowledge base.",
                "chunks": [],
                "source_summaries": [],
                "count": 0
            })
        
        # Generate AI response based on chunks
        ai_answer = graphrag.generate_ai_response(query, chunks)
        
        # Create source summaries
        source_summaries = []
        for chunk in chunks:
            summary = {
                "document_name": chunk.get('document_name', 'Unknown'),
                "chunk_index": chunk.get('chunk_index', 0),
                "score": chunk.get('score', 0.0),
                "summary": graphrag.summarize_chunk(chunk.get('chunk_text', ''), query)
            }
            source_summaries.append(summary)
        
        return jsonify({
            "query": query,
            "answer": ai_answer,
            "chunks": chunks,
            "source_summaries": source_summaries,
            "count": len(chunks)
        })
    
    except Exception as e:
        logger.error(f"Error in ask_with_ai: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/documents', methods=['GET'])
def get_documents():
    """Get all documents in the database"""
    try:
        with graphrag.driver.session() as session:
            # Count documents
            doc_count = session.run("MATCH (d:Document) RETURN count(d) as count").single()['count']
            
            # Get all document names
            docs = session.run("MATCH (d:Document) RETURN d.name as name ORDER BY d.name").data()
            doc_names = [doc['name'] for doc in docs]
            
            return jsonify({
                "document_count": doc_count,
                "documents": doc_names
            })
    
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/stats', methods=['GET'])
def get_stats():
    """Get statistics about the knowledge graph"""
    try:
        with graphrag.driver.session() as session:
            # Count nodes
            doc_count = session.run("MATCH (d:Document) RETURN count(d) as count").single()['count']
            chunk_count = session.run("MATCH (c:Chunk) RETURN count(c) as count").single()['count']
            question_count = session.run("MATCH (q:Question) RETURN count(q) as count").single()['count']
            
            # Get document names
            docs = session.run("MATCH (d:Document) RETURN d.name as name, d.chunk_count as chunks").data()
            
            return jsonify({
                "documents": doc_count,
                "chunks": chunk_count,
                "questions": question_count,
                "document_list": docs
            })
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting GraphRAG API server...")
        logger.info("Available endpoints:")
        logger.info("  GET  /health - Health check")
        logger.info("  POST /search/chunks - Search similar chunks")
        logger.info("  POST /search/questions - Search similar questions")
        logger.info("  POST /query - Query relevant chunks (no AI generation)")
        logger.info("  POST /ask - AI-generated answer with source summaries")
        logger.info("  GET  /stats - Get knowledge graph statistics")
        logger.info("")
        logger.info("Server starting on http://0.0.0.0:8000")
        
        app.run(host='0.0.0.0', port=8000, debug=False)
    
    except KeyboardInterrupt:
        logger.info("Shutting down GraphRAG API server...")
    finally:
        graphrag.close()