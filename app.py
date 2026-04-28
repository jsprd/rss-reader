import streamlit as st
import feedparser
from dateutil import parser
from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup

st.set_page_config(page_title="RSS Aggregator", layout="wide")

def extract_image(entry):
    # 1. Standard Media Content
    if 'media_content' in entry and entry.media_content:
        return entry.media_content[0]['url']
    # 2. Thumbnail tags
    if 'media_thumbnail' in entry and entry.media_thumbnail:
        return entry.media_thumbnail[0]['url']
    # 3. Links with image type
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', '') or 'image' in link.get('rel', ''):
                return link.get('href')
    # 4. Enclosures
    if 'enclosures' in entry:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                return enc.get('href')
    # 5. BeautifulSoup fallback
    content = entry.get('summary', '') or entry.get('description', '')
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            src = img_tag.get('src')
            if src.startswith('http'):
                return src
    return None

# --- SESSION STATE ---
if 'my_feeds' not in st.session_state:
    st.session_state.my_feeds = {
        "Pressroom RSS": "https://press.asus.com/rss.xml/",
        "EdgeUp RSS": "https://edgeup.asus.com/feed/"
    }

if 'exclude_keywords' not in st.session_state:
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

# --- SIDEBAR: CONTENT FILTERS ---
st.sidebar.markdown("---")
st.sidebar.title("🚫 Content Filters")
with st.sidebar.expander("➕ Add URL Exclusion"):
    excl_input = st.text_input("Block keyword")
    if st.button("Add Filter"):
        if excl_input:
            st.session_state.exclude_keywords.append(excl_input.lower())
            st.rerun()

if st.session_state.exclude_keywords:
    for word in st.session_state.exclude_keywords:
        c_text, c_btn = st.sidebar.columns([4, 1])
        c_text.write(f"`{word}`")
        if c_btn.button("✖", key=f"del_{word}"):
            st.session_state.exclude_keywords.remove(word)
            st.rerun()

# --- SIDEBAR: SETTINGS ---
st.sidebar.markdown("---")
st.sidebar.title("⚙️ Settings")
per_source_limit = st.sidebar.number_input("Pull per source", 1, 100, 10)
global_limit = st.sidebar.number_input("Max display", 1, 500, 20)
search_query = st.sidebar.text_input("🔍 Search", "").lower()

selected_sources = st.sidebar.multiselect(
    "Sources", options=list(st.session_state.my_feeds.keys()), default=list(st.session_state.my_feeds.keys())
)

# --- FETCH & FILTER ---
all_entries = []
fetch_buffer = 150

with st.spinner('Syncing...'):
    for name, url in st.session_state.my_feeds.items():
        if name in selected_sources:
            try:
                feed = feedparser.parse(url)
                source_count = 0
                for entry in feed.entries[:fetch_buffer]:
                    if source_count >= per_source_limit:
                        break
                    
                    is_excluded = any(excl in entry.link.lower() for excl in st.session_state.exclude_keywords)
                    if not is_excluded:
                        entry['source_label'] = name
                        entry['detected_image'] = extract_image(entry)
                        all_entries.append(entry)
                        source_count += 1
            except:
                st.sidebar.error(f"Error: {name}")

all_entries.sort(key=lambda x: parser.parse(x.get('published', 'Jan 1 1900')), reverse=True)
filtered = [e for e in all_entries if search_query in e.title.lower() or search_query in e.get('summary', '').lower()]
display_entries = filtered[:int(global_limit)]

# --- MAIN DISPLAY ---
st.title("🗂️ RSS Aggregator")
st.info(f"Showing **{len(display_entries)}** of {len(filtered)} total articles found.")

for entry in display_entries:
    with st.container():
        c1, c2 = st.columns([1, 4])
        with c1:
            if entry['detected_image']:
                st.image(entry['detected_image'], use_container_width=True)
            else:
                st.write("🖼️ No Image")
        with c2:
            st.markdown(f"### [{entry.title}]({entry.link})")
            st.caption(f"**{entry.source_label}** | {entry.get('published', 'N/A')}")
            raw_content = entry.get('summary', '') or entry.get('description', '')
            clean_summary = BeautifulSoup(raw_content, "html.parser").get_text()
            st.write(clean_summary[:250] + "...")
        st.markdown("---")

# --- SIDEBAR: EXPORT ---
st.sidebar.markdown("---")
st.sidebar.subheader("Export Results")

if display_entries:
    try:
        fg = FeedGenerator()
        fg.title("Custom News Feed")
        fg.link(href="https://share.streamlit.io", rel="self")
        fg.description("Latest articles first")
        
        # Add entries in reverse order so newest is at the top of the XML
        for entry in reversed(display_entries):
            fe = fg.add_entry()
            fe.title(entry.title)
            fe.link(href=entry.link)
            
            img_url = entry.get('detected_image')
            raw_c = entry.get('summary', '') or entry.get('description', '')
            clean_t = BeautifulSoup(raw_c, "html.parser").get_text()
            
            if img_url:
                # Fixed the truncated line here
                fe.description(f'<img src="{img_url}" style="width:100%;"><br>{clean_t}')
                fe.enclosure(img_url, '0', 'image/jpeg')
            else:
                fe.description(clean_t)
            
            try:
                fe.pubDate(parser.parse(entry.get('published')))
            except:
                pass
        
        rss_data = fg.rss_str(pretty=True)
        st.sidebar.download_button(
            label="📥 Download XML Feed",
            data=rss_data,
            file_name="news_export.xml",
            mime="application/rss+xml"
        )
    except Exception as e:
        st.sidebar.error(f"Export Error: {str(e)}")
else:
    st.sidebar.warning("No articles to export.")