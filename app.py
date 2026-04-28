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

with st.sidebar.expander("➕ Add New Source"):
    new_name = st.text_input("Source Name")
    new_url = st.text_input("RSS URL")
    if st.button("Add to List"):
        if new_name and new_url:
            st.session_state.my_feeds[new_name] = new_url
            st.rerun()

# --- SIDEBAR: DISPLAY SETTINGS ---
st.sidebar.markdown("---")
st.sidebar.title("🎨 Display Settings")

view_mode = st.sidebar.radio("Layout View", ["List", "Grid"])
limit = st.sidebar.slider("Number of articles to pull", 5, 100, 20)

st.sidebar.markdown("---")
st.sidebar.title("🔍 Search")
search_query = st.sidebar.text_input("Search keywords", "").lower()

selected_sources = st.sidebar.multiselect(
    "Filter View", 
    options=list(st.session_state.my_feeds.keys()), 
    default=list(st.session_state.my_feeds.keys())
)

st.title("🗂️ Universal News Aggregator")

# --- FETCH & COMBINE ---
all_entries = []
with st.spinner('Syncing...'):
    for name, url in st.session_state.my_feeds.items():
        if name in selected_sources:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
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
display_entries = filtered[:limit]

# --- SIDEBAR: EXPORT XML ---
st.sidebar.markdown("---")
if st.sidebar.button("📦 Build XML Feed"):
    fg = FeedGenerator()
    fg.title("Custom Exported Feed")
    fg.description("Articles with embedded images")
    for entry in display_entries:
        fe = fg.add_entry()
        fe.title(entry.title)
        fe.link(href=entry.link)
        if entry.get('detected_image'):
            fe.enclosure(entry['detected_image'], '0', 'image/jpeg')
    
    rss_xml = fg.rss_str(pretty=True)
    st.sidebar.download_button("📥 Download XML", data=rss_xml, file_name="feed.xml")

# --- MAIN DISPLAY ENGINE ---
st.write(f"Showing **{len(display_entries)}** articles.")

if not display_entries:
    st.info("No articles found.")

elif view_mode == "List":
    for entry in display_entries:
        with st.container():
            col1, col2 = st.columns([1, 4])
            with col1:
                if entry['detected_image']:
                    st.image(entry['detected_image'], use_container_width=True)
            with col2:
                st.markdown(f"### [{entry.title}]({entry.link})")
                st.caption(f"**{entry.source_label}** | {entry.get('published', 'N/A')}")
                clean_text = BeautifulSoup(entry.get('summary', '') or entry.get('description', ''), "html.parser").get_text()
                st.write(clean_text[:250] + "...")
            st.markdown("---")

else: # Grid View
    cols = st.columns(3) # 3 columns per row
    for i, entry in enumerate(display_entries):
        with cols[i % 3]:
            if entry['detected_image']:
                st.image(entry['detected_image'], use_container_width=True)
            st.markdown(f"**[{entry.title}]({entry.link})**")
            st.caption(f"{entry.source_label}")
            st.markdown("---")