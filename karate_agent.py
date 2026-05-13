import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.agents import create_agent

load_dotenv()

# Read agent instructions from .md file
with open("instructions.md", "r") as f:
    agent_instructions = f.read()        # reads the whole .md file as text



#1. Define TOOL

@tool
def generate_karate_feature(
    feature_name: str, base_url: str, endpoint: str, method: str,
    headers: str, request_body: str, expected_status: str,
    expected_fields: str, scenario_name: str
) -> str:
    """Generates a Karate BDD .feature file for API testing."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    prompt = PromptTemplate(
        input_variables=["feature_name","base_url","endpoint","method",
                         "headers","request_body","expected_status",
                         "expected_fields","scenario_name"],
        template="""
You are a Karate API testing expert. Generate a complete Karate BDD feature file.
Feature Name: {feature_name}
Base URL: {base_url}
Endpoint: {endpoint}
HTTP Method: {method}
Headers: {headers}
Request Body: {request_body}
Expected Status Code: {expected_status}
Expected Response Fields: {expected_fields}
Scenario Name: {scenario_name}
Generate a complete Karate .feature file with Feature description, Background section,
positive scenario, negative scenario, and proper Karate syntax with match assertions.
Return only the raw .feature file content, no explanation.
"""
    )

    chain = prompt | llm
    response = chain.invoke({
        "feature_name": feature_name, "base_url": base_url,
        "endpoint": endpoint, "method": method, "headers": headers,
        "request_body": request_body, "expected_status": expected_status,
        "expected_fields": expected_fields, "scenario_name": scenario_name
    })
    return response.content


# ============================================
# AGENT
# ============================================
@st.cache_resource
def get_agent(api_key: str):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key
    )
    tools = [generate_karate_feature]

    return create_agent(
        llm,
        tools,
        system_prompt=agent_instructions
    )


# ============================================
# STREAMLIT UI
# ============================================
st.set_page_config(page_title="KarateGen AI")
st.title("KarateGen AI")
st.caption("Fill in your API details and let the Agent generate your Karate feature file!")

# --- Sidebar: API Key ---
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-xxxxxxxx"
    )
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key # Set the API key in environment variable for the agent to use
        st.success("API Key set!")
    else:
        st.warning("Please enter your API Key")

if not api_key:
    st.info("Enter your OpenAI API Key in the sidebar to get started")
    st.stop()

# --- Input Fields ---
st.subheader("API Details")

col1, col2 = st.columns(2)

with col1:
    feature_name   = st.text_input("Feature Name", placeholder="e.g. User Login")
    base_url       = st.text_input("Base URL", placeholder="e.g. https://api.example.com")
    endpoint       = st.text_input("Endpoint", placeholder="e.g. /auth/login")
    method         = st.selectbox("HTTP Method", ["POST", "GET", "PUT", "DELETE", "PATCH"])

with col2:
    headers        = st.text_input("Headers", placeholder="e.g. Content-Type: application/json")
    expected_status= st.text_input("Expected Status Code", placeholder="e.g. 200")
    expected_fields= st.text_input("Expected Response Fields", placeholder="e.g. token, userId")
    scenario_name  = st.text_input("Scenario Name", placeholder="e.g. Successful Login")

request_body = st.text_area(
    "Request Body",
    placeholder='e.g. {"username": "test", "password": "pass123"}',
    height=100
)

st.markdown("---")

# --- Generate Button ---
if st.button("Generate Karate Feature File", use_container_width=True):

    if not all([feature_name, base_url, endpoint, method,
                headers, expected_status, expected_fields,
                scenario_name, request_body]):
        st.warning("Please fill in all fields before generating!")

    else:
        user_message = f"""
        Generate a Karate feature file with these details:
        - Feature name: {feature_name}
        - Base URL: {base_url}
        - Endpoint: {endpoint}
        - Method: {method}
        - Headers: {headers}
        - Request body: {request_body}
        - Expected status: {expected_status}
        - Expected fields: {expected_fields}
        - Scenario name: {scenario_name}
        """

        with st.spinner("Agent is generating your feature file..."):
            agent = get_agent(api_key)
            result = agent.invoke({"messages": [("human", user_message)]})
            response = result["messages"][-1].content

        st.success("Feature file generated!")
        st.subheader("Generated Karate Feature File")
        st.code(response, language="gherkin")

        st.download_button(
            label="Download .feature File",
            data=response,
            file_name=f"{feature_name.replace(' ', '_')}.feature",
            mime="text/plain",
            use_container_width=True
        )