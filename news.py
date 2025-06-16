import requests
import json
import time
import random
from bs4 import BeautifulSoup
from serpapi import GoogleSearch

WEBHOOK_URL = "https://hook.eu2.make.com/34mhiff5txeogxm8uf4qy5o2uawbi2to"


def extract_diffbot_data(link):
    url = f"https://api.diffbot.com/v3/analyze?url={link}&token=fdbc63a153d0d8da7c0dfb7ccef69945"
    headers = {"accept": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        article = data.get("objects", [])[0]  # Take the first object

        title = article.get("title", "N/A")
        date = article.get("date", "N/A")
        link = article.get("pageUrl", "N/A")
        content = article.get("text", "N/A")

        return content

        #print("🔹 Title:", title)
        #print("📅 Date:", date)
        #print("🔗 Link:", link)
        #print("\n📄 Content:\n", content[:1000], "...")  # Print first 1000 chars for brevity

    except Exception as e:
        print(f"❌ Failed to extract Diffbot data: {e}")
        print(link)

def main():
    session = requests.Session()
    session.get("https://www.google.com", timeout=10)

    # Sample query - SerpAPI
    company_name = "Avidity Biosciences"
    product_name = "AOC 1001"
    target_year = "2025"
    query = f"{target_year} Press Releases about {product_name} by {company_name}"
    
    params = {
        "q": query,
        "api_key": "6bbbb0268f96b1336ac50343fe6ef93a286a74d0f64c3d09fca848c5d62c9cce"
    }

    print(f"\n🔍 Searching SerpAPI with query: {query}")
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        print(results)
        print("✅ SerpAPI search completed")
    except Exception as e:
        print(f"❌ SerpAPI error: {e}")
        return
    
    press_releases = []
    for item in results.get("organic_results", []):
        title = item.get("title", "")
        date = item.get("date", "")
        link = item.get("link", "")
        print(f"\n📄 Scraping: {title}")
        content = extract_diffbot_data(link)

        press_releases.append({
            "title": title,
            "date": date,
            "link": link,
            "content": content
        })

        time.sleep(4)

    #Webhook payload
    payload = {
        "press_releases": press_releases,
        "company": company_name,
        "product": product_name,
        "year": target_year
    }

    print("\n📤 Sending to Make.com webhook...")
    try:
        response = session.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print("✅ Successfully posted to the webhook.")
        else:
            print(f"❌ Webhook error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error posting to webhook: {e}")

if __name__ == "__main__":
    main()


    #press_releases = []
    #for item in results.get("organic_results", []):
        #title = item.get("title", "")
        #date = item.get("date", "")
        #link = item.get("link", "")
        #print(f"\n📄 Scraping: {title}")
        #content = scrape_page(link, session)

        #press_releases.append({
            #"title": title,
            #"date": date,
            #"link": link,
            #"content": content
        #})

    # Webhook payload
    #payload = {
        #"press_releases": press_releases,
        #"company": company_name,
        #"product": product_name,
        #"year": target_year
    #}

    #print("\n📤 Sending to Make.com webhook...")
    #try:
        #response = session.post(WEBHOOK_URL, json=payload)
        #if response.status_code == 200:
            #print("✅ Successfully posted to the webhook.")
        #else:
            #print(f"❌ Webhook error: {response.status_code} - {response.text}")
    #except Exception as e:
        #print(f"❌ Error posting to webhook: {e}")

    # Preview results
    #print("\n📰 Preview of Scraped Press Releases")
    #for pr in press_releases:
        #print(f"\n--- {pr['title']} ({pr['date']}) ---")
        #print(f"🔗 {pr['link']}")
        #print(f"\n{pr['content'][:800]}...\n{'-'*80}")