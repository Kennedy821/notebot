# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:43:24 2024

@author: worldcontroller
"""

import streamlit as st
from PIL import Image
import jwt  # To generate and decode tokens

# Loading Image using PIL



im = Image.open('slug_logo.png')
st.set_page_config(
    page_title="Hello",
    page_icon=im,
    initial_sidebar_state="collapsed",
    layout="wide"
)


SECRET_KEY = st.secrets["general"]["SECRET_KEY"]

# Decode and verify JWT token
def verify_token(token):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded_token
    except jwt.InvalidTokenError:
        return None


# Here is the new code to get the query parameters

query_params = st.query_params.get("token")

token = st.query_params.token

# Set token after login
st.session_state['token'] = token

if token:
    # decoded_token = verify_token(token)


# if 'token' in query_params:
#     token = query_params.get('token')[0]  # Get the token from the query
    decoded_token = verify_token(token)

    if decoded_token:
        user_email = str(decoded_token).split(":")[1].split("'")[1]
        
        st.success(f"Access granted! Welcome, {user_email}.")
        st.write(f"Your account: {user_email}")


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
    {"image": "slug_logo.png", "label": "Section 1", "url": f"https://notebot.streamlit.app/notebot_transcription_simple?token={token}"},
    {"image": "slug_logo.png", "label": "Section 2", "url": f"https://notebot.streamlit.app/notebot_generate_notes?token={token}"},
    {"image": "slug_logo.png", "label": "Section 3", "url": f"https://notebot.streamlit.app/notebot_study_multiselect?token={token}"},
]





# Display sections in three columns
cols = st.columns(3)

for idx, section in enumerate(sections):
    with cols[idx % 3]:  # Dynamically choose a column
        # Display the image
        st.image(section["image"], use_column_width=True, caption=section["label"])

        # Make the image clickable

        if st.button(f"Go to {section['label']}", key=f"btn_{idx}", use_container_width=True):
            # st.experimental_set_query_params(page=section["url"])

            redirect_url = f"{section["url"]}"
            st.markdown(f"""
            <meta http-equiv="refresh" content="0; url={redirect_url}">
            """, unsafe_allow_html=True)

        # internal_cols_1,internal_cols_2,internal_cols_3  = st.columns([1,6,1])
        # with internal_cols_1:
        #     pass
        # with internal_cols_2:
        #     if st.button(f"Go to {section['label']}", key=f"btn_{idx}", use_container_width=True):
        #         # st.experimental_set_query_params(page=section["url"])

        #         redirect_url = f"{section["url"]}"
        #         st.markdown(f"""
        #         <meta http-equiv="refresh" content="0; url={redirect_url}">
        #         """, unsafe_allow_html=True)
        # with internal_cols_3:
        #     pass