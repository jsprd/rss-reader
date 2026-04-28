import streamlit as st
import feedparser
from dateutil import parser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup

st.set_page_config(page_title="Custom RSS Curator", layout="wide")

def extract_image(entry):
    """Detects images in official tags OR inside the HTML description."""
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

# Initialize session state for feeds if it doesn't exist
if 'my_feeds' not in st.session_state:
    st.session_state.my_feeds = {
        "Press Feed": "https://press.asus.com/rss.xml/",
        "Blog Feed": "https://edgeup.asus.com/feed/"
    }

# Function to add new source
with st.sidebar.expander("➕ Add New Source"):
    new_name = st.text_input("Source Name (e.g. Tech News)")
    new_url = st.text_input("RSS URL")
    if st.button("Add to List"):
        if new_name and new_url:
            st.session_state.my_feeds[new_name] = new_url
            st.rerun()

# Function to remove sources
with st.sidebar.expander("🗑️ Remove Source"):
    source_to_delete = st.selectbox("Select to remove", options=list(st.session_state.my_feeds.keys()))
    if st.button("Delete Selected"):
        del st.session_state.my_feeds[source_to_delete]
        st.rerun()

# --- SIDEBAR: FILTER ---
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
                    # Pre-calculate image for display and export
                    entry['detected_image'] = extract_image(entry)
                    all_entries.append(entry)
            except:
                st.sidebar.error(f"Error: {name}")

# Sort by Date
all_entries.sort(key=lambda x: parser.parse(x.get('published', 'Jan 1 1900')), reverse=True)

# Filter Logic
filtered = [
    e for e in all_entries 
    if (search_query in e.title.lower() or search_query in e.get('summary', '').lower())
]

# --- SIDEBAR: EXPORT XML (With Images) ---
st.sidebar.markdown("---")
st.sidebar.subheader("Export Results")

if st.sidebar.button("📦 Build XML with Images"):
    fg = FeedGenerator()
    fg.title("Custom Filtered Feed")
    fg.link(href="https://share.streamlit.io", rel="self")
    fg.description("Exported articles with images")

    for entry in filtered[:50]:
        fe = fg.add_entry()
        fe.title(entry.title)
        fe.link(href=entry.link)
        
        # Clean HTML from description
        clean_desc = BeautifulSoup(entry.get('summary', ''), "html.parser").get_text()
        fe.description(clean_desc[:500])
        
        # INCLUDE IMAGE IN EXPORT (Enclosure tag)
        if entry.get('detected_image'):
            # Enclosure needs: URL, length (0 is fine), and MIME type
            fe.enclosure(entry['detected_image'], '0', 'image/jpeg')
        
        try:
            fe.pubDate(parser.parse(entry.get('published')))
        except:
            pass
            
    rss_xml = fg.rss_str(pretty=True)
    st.sidebar.download_button(
        label="📥 Download XML",
        data=rss_xml,
        file_name="custom_feed.xml",
        mime="application/rss+xml"
    )

# --- MAIN DISPLAY ---
st.write(f"Showing **{len(filtered)}** articles from **{len(selected_sources)}** sources.")

for entry in filtered[:40]:
    with st.container():
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if entry['detected_image']:
                st.image(entry['detected_image'], use_container_width=True)
            else:
                st.info("No Image")

        with col2:
            st.markdown(f"### [{entry.title}]({entry.link})")
            st.caption(f"**{entry.source_label}** | {entry.get('published', 'N/A')}")
            
            summary = entry.get('summary', '') or entry.get('description', '')
            clean_summary = BeautifulSoup(summary, "html.parser").get_text()
            st.write(clean_summary[:250] + "...")
        st.markdown("---")