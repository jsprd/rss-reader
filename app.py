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

with st.sidebar.expander("➕ Add/Edit Sources"):
    new_name = st.text_input("Source Name")
    new_url = st.text_input("RSS URL")
    if st.button("Add to List"):
        if new_name and new_url:
            st.session_state.my_feeds[new_name] = new_url
            st.rerun()
    
    st.markdown("---")
    source_to_delete = st.selectbox("Remove a source", options=[""] + list(st.session_state.my_feeds.keys()))
    if st.button("Delete Selected") and source_to_delete:
        del st.session_state.my_feeds[source_to_delete]
        st.rerun()

# --- SIDEBAR: ADVANCED FILTERING ---
st.sidebar.markdown("---")
st.sidebar.title("🚫 Content Filters")
exclude_keywords = st.sidebar.text_input("Exclude URLs containing (comma separated)", "blog")

st.sidebar.markdown("---")
st.sidebar.title("🎨 Display")
view_mode = st.sidebar.radio("Layout", ["List", "Grid"])
limit = st.sidebar.slider("Article Limit", 5, 100, 20)

st.sidebar.title("🔍 Search")
search_query = st.sidebar.text_input("Search keywords", "").lower()

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
                    # --- NEW EXCLUSION LOGIC ---
                    # Checks if any exclude keyword is in the link URL
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
display_entries = filtered[:limit]

# --- SIDEBAR: EXPORT ---
st.sidebar.markdown("---")
if st.sidebar.button("📦 Build XML Feed"):
    fg = FeedGenerator()
    fg.title("Custom Exported Feed")
    fg.description("Filtered results with images")
    for entry in display_entries:
        fe = fg.add_entry()
        fe.title(entry.title)
        fe.link(href=entry.link)
        if entry.get('detected_image'):
            fe.enclosure(entry['detected_image'], '0', 'image/jpeg')
    rss_xml = fg.rss_str(pretty=True)
    st.sidebar.download_button("📥 Download XML", data=rss_xml, file_name="filtered_feed.xml")

# --- DISPLAY ENGINE ---
if not display_entries:
    st.info("No articles found matching filters.")

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
    rows = [display_entries[i:i+3] for i in range(0, len(display_entries), 3)]
    for row in rows:
        cols = st.columns(3)
        for i, entry in enumerate(row):
            with cols[i]:
                if entry['detected_image']:
                    st.image(entry['detected_image'], use_container_width=True)
                st.markdown(f"**[{entry.title}]({entry.link})**")
                st.caption(f"{entry.source_label} | {entry.get('published', 'N/A')[:16]}")
                st.markdown("---")