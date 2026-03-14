import streamlit as st
import google.generativeai as genai
from neo4j import GraphDatabase
from opensearchpy import OpenSearch
import os
import pandas as pd
import json
from dotenv import load_dotenv

# Page Configuration
st.set_page_config(page_title="Clinical QI Copilot", page_icon="🏥", layout="wide")

# 1. Configuration
load_dotenv()
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")
INDEX_NAME = "clinical_guidelines"

# 2. Configure APIs
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("GEMINI_API_KEY environment variable not set. Please set it in a .env file.")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

# OpenSearch Client
os_client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)

# --- Helper Functions ---
def run_query(cypher_query):
    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            records, _, _ = driver.execute_query(cypher_query)
            return [r.data() for r in records]
    except Exception as e:
        return f"Error: {str(e)}"

def search_guidelines(query):
    try:
        embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )['embedding']

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
        return [{"text": hit['_source']['text'], "source": hit['_source']['source']} for hit in response['hits']['hits']]
    except:
        return []

def check_clarity(prompt):
    """Checks if the clinical request is clear enough for Cypher generation."""
    clarity_prompt = f"""
    Analyze this clinical quality improvement request: "{prompt}"
    
    TASK:
    Determine if this request can be converted into a clinical database query.
    
    RULES:
    - If a specific clinical condition (e.g., "heart failure", "diabetes") is mentioned, it is CLEAR.
    - If a specific care process (e.g., "admissions", "boarding", "medications") is mentioned, it is CLEAR.
    - Only return is_clear: false if the prompt is a single word or completely nonsensical.
    - If in doubt, set is_clear: true.
    
    Return ONLY JSON:
    {{
        "is_clear": true/false,
        "question": "..."
    }}
    """
    try:
        response = model.generate_content(clarity_prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except:
        return {"is_clear": True, "question": ""}

def generate_cypher(prompt, context="", error_feedback=""):
    """Generates Cypher, optionally incorporating previous error feedback."""
    system_prompt = f"""
    You are an expert Clinical Data Scientist and Cypher expert. 
    
    GUIDELINE CONTEXT (RAG):
    {context}

    SCHEMA:
    - (p:Patient {{id, first, last, birthdate, gender, race, ethnicity, city}})
    - (e:Encounter {{id, start, stop, description, type, reason_description}})
    - (c:Condition {{code, description, start, stop}})
    - (m:Medication {{code, description, start, stop, total_cost}})
    - (pr:Provider {{id, name, specialty, gender}})

    RELATIONSHIPS:
    - (p)-[:HAS_ENCOUNTER]->(e), (p)-[:HAS_CONDITION]->(c), (p)-[:PRESCRIBED]->(m)
    - (e)-[:DIAGNOSED_WITH]->(c), (e)-[:MEDICATION_ORDERED]->(m), (e)-[:PERFORMED_BY]->(pr)

    QUERY STRATEGIES:
    1. Longitudinal Chronic Conditions: For chronic conditions (like Heart Failure), join the Patient to their active Conditions based on date ranges.
       Logic: `MATCH (p)-[:HAS_CONDITION]->(c) WHERE c.description =~ '(?i)...' MATCH (p)-[:HAS_ENCOUNTER]->(e) WHERE datetime(e.start) >= datetime(c.start) AND (c.stop IS NULL OR datetime(e.start) <= datetime(c.stop))`
    2. Join Strategy: Try both direct `[:DIAGNOSED_WITH]` links AND the longitudinal date-based strategy above to find all relevant encounters.
    3. Case-Insensitivity: ALWAYS use `(?i)` regex or `toLower()`.
    4. Property Names: Always use `m.total_cost` for medications.

    PREVIOUS ERROR/RESULT FEEDBACK:
    {error_feedback}

    RULES:
    - NO APOC. Use native functions only.
    - Return ONLY the raw Cypher query. No markdown, no explanations.
    """
    response = model.generate_content(f"{system_prompt}\n\nUser request: {prompt}")
    return response.text.strip().replace("```cypher", "").replace("```", "")

def get_viz_recommendation(prompt, df, guidelines=""):
    sample_data = df.head(10).to_json(orient='records')
    viz_prompt = f"""
    Analyze this clinical dataset.
    USER QUESTION: "{prompt}"
    GUIDELINES: {guidelines}
    SAMPLE DATA: {sample_data}

    Determine the best Streamlit chart ("bar_chart", "line_chart", "area_chart", "scatter_chart", or "none").
    Provide "findings" (clinical significance based on data AND guidelines) and "rationale".
    
    RETURN JSON: {{"type": "...", "index": "...", "value": "...", "findings": "...", "rationale": "..."}}
    """
    try:
        response = model.generate_content(viz_prompt)
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except:
        return {"type": "none"}

# --- UI State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "insights" not in st.session_state:
    st.session_state.insights = []

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Clinical Ecosystem")
    
    with st.expander("📈 Database Snapshot", expanded=True):
        if st.button("Refresh Snapshot"):
            summary = run_query("MATCH (n) RETURN labels(n)[0] as label, count(*) as count")
            if isinstance(summary, list):
                for item in summary:
                    st.metric(label=f"Total {item['label']}s", value=f"{item['count']:,}")
    
    with st.expander("🔍 Database Schema"):
        st.markdown("- `Patient`, `Encounter`, `Condition`, `Medication`, `Observation`, `Provider`")
    
    st.header("📌 Saved Insights")
    for insight in reversed(st.session_state.insights):
        with st.container(border=True):
            st.caption(insight['query'])
            st.write(insight['text'])

# --- Main Interface ---
st.title("🏥 Clinical QI Copilot")
st.markdown("Knowledge-grounded clinical data analysis.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "query" in message: st.code(message["query"], language="cypher")
        if "data" in message: st.dataframe(message["data"])
        if "viz" in message and message["viz"].get("type") != "none":
            v = message["viz"]
            if v.get("findings"): st.info(f"**Clinical Findings:** {v['findings']}")
            try:
                chart_data = message["data"].set_index(v["index"])
                if v["type"] == "bar_chart": st.bar_chart(chart_data[v["value"]])
                elif v["type"] == "line_chart": st.line_chart(chart_data[v["value"]])
                elif v["type"] == "area_chart": st.area_chart(chart_data[v["value"]])
                elif v["type"] == "scatter_chart": st.scatter_chart(chart_data[v["value"]])
            except: pass

# User Input
if prompt := st.chat_input("Ask about hospital capacity, patient flow, or clinical trends..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        # 1. Clarity Check
        clarity = check_clarity(prompt)
        if not clarity["is_clear"]:
            response = clarity["question"]
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            # 2. RAG Search
            with st.spinner("Searching Clinical Guidelines..."):
                guidelines = search_guidelines(prompt)
                context_str = "\n".join([f"Source: {g['source']}\nContent: {g['text']}" for g in guidelines])
                if guidelines:
                    with st.expander("📚 Referenced Guidelines", expanded=False):
                        for g in guidelines:
                            st.markdown(f"**Source:** {g['source']}")
                            st.write(g['text'][:500] + "...")
            
            # 3. Iterative Generation Loop
            results = None
            cypher = ""
            error_feedback = ""
            
            for attempt in range(3): # Max 3 iterations
                with st.spinner(f"Analyzing Data (Attempt {attempt+1})..." if attempt > 0 else "Analyzing Clinical Data..."):
                    cypher = generate_cypher(prompt, context_str, error_feedback)
                    st.code(cypher, language="cypher")
                    results = run_query(cypher)
                    
                    if isinstance(results, list) and len(results) > 0:
                        break # Success!
                    elif isinstance(results, list) and len(results) == 0:
                        error_feedback = f"The query returned 0 results. Perhaps the filters were too strict or the terms didn't match. Try a broader search (e.g., using longitudinal condition matching or patient-medication links directly)."
                    else:
                        error_feedback = f"The query failed with error: {results}. Please fix the syntax or relationship mapping."
            
            # 4. Process Results
            if isinstance(results, list) and len(results) > 0:
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                viz = get_viz_recommendation(prompt, df, context_str)
                if viz.get("type") != "none":
                    findings = viz.get("findings", "Trends analyzed.")
                    st.info(f"**Clinical Findings:** {findings}")
                    st.session_state.insights.append({"query": prompt, "text": findings})
                    
                    try:
                        chart_data = df.set_index(viz["index"])
                        if viz["type"] == "bar_chart": st.bar_chart(chart_data[viz["value"]])
                        elif viz["type"] == "line_chart": st.line_chart(chart_data[viz["value"]])
                        elif viz["type"] == "area_chart": st.area_chart(chart_data[viz["value"]])
                        elif viz["type"] == "scatter_chart": st.scatter_chart(chart_data[viz["value"]])
                    except: pass
                response = "Analysis complete based on database records and handbook protocols."
            else:
                response = "I was unable to retrieve valid data after several attempts. Could you please refine your request or provide more specific terms?"

            st.markdown(response)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response, 
                "data": df if 'df' in locals() and results else None,
                "viz": viz if 'viz' in locals() and results else {"type": "none"},
                "query": cypher
            })
