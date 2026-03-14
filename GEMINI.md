# Clinical QI Copilot - System Architecture & Mandates

## 1. Core Clinical Graph (Neo4j)
- **Data Engine**: Automated ETL pipeline (`etl_synthea.py`) ingesting Synthea-generated clinical records.
- **Schema**: 
    - **Nodes**: `:Patient`, `:Encounter`, `:Condition`, `:Medication`, `:Observation`, `:Provider`.
    - **Relationships**: Unified clinical path mapping (e.g., `(Encounter)-[:DIAGNOSED_WITH]->(Condition)`).
- **Multi-Hop Logic**: Advanced Cypher generation for analyzing transitions between care settings (e.g., ED -> Inpatient boarding times).

## 2. OpenRAG Architecture (OpenSearch + Gemini)
- **Vector Database**: OpenSearch 3.5.0 cluster utilizing the `faiss` k-NN engine for high-performance similarity search.
- **Embedding Model**: `models/text-embedding-004` used for both document indexing and real-time query embedding.
- **Ingestion Pipelines**:
    - **PDF Ingest**: `rag_ingest.py` for processing local clinical policy documents.
    - **Web Ingest**: `web_ingest.py` featuring a headless browser (Playwright) to spider and index the **UCSF Hospitalist & Outpatient Handbooks**.
- **Clinical Archive**: All scraped web content is archived locally as `.txt` files in the `/guidelines` directory for transparency and auditability.

## 3. Intelligent Visualization Engine (UI Upgrade)
- **Concept**: AI-driven translation of raw database records into clinical insights.
- **Visualization Agent**: Uses Gemini to analyze query results and automatically select the most relevant Streamlit chart (Bar, Line, or Area).
- **Clinical Interpretation**: Every visualization includes:
    - **Findings**: A concise (2-sentence) clinical summary of the data trends.
    - **Rationale**: A brief explanation of why the specific visualization was chosen for that QI question.

## 4. MCP Server (Model Context Protocol)
- **Standardized Access**: Provides a unified interface for LLMs to interact with the clinical ecosystem.
- **Tools**:
    - `run_cypher`: Direct execution of queries against the graph.
    - `search_guidelines`: RAG-based vector search across the UCSF Handbook and local policies.

## 5. Security & Engineering Standards
- **API Security**: Strict environment variable management via `.env` and `.gitignore` to prevent credential leakage.
- **Temporal Integrity**: Mandated use of native `datetime()` casting for all ISO 8601 strings in Cypher to ensure accurate throughput calculations.
- **Native Cypher**: Forbids APOC functions in favor of native list comprehensions and `reduce()` logic for stability and portability.
