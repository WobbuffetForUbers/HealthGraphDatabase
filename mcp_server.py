from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase
import google.generativeai as genai
from opensearchpy import OpenSearch
import os
from dotenv import load_dotenv

# 1. Initialize the MCP Server
load_dotenv()
mcp = FastMCP("ClinicalQI")

# 2. Database connection credentials
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

# 3. Gemini & OpenSearch Config
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
os_client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)
INDEX_NAME = "clinical_guidelines"

# 4. Define the AI Tools
@mcp.tool()
def run_cypher(query: str) -> str:
    """Run Cypher queries on the hospital graph database to analyze patient flow, encounters, and QI metrics."""
    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            records, _, _ = driver.execute_query(query)
            return str([r.data() for r in records])
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def search_guidelines(query: str) -> str:
    """Search clinical policies and guidelines for relevant procedural or administrative data."""
    try:
        # 1. Embed Query
        embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )['embedding']

        # 2. Vector Search
        search_body = {
            "size": 3,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": embedding,
                        "k": 3
                    }
                }
            },
            "_source": ["text", "source"]
        }
        response = os_client.search(index=INDEX_NAME, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                "source": hit['_source']['source'],
                "text": hit['_source']['text'][:500] + "..." # Snippet for context
            })
        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
