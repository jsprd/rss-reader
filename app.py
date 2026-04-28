import streamlit as st
import feedparser

# 1. Setup Page
st.set_page_config(page_title="RSS Web App", layout="wide")
st.title("🗞️ Real-Time RSS Reader")

# 2. Input Section
feed_url = st.text_input("Enter RSS Feed URL", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml")

if feed_url:
    # 3. Parse the Feed
    feed = feedparser.parse(feed_url)
    
    if not feed.entries:
        st.error("No entries found. Please check the URL.")
    else:
        # 4. Display the Items
        for entry in feed.entries:
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                
                # --- LOGIC: Pull Image ---
                img_url = None
                # Check media content (common in news feeds)
                if 'media_content' in entry:
                    img_url = entry.media_content[0]['url']
                # Check enclosure (common in podcasts/blogs)
                elif 'links' in entry:
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            img_url = link.get('href')
                
                with col1:
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.write("🖼️ No image provided")

                with col2:
                    # --- LOGIC: Title & Link ---
                    st.subheader(f"[{entry.title}]({entry.link})")
                    
                    # --- LOGIC: Publish Date ---
                    # feedparser standardizes most dates into 'published'
                    date = entry.get('published', 'Date unknown')
                    st.caption(f"🕒 {date}")
                    
                    # Optional: Summary/Description
                    if 'summary' in entry:
                        st.write(entry.summary[:250] + "...")

            st.write("") # Spacer