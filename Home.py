# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:43:24 2024

@author: worldcontroller
"""

import streamlit as st
from PIL import Image
# Loading Image using PIL



im = Image.open('/Users/tariromashongamhende/Downloads/slug_logo.png')
st.set_page_config(
    page_title="Hello",
    page_icon=im,
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