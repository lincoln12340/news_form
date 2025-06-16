import streamlit as st
import requests
import time
import os
import tempfile
from serpapi import GoogleSearch
from urllib.parse import urlparse
from openai import OpenAI


# Constants
WEBHOOK_URL =  st.secrets["WEBHOOK_URL"]
DIFFBOT_TOKEN = st.secrets["DIFFBOT_TOKEN"]
SERPAPI_KEY =  st.secrets["SERPAPI_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Set page config
st.set_page_config(page_title="Press Release Scraper", page_icon="📰", layout="centered")

# UI Styling
st.markdown("""
    <style>
        .title { font-size: 32px; font-weight: bold; color: #0A74DA; text-align: center; }
        .subtitle { text-align: center; font-size: 18px; color: #555; margin-top: -10px; }
    </style>
""", unsafe_allow_html=True)

# Function: Extract content from article
def extract_diffbot_data(link):
    url = f"https://api.diffbot.com/v3/analyze?url={link}&token={DIFFBOT_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        article = data.get("objects", [])[0]
        return article.get("text", "N/A")
    except Exception as e:
        return f"\u26a0\ufe0f Error retrieving content: {e}"

# Function: Upload PDF to Vector Store
def handle_pdf_workflow(pdf_link, vector_store_id):
    try:
        response = requests.get(pdf_link)
        if response.status_code != 200:
            return {"error": f"Failed to download PDF: {pdf_link}"}

        filename = os.path.basename(urlparse(pdf_link).path)
        if not filename.endswith(".pdf"):
            filename += ".pdf"

        tmp_path = os.path.join(tempfile.gettempdir(), filename)
        with open(tmp_path, "wb") as f:
            f.write(response.content)

        uploaded_file = client.files.create(file=open(tmp_path, "rb"), purpose="assistants")

        client.vector_stores.file_batches.create(
            vector_store_id=vector_store_id,
            file_ids=[uploaded_file.id]
        )

        return {"status": "Uploaded", "filename": filename, "link": pdf_link}
    except Exception as e:
        return {"error": str(e)}

# Function: Run both search workflows
def search_and_scrape(company, product, year):
    queries = [
        {
            "query": f'("{product}") "{year}" (press release OR news)',
            "type": "news"
        },
        {
            "query": f'("{product}") "{year}" (press release OR news) filetype:pdf',
            "type": "pdf"
        }
    ]

    news_results = []
    pdf_results = []

    vector_store = client.vector_stores.create(name=f"{company}_{year}_VectorStore")

    for q in queries:
        st.info(f"\U0001F50D Searching: *{q['query']}*")
        params = {"q": q["query"], "api_key": SERPAPI_KEY}

        try:
            search = GoogleSearch(params)
            response = search.get_dict()
        except Exception as e:
            st.error(f"\u274c SerpAPI error: {e}")
            continue

        for result in response.get("organic_results", []):
            title = result.get("title", "")
            link = result.get("link", "")
            date = result.get("date", "")

            if q["type"] == "news":
                content = extract_diffbot_data(link)
                news_results.append({
                    "title": title,
                    "link": link,
                    "date": date,
                    "content": content
                })
                time.sleep(2)

            elif q["type"] == "pdf" and link.endswith(".pdf"):
                upload_result = handle_pdf_workflow(link, vector_store.id)
                pdf_results.append({
                    "title": title,
                    "link": link,
                    "date": date,
                    "upload_result": upload_result,
                    "vector store": vector_store.id
                })

    return news_results, pdf_results

# Function: Post to Webhook
def post_to_webhook(data):
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code == 200:
            st.success("\u2705 Webhook successfully posted.")
        else:
            st.error(f"\u274c Webhook failed: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"\u274c Webhook error: {e}")

# UI
st.markdown('<div class="title">\U0001F4F0 Press Release Scraper</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Find news & PDFs, upload to OpenAI, then post to your webhook</div>', unsafe_allow_html=True)
st.markdown("---")

def assistant1(vector_store_id,company):
    instructions = """ You are an expert biotechnology researcher focused on pharmaceutical company developments. Your task is to analyze press release content stored in a vector store and extract the most relevant product-related news, product-related milestones, or product-related clinical trial updates for a specific year.

    You will receive:

    A separate list of dictionaries containing metadata for each file

    Your task:

    Only analyze content from files found in the vector store.

    For each te, determine whether it meets all of the following conditions:

    Clearly mentions the specified product.

    Includes a timeframe (quarter, half-year, or specific date).

    Contains a milestone or event expected to happen in the target year, even if the document is published earlier or later.

    For each qualifying file, use the file_name to match it with its corresponding metadata entry. Then, extract and return the following structured JSON:

    id: A unique 8-character alphanumeric string.

    company: Company name.

    ticker: Ticker of the Company

    product: Product name or code.

    news: A specific and concise summary of the milestone or clinical update.

    timeframe: One or more of Q1, Q2, Q3, Q4, or ranges like Q1,Q2.

    year: Must match the specified target year.

    source:

    Source Name: Extract from metadata title or use "Unknown".

    url: From metadata.

    publication_date: From metadata, formatted as YYYY-MM-DD.

    Timeframe Parsing Rules:
    "H1" or "first half of the year" → Q1,Q2

    "Mid-year" → Q2,Q3

    "H2" or "second half" → Q3,Q4

    "early [year]" → Q1

    "late [year]" → Q4

    Use specific quarters when directly mentioned (e.g., Q2).

    Ignore any entry with no time indicator.

    Output:
    Return the final output as valid JSON only — no markdown or explanations.

    If no valid entries are found, return:

    {
    "results": [],
    "message": "No upcoming milestones or events found in the PDFs for [PRODUCT] by [COMPANY] in [TARGET_YEAR]."
    }

    All extracted information must be factually grounded in the text and tied to a milestone or event expected in the target year."""

    assistant = client.beta.assistants.create(
        name=f"{company} Assistant",
        instructions=instructions,
        tools=[{"type": "file_search"}],
        model= "gpt-4.1",
        tool_resources={"file_search":{"vector_store_ids":[vector_store_id]}}
        
    )

   
    return assistant





with st.form("search_form"):
    company = st.text_input("Company Name", "Avidity Biosciences")
    product = st.text_input("Product Name", "AOC 1001")
    year = st.text_input("Target Year", "2025")
    submitted = st.form_submit_button("Generate")

if submitted:
    news_data, pdf_data = search_and_scrape(company, product, year)
    vector_store_id = pdf_data[0]["vector store"]
    
    assistant = assistant1(vector_store_id,company)


    

    if news_data or pdf_data:
        payload = {
            "company": company,
            "product": product,
            "year": year,
            "press_releases": news_data,
            "pdf_uploads": pdf_data,
            "assistant":assistant.id,
            "vector store id": vector_store_id
        }
        post_to_webhook(payload)
        st.success("\u2705 Done! Check back on 'Universe Data' in 1–2 minutes.")
