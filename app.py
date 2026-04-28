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
    new_name = st.text_input("New Source Name")
    new_url = st.text_input("New RSS URL")
    if st.button("Add to List"):
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

# --- SIDEBAR: FILTERS & SETTINGS ---
st.sidebar.markdown("---")
st.sidebar.title("🚫 Content Filters")
exclude_keywords = st.sidebar.text_input("Exclude URLs (e.g. blog, news)", "blog")

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

all_entries.sort(key=lambda x: parser.parse(x.get('published', 'Jan 1 1900')), reverse=True)
filtered = [e for e in all_entries if search_query in e.title.lower() or search_query in e.get('summary', '').lower()]
display_entries = filtered[:int(limit)]

# --- MAIN DISPLAY ---
st.title("🗂️ Universal News Aggregator")
st.info(f"Showing **{len(display_entries)}** of {len(filtered)} total articles found.")

for entry in display_entries:
    with st.container():
        c1, c2 = st.columns([1, 4])
        with c1:
            if entry['detected_image']:
                st.image(entry['detected_image'], use_container_width=True)
        with c2:
            st.markdown(f"### [{entry.title}]({entry.link})")
            st.caption(f"**{entry.source_label}** | {entry.get('published', 'N/A')}")
            clean_summary = BeautifulSoup(entry.get('summary', '') or entry.get('description', ''), "html.parser").get_text()
            st.write(clean_summary[:250] + "...")
        st.markdown("---")

# --- SIDEBAR: EXPORT (WITH IMAGE FIX) ---
st.sidebar.markdown("---")
st.sidebar.subheader("Export Results")
if st.sidebar.button("📦 Build XML Feed"):
    fg = FeedGenerator()
    fg.title("Custom News Feed")
    fg.link(href="https://share.streamlit.io", rel="self")
    fg.description("Exported feed with images and keyword filters")

    for entry in display_entries:
        fe = fg.add_entry()
        fe.title(entry.title)
        fe.link(href=entry.link)
        
        # 1. Clean the summary text
        raw_summary = entry.get('summary', '') or entry.get('description', '')
        clean_text = BeautifulSoup(raw_summary, "html.parser").get_text()
        
        # 2. IMAGE FIX: Inject <img> into description AND use enclosure
        img_url = entry.get('detected_image')
        if img_url:
            # Most readers prioritize <img> tags inside the description
            rich_description = f'<img src="{img_url}" style="width:100%; max-width:600px;"><br>{clean_text}'
            fe.description(rich_description)
            # Some readers (like Feedly/Outlook) prioritize the enclosure
            fe.enclosure(img_url, '0', 'image/jpeg')
        else:
            fe.description(clean_text)
        
        try:
            fe.pubDate(parser.parse(entry.get('published')))
        except:
            pass
            
    rss_xml = fg.rss_str(pretty=True)
    st.sidebar.download_button(
        label="📥 Download XML File",
        data=rss_xml,
        file_name="news_export.xml",
        mime="application/rss+xml"
    )