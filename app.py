import streamlit as st
import google.generativeai as genai
from neo4j import GraphDatabase
import os

# Page Configuration
st.set_page_config(page_title="Clinical QI Copilot", page_icon="🏥", layout="wide")
st.title("🏥 Clinical QI Copilot")
st.markdown("Query the Synthea Graph Database to analyze patient flow bottlenecks.")

# 1. Database connection credentials
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

# 2. Configure Gemini API
API_KEY = "AIzaSyAZM55eLmJ7BPrsRooYC2PXynnIdEd8-lg"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

# Helper function to run Cypher queries
def run_query(cypher_query):
    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            records, _, _ = driver.execute_query(cypher_query)
            return [r.data() for r in records]
    except Exception as e:
        return f"Error: {str(e)}"

# Helper function to generate Cypher from natural language
def generate_cypher(prompt):
    system_prompt = """
    You are a Cypher query expert for a Neo4j database representing clinical data.
    The database has:
    - :Patient nodes with properties like 'first', 'last', 'birthdate', 'id'
    - :Encounter nodes with properties like 'start', 'stop', 'description', 'type', 'id'
    - (Patient)-[:HAS_ENCOUNTER]->(Encounter) relationships.

    Convert the user's natural language request into a valid Cypher query.
    Return ONLY the Cypher query text, without any markdown formatting or code blocks.
    """
    response = model.generate_content(f"{system_prompt}\n\nUser request: {prompt}")
    return response.text.strip().replace("```cypher", "").replace("```", "")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input Prompt
if prompt := st.chat_input("Ask about hospital capacity or patient flow..."):
    # Add user message to UI
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        # 3. Translate to Cypher
        with st.spinner("Generating Cypher query..."):
            cypher = generate_cypher(prompt)
            st.code(cypher, language="cypher")
        
        # 4. Execute Query
        with st.spinner("Executing query..."):
            results = run_query(cypher)
            
            if isinstance(results, str) and results.startswith("Error"):
                st.error(results)
                response = f"I encountered an error while running the query."
            else:
                st.write("Results:", results)
                response = f"I found {len(results)} results for your query."

        st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})