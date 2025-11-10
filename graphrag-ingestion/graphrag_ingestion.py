import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
import ollama
import boto3
from pypdf import PdfReader
from neo4j import GraphDatabase

class GraphRAGIngestor:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://neo4j.hyperplane-neo4j:7687", 
            auth=("neo4j", "Shakudo312!")
        )
        self.embedding_model = "nomic-embed-text:latest"
        self.chat_model = "granite-3.3-8b-instruct-Q6_K_L:latest"
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        # Configure Ollama client with custom endpoint
        self.ollama_host = "http://ollama-1.hyperplane-ollama-gpu-1.svc.cluster.local:11434"
    
        username = "shakudo_svc"
        access_key = "PSFBSAZRMKMLKEHHEBPPOPFINJGCBGMJLNPFOJNNF"
        secret_key = "C710E5FDb9c61269+2cfd+58A1104D1c8c2dc7LJFF"
        endpoint_url = "https://flashblade-data.campbell.com"
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            verify=False  # disable SSL cert check
        )
# ---------------- [START] Pull PDFS from Flashblade ------------------
    def download_pdfs(self, bucket: str, download_dir: str):
        print(f"[INFO] Ensuring download directory exists: {download_dir}")
        Path(download_dir).mkdir(parents=True, exist_ok=True)

        processed_file_key = "processed_files.txt"
        local_processed_file = Path(download_dir) / processed_file_key

        print("[INFO] Loading processed files from bucket...")
        processed_files = self._load_processed_files(bucket, local_processed_file, processed_file_key)

        print("[INFO] Listing new PDFs in the bucket...")
        new_files = self._list_new_pdfs(bucket, processed_files)

        if not new_files:
            print("[INFO] No new PDF files to download.")
            return list(Path(download_dir).glob("*.pdf"))

        print("[INFO] Downloading new PDF files...")
        downloaded_files = self._download_new_files(bucket, new_files, download_dir)

        print("[INFO] Updating processed files log in the bucket...")
        processed_files.update(new_files)
        self._update_processed_files(bucket, local_processed_file, processed_file_key, processed_files)

        print(f"[INFO] Download completed. Total downloaded: {len(downloaded_files)} files.")
        return downloaded_files

    # -----------------------------
    # Helper functions
    # -----------------------------
    
    def _load_processed_files(self, bucket: str, local_file: Path, s3_key: str):
        """Download and load processed_files.txt from the bucket. Create locally if it doesn't exist."""
        processed_files = set()
        try:
            print(f"[DEBUG] Attempting to download {s3_key} from bucket {bucket}...")
            self.s3.download_file(bucket, s3_key, str(local_file))
            with open(local_file) as f:
                processed_files = set(line.strip() for line in f)
            print(f"[INFO] Loaded {len(processed_files)} processed files from bucket.")
        except self.s3.exceptions.NoSuchKey:
            # File doesn't exist in the bucket yet, create empty local file
            print("[WARN] processed_files.txt not found in bucket. Creating new local file.")
            local_file.touch(exist_ok=True)
        except Exception as e:
            print(f"[ERROR] Failed to load processed_files.txt: {e}")
            # still create empty local file to allow updates
            local_file.touch(exist_ok=True)

        return processed_files

    def _list_new_pdfs(self, bucket: str, processed_files: set):
        """List all PDFs in the bucket that haven't been processed yet."""
        try:
            response = self.s3.list_objects_v2(Bucket=bucket)
            all_files = response.get("Contents", [])
            print(f"[DEBUG] Total objects in bucket: {len(all_files)}")
            new_files = [
                obj["Key"]
                for obj in all_files
                if obj["Key"].lower().endswith(".pdf") and obj["Key"] not in processed_files
            ]
            print(f"[INFO] Found {len(new_files)} new PDF(s) to download.")
        except Exception as e:
            print(f"[ERROR] Failed to list objects in bucket: {e}")
            new_files = []
        return new_files

    def _download_new_files(self, bucket: str, new_files: list, download_dir: str):
        """Download new PDFs and return the local file paths."""
        downloaded_files = []
        for key in new_files:
            local_path = Path(download_dir) / Path(key).name
            try:
                print(f"[DEBUG] Downloading {key} to {local_path}...")
                self.s3.download_file(bucket, key, str(local_path))
                downloaded_files.append(local_path)
            except Exception as e:
                print(f"[ERROR] Failed to download {key}: {e}")
        return downloaded_files

    def _update_processed_files(self, bucket: str, local_file: Path, s3_key: str, processed_files: set):
        """Update processed_files.txt locally and push it back to the bucket."""
        try:
            with open(local_file, "w") as f:
                for key in sorted(processed_files):
                    f.write(f"{key}\n")
            print(f"[DEBUG] Uploading updated {s3_key} back to bucket {bucket}...")
            self.s3.upload_file(str(local_file), bucket, s3_key)
            print("[INFO] processed_files.txt updated successfully in the bucket.")
        except Exception as e:
            print(f"[ERROR] Failed to update processed_files.txt: {e}")

    # ---------------- [END] Pull PDFS from Flashblade ------------------

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if not text:
            return []
        
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = " ".join(chunk_words)
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks
    
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
            print(f"Error getting embedding: {e}")
            return []
    
    def generate_questions(self, chunk_text: str) -> List[str]:
        """Generate 1-2 questions for a chunk using LLM"""
        prompt = f"""Based on the following text chunk, generate 1-2 concise questions that this chunk could answer. Return only the questions, one per line.

Text chunk:
{chunk_text[:500]}..."""
        
        try:
            client = ollama.Client(host=self.ollama_host)  # <--- use client
            response = client.chat(
                model=self.chat_model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            questions_text = response['message']['content'].strip()
            questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
            return questions[:2]  # Limit to 2 questions
        except Exception as e:
            print(f"Error generating questions: {e}")
            return []
    
    def create_graph_schema(self):
        """Create Neo4j constraints and indexes"""
        with self.driver.session() as session:
            # Create constraints
            session.run("CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
            session.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")
            session.run("CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE")
            
            # Create vector indexes
            try:
                session.run("CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS FOR (c:Chunk) ON c.embedding OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}}")
                session.run("CREATE VECTOR INDEX question_embedding IF NOT EXISTS FOR (q:Question) ON q.embedding OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}}")
            except:
                pass  # Index might already exist
    
    def ingest_document(self, pdf_path: str):
        """Ingest a single PDF document"""
        print(f"Processing {pdf_path}...")
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            print(f"No text extracted from {pdf_path}")
            return
        
        # Generate document ID
        doc_id = hashlib.md5(pdf_path.encode()).hexdigest()
        doc_name = Path(pdf_path).stem
        
        # Chunk text
        chunks = self.chunk_text(text)
        print(f"Generated {len(chunks)} chunks")
        
        with self.driver.session() as session:
            # Create document node
            session.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.name = $name, 
                    d.path = $path, 
                    d.text_length = $text_length,
                    d.chunk_count = $chunk_count
            """, doc_id=doc_id, name=doc_name, path=pdf_path, 
                text_length=len(text), chunk_count=len(chunks))
            
            # Process each chunk
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                
                # Get embedding for chunk
                chunk_embedding = self.get_embedding(chunk_text)
                if not chunk_embedding:
                    continue
                
                # Create chunk node
                session.run("""
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.text = $text,
                        c.embedding = $embedding,
                        c.chunk_index = $index
                    WITH c
                    MATCH (d:Document {id: $doc_id})
                    MERGE (d)-[:HAS_CHUNK]->(c)
                """, chunk_id=chunk_id, text=chunk_text, 
                    embedding=chunk_embedding, index=i, doc_id=doc_id)
                
                # Generate and process questions
                questions = self.generate_questions(chunk_text)
                for j, question_text in enumerate(questions):
                    question_id = f"{chunk_id}_question_{j}"
                    
                    # Get embedding for question
                    question_embedding = self.get_embedding(question_text)
                    if not question_embedding:
                        continue
                    
                    # Create question node and relationship
                    session.run("""
                        MERGE (q:Question {id: $question_id})
                        SET q.text = $text,
                            q.embedding = $embedding
                        WITH q
                        MATCH (c:Chunk {id: $chunk_id})
                        MERGE (c)-[:HAS_QUESTION]->(q)
                    """, question_id=question_id, text=question_text, 
                        embedding=question_embedding, chunk_id=chunk_id)
                
                print(f"Processed chunk {i+1}/{len(chunks)}")
        
        print(f"Successfully ingested {pdf_path}")
    
    def ingest_all_pdfs(self, folder_path: str = "pdfs"):
        """Ingest all PDF files in the folder that haven't been ingested yet"""
        folder = Path(folder_path)
        processed_file_path = folder / "processed_files_ingested.txt"

        # Load already ingested files
        processed_files = set()
        if processed_file_path.exists():
            with open(processed_file_path, "r") as f:
                processed_files = set(line.strip() for line in f if line.strip())

        # Find all PDFs in folder
        pdf_files = list(folder.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return

        print(f"Found {len(pdf_files)} PDF files, {len(processed_files)} already ingested")

        # Create schema once
        self.create_graph_schema()

        for pdf_file in pdf_files:
            if pdf_file.name in processed_files:
                print(f"Skipping {pdf_file.name} (already ingested)")
                continue

            try:
                self.ingest_document(str(pdf_file))
                print(f"✅ Successfully ingested {pdf_file.name}")

                # Mark as ingested
                with open(processed_file_path, "a") as f:
                    f.write(f"{pdf_file.name}\n")
                processed_files.add(pdf_file.name)

                # Remove the file after successful ingestion
                pdf_file.unlink()
                print(f"🗑️ Removed {pdf_file.name} from {folder_path}")

            except Exception as e:
                print(f"❌ Error processing {pdf_file}: {e}")

    
    def close(self):
        """Close Neo4j driver"""
        self.driver.close()

def main():
    """Main function to run the ingestion"""
    ingestor = GraphRAGIngestor()
    
    try:
        ingestor.ingest_all_pdfs()
        print("Ingestion completed!")
    except Exception as e:
        print(f"Error during ingestion: {e}")
    finally:
        ingestor.close()

if __name__ == "__main__":
    main()