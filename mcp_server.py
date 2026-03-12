from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase

# 1. Initialize the MCP Server
mcp = FastMCP("ClinicalQI")

# 2. Database connection credentials
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

# 3. Define the AI Tool
@mcp.tool()
def run_cypher(query: str) -> str:
    """Run Cypher queries on the hospital graph database to analyze patient flow, encounters, and QI metrics."""
    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            records, _, _ = driver.execute_query(query)
            # Returns the raw database output as a string to the LLM
            return str([r.data() for r in records])
    except Exception as e:
        return f"Database Error: {e}"

if __name__ == "__main__":
    # Runs the server using standard input/output (required for MCP)
    mcp.run()