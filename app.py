import streamlit as st
import feedparser
from dateutil import parser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup  # New tool to search inside HTML

st.set_page_config(page_title="Pro RSS Dashboard", layout="wide")

def extract_image(entry):
    """Detects images in official tags OR inside the HTML description."""
    # 1. Try official media tags first
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''):
                return link.get('href')
    
    # 2. If nothing found, look inside the 'summary' or 'description' HTML
    content = entry.get('summary', '') or entry.get('description', '')
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            return img_tag.get('src')
            
    return None

# --- Rest of the logic ---
st.sidebar.title("Settings")
search_query = st.sidebar.text_input("🔍 Search keywords", "").lower()

feed_list = [
    "https://press.asus.com/rss.xml/",
    "https://edgeup.asus.com/feed/"
]

st.title("🗂️ Personal News Engine")

all_entries = []
with st.spinner('Syncing feeds...'):
    for url in feed_list:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                entry['source_name'] = feed.feed.get('title', 'Source')
                all_entries.append(entry)
        except:
            st.sidebar.warning(f"Error loading: {url}")

# Sort
all_entries.sort(key=lambda x: parser.parse(x.get('published', 'Jan 1 1900')), reverse=True)

# Filter
filtered = [e for e in all_entries if search_query in e.title.lower()] if search_query else all_entries

# Display
for entry in filtered[:30]:
    with st.container():
        col1, col2 = st.columns([1, 4])
        
        # USE OUR NEW DETECTIVE FUNCTION
        img_url = extract_image(entry)
        
        with col1:
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.markdown("### 📰") # Fallback icon

        with col2:
            st.markdown(f"### [{entry.title}]({entry.link})")
            st.caption(f"{entry.source_name} | {entry.get('published', 'N/A')}")
            
            # Clean up the summary text (removes HTML tags so it looks nice)
            clean_summary = BeautifulSoup(entry.get('summary', ''), "html.parser").get_text()
            st.write(clean_summary[:200] + "...")
        
        st.markdown("---")