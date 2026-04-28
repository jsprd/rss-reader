from feedgen.feed import FeedGenerator

# ... (Insert this after your filtered_entries logic) ...

st.sidebar.divider()
st.sidebar.subheader("Export Results")

if st.sidebar.button("Generate filtered_feed.xml"):
    fg = FeedGenerator()
    fg.title(f"Filtered Feed: {search_query}")
    fg.link(href="http://your-app-url.com", rel="self")
    fg.description(f"Combined RSS feed filtered by keyword: {search_query}")

    for entry in filtered_entries[:50]:
        fe = fg.add_entry()
        fe.title(entry.title)
        fe.link(href=entry.link)
        fe.description(entry.get('summary', 'No description available'))
        # Standardize the date for the XML file
        try:
            pub_date = parser.parse(entry.get('published', 'Jan 1 1900'))
            fe.pubDate(pub_date)
        except:
            pass

    # Convert the whole thing to an XML string
    rss_feed_xml = fg.rss_str(pretty=True)
    
    # Create the download button
    st.sidebar.download_button(
        label="📥 Download XML File",
        data=rss_feed_xml,
        file_name="filtered_feed.xml",
        mime="application/rss+xml"
    )