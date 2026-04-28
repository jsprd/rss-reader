import streamlit as st
import feedparser
from dateutil import parser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup

st.set_page_config(page_title="Custom News Curator", layout="wide")

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

# --- SIDEBAR: SOURCE MANAGER ---
st.sidebar.title("🛠️ Source Manager")

if 'my_feeds' not in st.session_state:
    st.session_state.my_feeds = {
        "Pressroom RSS": "https://press.asus.com/rss.xml/",
        "EdgeUp RSS": "https://edgeup.asus.com/feed/"
    }

# 1. Add New Source
with st.sidebar.expander("➕ Add New Source"):
    new_name = st.text_input("New Source Name")
    new_url = st.text_input("New RSS URL")
    if st.button("Add to List"):
        if new_name and new_url:
            st.session_state.my_feeds[new_name] = new_url
            st.rerun()

# 2. Rename or Delete Existing Sources
with st.sidebar.expander("📝 Edit / Remove Sources"):
    source_to_edit = st.selectbox("Select a source to modify", options=[""] + list(st.session_state.my_feeds.keys()))
    
    if source_to_edit:
        current_url = st.session_state.my_feeds[source_to_edit]
        new_label = st.text_input("Rename to:", value=source_to_edit)
        
        col1, col2 = st.columns(2)
        if col1.button("Save Changes"):
            # Swap the key in the dictionary
            st.session_state.my_feeds[new_label] = st.session_state.my_feeds.pop(source_to_edit)
            st.rerun()
            
        if col2.button("🗑️ Delete"):
            del st.session_state.my_feeds[source_to_edit]
            st.rerun()

# --- SIDEBAR: ADVANCED FILTERING ---
st.sidebar.markdown("---")
st.sidebar.title("🚫 Content Filters")
exclude_keywords = st.sidebar.text_input("Exclude URLs containing (comma separated)", "blog")

st.sidebar.markdown("---")
st.sidebar.title("⚙️ Display Settings")
# Manual numeric input for article limit
limit = st.sidebar.number_input("Max articles to show", min_value=1, max_value=500, value=20, step=1)

search_query = st.sidebar.text_input("🔍 Search keywords", "").lower()

selected_sources = st.sidebar.multiselect(
    "Active Sources", 
    options=list(st.session_state.my_feeds.keys()), 
    default=list(st.session_state.my_feeds.keys())
)

st.title("🗂️ Universal News Aggregator")

# --- FETCH & COMBINE ---
all_entries = []
exclude_list = [x.strip().lower() for x in exclude_keywords.split(",") if x.strip()]

with st.spinner('Syncing...'):
    for name, url in st.session_state.my_feeds.items():
        if name in selected_sources:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    is_excluded = any(excl in entry.link.lower() for excl in exclude_list)
                    if not is_excluded:
                        entry['source_label'] = name
                        entry['detected_image'] = extract_image(entry)
                        all_entries.append(entry)
            except:
                st.sidebar.error(f"Error: {name}")

# Sort and Limit
all_entries.sort(key=lambda x: parser.parse(x.get('published', 'Jan 1 1900')), reverse=True)
filtered = [
    e for e in all_entries 
    if (search_query in e.title.lower() or search_query in e.get('summary', '').lower())
]
display_entries = filtered[:int(limit)]

# --- MAIN DISPLAY ENGINE ---
# Restore the article counter
st.info(f"Showing **{len(display_entries)}** of {len(filtered)} total articles found.")

if not display_entries:
    st.warning("No articles found matching your filters.")

for entry in display_entries:
    with st.container():
        col1, col2 = st.columns([1, 4])
        with col1:
            if entry['detected_image']:
                st.image(entry['detected_image'], use_container_width=True)
        with col2:
            st.markdown(f"### [{entry.title}]({entry.link})")
            st.caption(f"**{entry.source_label}** | {entry.get('published', 'N/A')}")
            
            summary = entry.get('summary', '') or entry.get