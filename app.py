import streamlit as st
import feedparser
from dateutil import parser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup

st.set_page_config(page_title="Asus News Curator", layout="wide")

def extract_image(entry):
    """Finds images in official tags or deep inside HTML description."""
    # 1. Check official media content
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    
    # 2. Check for enclosures (Common in Asus Press XML)
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''):
                return link.get('href')
    
    # 3. Deep dive into HTML description
    content = entry.get('summary', '') or entry.get('description', '')
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            return img_tag.get('src')
    return None

# --- SIDEBAR: Filter & Management ---
st.sidebar.title("🔍 Search & Filter")
search_query = st.sidebar.text_input("Search Asus articles", "").lower()

# Updated Feed URLs
feed_urls = {
    "Asus Press": "https://press.asus.com/rss.xml/",
    "Asus Edge Up": "https://edgeup.asus.com/feed/"
}

selected_sources = st.sidebar.multiselect(
    "Filter by Source", 
    options=list(feed_urls.keys()), 
    default=list(feed_urls.keys())
)

st.title("💻 Asus News Aggregator")

all_entries = []

# --- FETCH & COMBINE ---
with st.spinner('Syncing Asus Feeds...'):
    for name, url in feed_urls.items():
        if name in selected_sources:
            try:
                # We add a user-agent header because some servers block basic python requests
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    entry['source_name'] = name
                    all_entries.append(entry)
            except:
                st.sidebar.error(f"Failed to reach: {name}")

# --- SORT BY DATE ---
all_entries.sort(key=lambda x: parser.parse(x.get('published', 'Jan 1 1900')), reverse=True)

# --- FILTER LOGIC ---
filtered = [
    e for e in all_entries 
    if (search_query in e.title.lower() or search_query in e.get('summary', '').lower())
]

# --- SIDEBAR: EXPORT XML ---
st.sidebar.markdown("---")
st.sidebar.subheader("Export Filtered Feed")

if st.sidebar.button("📦 Build XML Feed"):
    fg = FeedGenerator()
    fg.title("Filtered Asus News")
    fg.link(href="https://your-app.streamlit.app", rel="self")
    fg.description(f"Articles matching: {search_query if search_query else 'All'}")

    for entry in filtered[:50]:
        fe = fg.add_entry()
        fe.title(entry.title)
        fe.link(href=entry.link)
        clean_text = BeautifulSoup(entry.get('summary', ''), "html.parser").get_text()
        fe.description(clean_text[:500])
        try:
            fe.pubDate(parser.parse(entry.get('published')))
        except:
            pass
            
    rss_xml = fg.rss_str(pretty=True)
    
    st.sidebar.download_button(
        label="📥 Download XML",
        data=rss_xml,
        file_name="asus_filtered.xml",
        mime="application/rss+xml"
    )

# --- MAIN DISPLAY ---
st.write(f"Displaying **{len(filtered)}** articles from Asus.")

for entry in filtered[:40]:
    with st.container():
        col1, col2 = st.columns([1, 4])
        img_url = extract_image(entry)
        
        with col1:
            if img_url:
                st.image(img_url, use_container_width=True)
            else:
                st.info("No Image")

        with col2:
            st.markdown(f"### [{entry.title}]({entry.link})")
            st.caption(f"**{entry.source_name}** | {entry.get('published', 'N/A')}")
            
            # Show summary without HTML tags
            summary = entry.get('summary', '') or entry.get('description', '')
            clean_summary = BeautifulSoup(summary, "html.parser").get_text()
            st.write(clean_summary[:250] + "...")
        
        st.markdown("---")