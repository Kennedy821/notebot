import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import time
# from gtts import gTTS
import collections
import threading
import queue
import base64
from pydub import AudioSegment
from TTS.api import TTS
import fitz  # PyMuPDF
import tempfile
from google.oauth2 import service_account
from google.cloud import storage
from PIL import Image
import jwt


im = Image.open('slug_logo.png')
st.set_page_config(
    page_title="Hello",
    page_icon=im,
)

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

user_hash = token




# make a function that can upload a file to gcs
def upload_file_to_gcs(file, bucket_name, blob_name):
    # Initialize the GCS client
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = storage.Client(credentials=credentials)

    # Get the bucket
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    # Upload from the file object instead of filename
    blob.upload_from_file(file)
    print(f"File saved successfully in GCS bucket '{bucket_name}' under '{blob_name}'.")


# download an mp3 file from gcs
def download_mp3_file_from_gcs(bucket_name, blob_name, file_path):
    # Initialize the GCS client
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(file_path)
    print(f"File '{file_path}' downloaded successfully from GCS bucket '{bucket_name}' under '{blob_name}'.")

# define a function that will periodically check for the mp3 file in the gcs bucket
def check_for_wav_file_in_gcs(bucket_name, blob_name):
    # Initialize the GCS client
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if blob.exists():
        return True
    else:
        return False


# load the structure of the streamlit webpage
st.set_page_config(page_title="Reader", page_icon=":material/volume_up:", layout="wide")
st.title("Reader")

# display a file uploader widget for pdf files
uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

# add a button that says "generate audio"
if st.button("Generate Audio"):
    with st.spinner("Generating audio..."):
        # check if a file has been uploaded
        if uploaded_file is not None:
            

            # upload the pdf file to gcs
            # make the filename to upload
            uploaded_file_name = f"users/{user_hash}/reader_uploaded_file.pdf"
            upload_file_to_gcs(uploaded_file, st.secrets["gcp_service_account"]["bucket_name"], uploaded_file_name)
            # iteratively check if the mp3 file exists in the gcs bucket
            # Keep checking for the MP3 file every 10 seconds
            while not check_for_wav_file_in_gcs("pdf_files", "notebot_reader_uploaded_file.mp3"):
                time.sleep(10)
                st.write("Waiting for audio file to be ready...")
            
            
            with tempfile.TemporaryDirectory() as temp_dir:
           
              # Once found, download the MP3 file
              download_mp3_file_from_gcs("pdf_files", "notebot_reader_uploaded_file.wav", "notebot_reader_uploaded_file.wav")

              # Generate speech
              output_wav_path = "reader_output.wav"

              st.audio(output_wav_path)