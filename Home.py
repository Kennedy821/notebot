# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:43:24 2024

@author: worldcontroller
"""

import streamlit as st
from PIL import Image
# Loading Image using PIL



im = Image.open('slug_logo.png')
st.set_page_config(
    page_title="Hello",
    page_icon=im,
    initial_sidebar_state="collapsed",
    layout="wide"
)

st.write(f"<h2 class='black-text'>  Welcome to Notebot - a simple notetaking app by Slug </h2>",unsafe_allow_html=True)

# st.sidebar.failure("Select a demo above.")

st.markdown(
    """
    <style>
    .black-text {
        color: #37474F;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """<p class="black-text">
Notebot is a simple and efficient note-taking app designed for everyone, from students to professionals. Capture, organize, and access your ideas with ease.
</p>
""",unsafe_allow_html=True
)

hide_default_format = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       </style>
       """
st.markdown(hide_default_format, unsafe_allow_html=True)

# Define the sections

sections = [
    {"image": "slug_logo.png", "label": "Section 1", "url": "https://notebot.streamlit.app/notebot_download_and_process_ydl"},
    {"image": "slug_logo.png", "label": "Section 2", "url": "https://notebot.streamlit.app/notebot_generate_notes"},
    {"image": "slug_logo.png", "label": "Section 3", "url": "https://notebot.streamlit.app/notebot_study_multiselect"},
]





# Display sections in three columns
cols = st.columns(3)

for idx, section in enumerate(sections):
    with cols[idx % 3]:  # Dynamically choose a column
        # Display the image
        st.image(section["image"], use_column_width=True, caption=section["label"])
        # Make the image clickable
        internal_cols_1,internal_cols_2,internal_cols_3  = st.columns([1,6,1])
        with internal_cols_1:
            pass
        with internal_cols_2:
            if st.button(f"Go to {section['label']}", key=f"btn_{idx}"):
                # st.experimental_set_query_params(page=section["url"])

                redirect_url = f"{section["url"]}"
                st.markdown(f"""
                <meta http-equiv="refresh" content="0; url={redirect_url}">
                """, unsafe_allow_html=True)
        with internal_cols_3:
            pass