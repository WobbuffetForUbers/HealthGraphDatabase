import os
import glob
from pypdf import PdfReader
import google.generativeai as genai
from opensearchpy import OpenSearch

# 1. Configuration
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)

INDEX_NAME = "clinical_guidelines"

def create_index():
    if not client.indices.exists(INDEX_NAME):
        settings = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": "100"
                }
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 768,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16
                            }
                        }
                    },
                    "source": {"type": "keyword"}
                }
            }
        }
        client.indices.create(INDEX_NAME, body=settings)
        print(f"Created index {INDEX_NAME}")

def get_embedding(text):
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",
        title="Clinical Guideline Chunk"
    )
    return result['embedding']

def ingest_pdfs():
    create_index()
    pdf_files = glob.glob("./guidelines/*.pdf")
    
    for pdf_path in pdf_files:
        print(f"Processing {pdf_path}...")
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
        
        # Simple chunking (by paragraphs or fixed length)
        chunks = [full_text[i:i+2000] for i in range(0, len(full_text), 1500)]
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            embedding = get_embedding(chunk)
            doc = {
                "text": chunk,
                "embedding": embedding,
                "source": os.path.basename(pdf_path)
            }
            client.index(index=INDEX_NAME, body=doc)
            print(f"Indexed chunk {i+1}/{len(chunks)} from {os.path.basename(pdf_path)}")

if __name__ == "__main__":
    ingest_pdfs()
