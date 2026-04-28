import streamlit as st
import feedparser
from dateutil import parser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup

st.set_page_config(page_title="RSS Aggregator", layout="wide")

def extract_image(entry):
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''):
                return link.get('href')
    content = entry.get('summary', '') or entry.get('description', '')
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            return img_tag.get('src')
    return None

# Initialize Session States
if 'my_feeds' not in st.session_state:
    st.session_state.my_feeds = {
        "Pressroom RSS": "https://press.asus.com/rss.xml/",
        "EdgeUp RSS": "https://edgeup.asus.com/feed/"
    }

if 'exclude_keywords' not in st.session_state:
    # UPDATED: Default exclusion set to "news" instead of "blog"
    st.session_state.exclude_keywords = ["news"]

# --- SIDEBAR: SOURCE MANAGER ---
st.sidebar.title("🛠️ Source Manager")

with st.sidebar.expander("➕ Add New Source"):
    new_name = st.text_input("New Source Name")
    new_url = st.text_input("New RSS URL")
    if st.button("Add Source"):
        if new_name and new_url:
            st.session_state.my_feeds[new_name] = new_url
            st.rerun()

with st.sidebar.expander("📝 Edit / Remove Sources"):
    source_to_edit = st.selectbox("Select a source", options=[""] + list(st.session_state.my_feeds.keys()))
    if source_to_edit:
        new_label = st.text_input("Rename to:", value=source_to_edit)
        col1, col2 = st.columns(2)
        if col1.button("Save"):
            st.session_state.my_feeds[new_label] = st.session_state.my_feeds.pop(source_to_edit)
            st.rerun()
        if col2.button("🗑️ Delete"):
            del st.session_state.my_feeds[source_to_edit]
            st.rerun()

# --- SIDEBAR: ENHANCED CONTENT FILTERS ---
st.sidebar.markdown("---")
st.sidebar.title("🚫 Content Filters")

with st.sidebar.expander("➕ Add URL Exclusion"):
    excl_input = st.text_input("Word to block in URL (e.g., 'blog')")
    if st.button("Add Filter"):
        if excl_input and excl_input.lower() not in st.session_state.exclude_keywords:
            st.session_state.exclude_keywords.append(excl_input.lower())
            st.rerun()

# Management section for exclusions
if st.session_state.exclude_keywords:
    st.sidebar.write("**Currently Blocked:**")
    for word in st.session_state.exclude_keywords:
        col_text, col_btn = st.sidebar.columns([4, 1])
        col_text.write(f"`{word}`")
        # Unique key prevents button conflicts
        if col_btn.button("✖", key=f"del_{word}"):
            st.session_state.exclude_keywords.remove(word)
            st.rerun()
else:
    st.sidebar.write("_No active filters._")

# --- SIDEBAR: DISPLAY SETTINGS ---
st.sidebar.markdown("---")
st.sidebar.title("⚙️ Display Settings")
limit = st.sidebar.number_input("Max articles", min_value=1, max_value=500, value=20)
search_query = st.sidebar.text_input("🔍 Search keywords", "").lower()

selected_sources = st.sidebar.multiselect(
    "Active Sources", 
    options=list(st.session_state.my_feeds.keys()), 
    default=list(st.session_state.my_feeds.keys())
)

# --- FETCH & PROCESS ---
all_entries = []
with st.spinner('Syncing...'):
    for name, url in st.session_state.my_feeds.items():
        if name in selected_sources:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    # Logic to check URL against current exclusion list
                    is_excluded = any(excl in entry.link.lower() for excl in st.session_state.exclude_keywords)
                    
                    if not is_excluded:
                        entry['source_label'] = name
                        entry['detected_image'] = extract_image(entry)
                        all_entries.append(entry)
            except:
                st.sidebar.error(f"Error connecting to: {name}")

all_entries.sort(key=lambda x: parser.parse(x.get('published', 'Jan 1 1900')), reverse=True)
filtered = [e for e in all_entries if search_query in e.title.lower() or search_query in e.get('summary', '').lower()]
display_entries = filtered[:int(limit)]

# --- MAIN DISPLAY ---
st.title("🗂️ RSS Aggregator")
st.info(f"Showing **{len(display_entries)}** of {len(filtered)} total articles found.")

if