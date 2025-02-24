import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import numpy as np
import tempfile
import time
import fitz
import tempfile
from google.oauth2 import service_account
from google.cloud import storage
from PIL import Image
import jwt
import pandas as pd

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
    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)


    # The bucket on GCS in which to write the CSV file
    bucket = client.bucket(st.secrets["gcp_bucket"]["application_bucket"])

    
    #-----------------------------------------------------------------------------------------------------


    # next get the uploaded object ready to be uploaded by renaming it and giving it the correct filepath
    # what is the filetype of the uploaded file and filename 
    uploaded_file_type = file.name.split(".")[-1]
    uploaded_file_name = file.name.split(".")[0]

    # this makes sure that requests are segregated by each user
    user_directory = f'users/{user_hash}/'

    logging_filename = f"{uploaded_file_name}.pdf"
    full_file_path = f'{user_directory}{logging_filename}'

    # The name assigned to the CSV file on GCS
    blob = bucket.blob(full_file_path)
    # Upload the file
    blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
    print(f"File saved successfully in GCS bucket under '{logging_filename}'.")

def upload_csv_to_gcs(dataframe, bucket_name, blob_name):
    # Initialize the GCS client
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(bucket_name)
    
    # convert the dataframe to a csv
    csv_data = dataframe.to_csv(index=False)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(csv_data, content_type="csv")

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
def check_for_wav_file_in_gcs(blob_name):
    # Initialize the GCS client
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)


    # The bucket on GCS in which to write the CSV file
    bucket = client.bucket(st.secrets["gcp_bucket"]["application_bucket"])
    blob = bucket.blob(blob_name)
    if blob.exists():
        return True
    else:
        return False


# load the structure of the streamlit webpage
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
            upload_file_to_gcs(uploaded_file, st.secrets["gcp_bucket"]["application_bucket"], uploaded_file_name)
            
            # process the pdf 
            pdf_page_container = []

            # Read the content of the uploaded file
            pdf_content = uploaded_file.read()
            uploaded_file.seek(0)

            # Open the PDF from the content
            doc = fitz.open(pdf_content, filetype="pdf")

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text")
                pdf_page_container.append(text)

            # Close the document
            doc.close()

            # join the text from the pdf
            text = " ".join(pdf_page_container)

            # create a dataframe from the text
            dataframe = pd.DataFrame({"text": [text]})






            # upload the csv file to gcs
            uploaded_csv_name = f"users/{user_hash}/reader_uploaded_file.csv"
            upload_csv_to_gcs(dataframe, st.secrets["gcp_bucket"]["application_bucket"], uploaded_csv_name)
            
            
            # iteratively check if the mp3 file exists in the gcs bucket
            # Keep checking for the MP3 file every 10 seconds
            while not check_for_wav_file_in_gcs(f"users/{user_hash}/notebot_reader_uploaded_file.wav"):
                time.sleep(10)
                st.write("Waiting for audio file to be ready...")
            
            
            with tempfile.TemporaryDirectory() as temp_dir:
           
              # Once found, download the MP3 file
              local_wav_path = f"{temp_dir}/notebot_reader_uploaded_file.wav"
              download_mp3_file_from_gcs(
                  st.secrets["gcp_bucket"]["application_bucket"],
                  f"users/{user_hash}/notebot_reader_uploaded_file.wav",
                  local_wav_path
              )
              # Generate speech
              # output_wav_path = "reader_output.wav"

              st.audio(local_wav_path)