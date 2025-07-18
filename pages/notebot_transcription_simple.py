#import whisper
import os
import streamlit as st
import pandas as pd
# from openai import OpenAI
import os
import tiktoken
# import yt_dlp
from PIL import Image
from fuzzywuzzy import fuzz
import tempfile
from google.oauth2 import service_account
from google.cloud import storage
import jwt
import time

def get_transcription_from_gcs(user_hash):

    start_time = time.time()
    
    
    while True:



        #download the indices from gcs
        blob = bucket.blob(f"users/{user_hash}/transcription_successful.csv")
        if blob.exists():

            # Download the file to a destination
            blob.download_to_filename(temp_dir+"transcription_successful.csv")
            downloaded_indices_df = pd.read_csv(temp_dir+"transcription_successful.csv")
            # st.dataframe(downloaded_indices_df)
            break
        else:
            time.sleep(10)
    end_time = time.time()
    st.write(f"Time taken to get recommendations is: {end_time-start_time}")
    return downloaded_indices_df

im = Image.open('slug_logo.png') # slug_logo.png is the image file in the same directory as the script
st.set_page_config(
    page_title="Hello",
    page_icon=im,
    initial_sidebar_state="collapsed"

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




# the code below will be deleted as the transcription will be handled on the backend
# ----------------------------------------------------------------------------------

# load the whisper model
# if 'model' not in st.session_state:
#     # st.session_state.model = whisper.load_model("large")
#     # st.session_state.model = whisper.load_model("medium")
#     # st.session_state.model = whisper.load_model("small")
# else:
#     model = st.session_state.model
# model = whisper.load_model("large")
# model = whisper.load_model("medium")
# model = whisper.load_model("small")

# load spatial sentences dataframe and convert to list

# ----------------------------------------------------------------------------------

# delete code block above once the backend is confirmed to be working


# Replace with your OpenAI API key
# client = OpenAI(api_key=st.secrets["openai"]["OPEN_AI_KEY"])

# I'm making a random comment to make sure git is working 


st.title("Notebot: Transcription")

# Input interface
# st.subheader("Input Songs")

# song_link = st.text_input("Enter the YouTube link of the song or playlist:")
#generate_playlist = st.checkbox("Generate spectrograms for a playlist")


if 'messages' not in st.session_state:
    st.session_state['messages'] = []

if 'files_uploaded' not in st.session_state:
    st.session_state.files_uploaded = False

def delete_csv_file(file_name, bucket_name=st.secrets["notebot"]["bucket_name"]):
    """
    Delete a file from Google Cloud Storage bucket.
    
    Args:
        file_name (str): Path to the file in the bucket
        bucket_name (str): Name of the bucket (defaults to notebot bucket)
    """
    try:
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

        # Use the credentials to create a client
        client = storage.Client(credentials=credentials)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        # Check if blob exists before trying to delete
        if blob.exists():
            blob.delete()
            print(f"File {file_name} deleted from bucket {bucket_name}")
        else:
            print(f"File {file_name} not found in bucket {bucket_name}")
            
    except Exception as e:
        print(f"Error deleting file: {e}")

def check_status_of_fast_processing():
    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)

    # Get the bucket
    bucket = client.bucket(st.secrets["notebot"]["bucket_name"])

    # create a dataframe that has one column to check if thhe fast job is active
    fast_job_df = pd.DataFrame([user_hash])
    # add the user hash to the dataframe
    fast_job_df.columns = ["user_hash"] 

    blob = bucket.blob(f"status_files/is_fast_job_active.csv")
    
    csv_string = fast_job_df.to_csv(index=False)
    blob.upload_from_string(csv_string)

    time.sleep(20)

    # check if the new response file exists in gcs 
    FILE_SUFFIX = "fast_job_status_verified.csv"

    prefix = "status_files/"
    matching_blobs = []
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith(FILE_SUFFIX):

            matching_blobs.append(blob.name)
    
    if len(matching_blobs)>0:
        return 1
    else:
        return 0

def flatten(nested_list):
    """
    Flatten a list of lists.

    Parameters:
    nested_list (list): A list of lists to be flattened.

    Returns:
    list: A single, flattened list.
    """
    return [item for sublist in nested_list for item in sublist]

def encode_sentences(sentences, model):
    return model(sentences)

def generate_combined_prompt_final(user_prompt, input_context): 
    intro_block_phrase = ["You have been asked the following:"]
    
    data_intro_phrase = ["You are a helping someone make notes from a lecture and your goal is to identify key concepts provided to you and use the idea of chunking mentioned by Cal Newport. Your goal is to standardise the format of the notes you've been provided to be able to make them logically structured and easy to understand for someone to be able to learn a complicated topic. Convert the chunks the following format: question, answer, and evidence. Provide some further reading at the end of the evidence section by suggesting likely papers and further reading where relevant"]
    # data_context = location_intelligence_sentences_list[:4000]
    data_context = input_context
    print(f"number of sentences is : {len(data_context)}")
    model_archetype = ["When giving your answer try to be as plain speaking words as possible and imagine you are speaking to a 10 year old. Your user has some understanding of the field but don't take any prior knowledge for granted, so be clear and avoid using jargon in your response. Speak in the tone of the 3Blue1Brown youtube channel."]
    prompt_given_by_user = [user_prompt]
    system_role_context = str(flatten([data_intro_phrase,data_context,model_archetype])).replace(",",".").replace("[","").replace("]","")
    
    return user_prompt,system_role_context

def generate_combined_prompt_iterative(user_prompt, lower_bound_value, upper_bound_value): 
    
    intro_block_phrase = ["You have been asked the following:"]
    
    data_intro_phrase = ["You are a helping someone make notes from a lecture and your goal is to identify key concepts provided to you and use the idea of chunking mentioned by Cal Newport to be able to make the lecture logically structured and easy to understand for someone to be able to learn a complicated topic. Convert the chunks the following format: question, answer, and evidence. In the evidence section suggest likely papers and further reading where relevant"]
    # data_context = location_intelligence_sentences_list[:4000]
    data_context = test_lecture_df.lecture_notes[0][lower_bound_value:upper_bound_value]
    print(f"number of sentences is : {len(data_context)}")
    model_archetype = ["When giving your answer try to be as plain speaking words as possible and imagine you are speaking to a 10 year old. Your user has some understanding of the field but don't take any prior knowledge for granted, so be clear and avoid using jargon in your response. Speak in the tone of the 3Blue1Brown youtube channel."]
    prompt_given_by_user = [user_prompt]
    system_role_context = str(flatten([data_intro_phrase,data_context,model_archetype])).replace(",",".").replace("[","").replace("]","")
    
    return user_prompt,system_role_context

def get_gpt4_response(prompt, lower_string_chunk_value, upper_string_chunk_value):
    """
    Send a prompt to the OpenAI API to get a response from GPT-4.

    Parameters:
    prompt (str): The prompt to send to GPT-4.

    Returns:
    str: The response from GPT-4.
    """

    chosen_model = "gpt-4o"
    
    # user_prompt, system_role_prompt = generate_combined_prompt(prompt)
    user_prompt, system_role_prompt = generate_combined_prompt_iterative(prompt,lower_string_chunk_value,upper_string_chunk_value)


    # Load the tokenizer
    tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(text):
        tokens = tokenizer.encode(text)
        return len(tokens)

    num_tokens = count_tokens(system_role_prompt)
    print(f"Number of system role tokens: {num_tokens}")
    
    response = client.chat.completions.create(
      model=chosen_model,
      messages=[
        {"role": "system", "content": f"""{system_role_prompt}"""},
        {"role": "user", "content": user_prompt}
      ]
    )
    return response.choices[0].message.content

def get_gpt4_response_final(prompt, initial_string_notes_context):
    """
    Send a prompt to the OpenAI API to get a response from GPT-4.

    Parameters:
    prompt (str): The prompt to send to GPT-4.

    Returns:
    str: The response from GPT-4.
    """

    chosen_model = "gpt-4o"
    
    user_prompt, system_role_prompt = generate_combined_prompt_final(prompt,initial_string_notes_context)


    # Load the tokenizer
    tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(text):
        tokens = tokenizer.encode(text)
        return len(tokens)

    num_tokens = count_tokens(system_role_prompt)
    print(f"Number of system role tokens: {num_tokens}")
    
    response = client.chat.completions.create(
      model=chosen_model,
      messages=[
        {"role": "system", "content": f"""{system_role_prompt}"""},
        {"role": "user", "content": user_prompt}
      ]
    )
    return response.choices[0].message.content


import os

def save_note(category, topic, file_name, file_content):
    """
    Save a note in the appropriate category and topic folder.

    Args:
    category (str): The category to save the note under (e.g., 'Transcripts').
    topic (str): The topic to save the note under.
    file_name (str): The name of the file to be saved.
    file_content (str): The content to be written in the file.
    """

    # Define the root folder
    root_folder = "/Users/tariromashongamhende/Documents/Documents - Tariro's MacBook Pro/ml_projects/notebot/"

    # Create the category folder if it doesn't exist
    category_path = os.path.join(root_folder, category)
    os.makedirs(category_path, exist_ok=True)

    # Create the topic folder if it doesn't exist
    topic_folder = os.path.join(category_path, topic)
    os.makedirs(topic_folder, exist_ok=True)

    # Define the full file path (without extension for now)
    file_path = os.path.join(topic_folder, file_name)

    # Save this bot response as a Parquet file with .gzip compression
    transcript_df = pd.DataFrame([file_content], columns=["lecture_notes"])
    
    # Add .parquet.gzip extension to the file path
    parquet_file_path = f"{file_path}_transcript.parquet.gzip"
    
    # Save the Parquet file
    transcript_df.to_parquet(parquet_file_path, compression="gzip")

    print(f"File '{file_name}' saved successfully in '{topic_folder}' as a Parquet file.")

def save_note_cloud_version(category, topic, file_name, file_content, bucket_name):
    """
    Save a note in the appropriate category and topic folder in GCS.

    Args:
    category (str): The category to save the note under (e.g., 'Transcripts').
    topic (str): The topic to save the note under.
    file_name (str): The name of the file to be saved (without extension).
    file_content (str): The content to be written in the file.
    bucket_name (str): The name of the GCS bucket.
    """
    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)

    # Get the bucket
    bucket = client.bucket(bucket_name)

    # Define the file path in the bucket
    gcs_file_path = f"{category}/{topic}/{file_name}_transcript.parquet.gzip"

    try:
        # Convert the file content to a DataFrame
        transcript_df = pd.DataFrame([file_content], columns=["lecture_notes"])

        # Save the DataFrame to a Parquet file in memory
        parquet_buffer = io.BytesIO()
        transcript_df.to_parquet(parquet_buffer, compression="gzip")
        parquet_buffer.seek(0)

        # Upload the file to GCS
        blob = bucket.blob(gcs_file_path)
        blob.upload_from_file(parquet_buffer, content_type="application/octet-stream")

        print(f"File '{file_name}' saved successfully in GCS bucket '{bucket_name}' under '{gcs_file_path}'.")
    except Exception as e:
        print(f"An error occurred while saving the file: {e}")


#function to check for the topics the user has created 
def check_for_topics():
    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)

    # Specify your bucket name
    bucket_name = st.secrets["notebot"]["bucket_name"]

    # Get the bucket object
    bucket = client.bucket(bucket_name)

    # List all blobs in the 'users/' directory
    blobs = client.list_blobs(bucket_name, prefix='Transcripts/')

    # Initialize an empty list to store DataFrames
    topic_list = []

    # Temporary directory for storing downloaded files (optional)
    # temp_dir = "/tmp/"  # If needed

    # Iterate over all blobs in the 'users/' directory
    for blob in blobs:
        topic_name = blob.name.split(".")[0].split("/")[-2]
        if topic_name != "Transcripts":
            topic_list.append(topic_name)
    return topic_list

# # Example usage
# category = "Transcripts"  # Or "Detailed Notes", "High Level Notes"
# topic = "Topic 1"
# file_name = "transcript_topic1.txt"
# file_content = "This is the content of the transcript for Topic 1."

# # Save the file incrementally
# save_note(category, topic, file_name, file_content)

# Offer two options for the user either they can upload their own audio or they can use a link to a video
processing_type = st.selectbox("Would you like to upload your own audio file(s)?", options=["","upload my own audio",
                                                                                                                #   "use a link from a website"
                                                                                                                  ])

if processing_type == "upload my own audio":


    upload_type = st.selectbox("Would you like to upload a single file or many files?", options=["","bulk"])

    if upload_type=="single file":
        uploaded_file = st.file_uploader("Choose a file", type=['mp3'], accept_multiple_files=False)
    elif upload_type=="bulk":
        uploaded_files = st.file_uploader("Choose a file", type=['mp3'], accept_multiple_files=True)
        for uploaded_file in uploaded_files:
            if uploaded_file is not None:
                # st.write(uploaded_file.name)
                pass


# if processing_type == "use a link from a website":

# # with st.form(key='chat_form'):
#     user_input = st.text_input("Enter the YouTube link of the song or playlist:", key='input')

# add an option for the user to be able to add a new topic or select from an existing topic

# topic_selection_options = st.selectbox("Do you want your transcript to be in a new topic or an existing one?", options=["","New","Existing"])

# if topic_selection_options == "New":

#     topic_chosen = st.text_input("Add a new topic here")


# elif topic_selection_options == "Existing":
#     # check the existing directory of transcripts for this user:

#     existing_topics_list = check_for_topics()
#     existing_topics_list = [x for x in existing_topics_list if "." not in x]
#     existing_topics_list = [""] + existing_topics_list

#     topic_chosen = st.selectbox("Select which existing topic you'd like to add your transcript to", options=existing_topics_list)

# this is the old working code that is being deprecated
# |
# |
# v

# elif topic_selection_options == "Existing":
#     # check the existing directory of transcripts for this user:
#     topic_list_filepath = os.getcwd()+'/Transcripts/'
#     existing_topics_list = os.listdir(topic_list_filepath)
#     existing_topics_list = [x for x in existing_topics_list if "." not in x]
#     existing_topics_list = [""] + existing_topics_list

#     topic_chosen = st.selectbox("Select which existing topic you'd like to add your transcript to", options=existing_topics_list)


# if len(topic_chosen)>4:


completed_status = False

# Define the CSS for the dark brown button
submit_button = """
<style>
div.stButton > button {
    background-color: #3F301D;  /* Dark brown color */
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
}

div.stButton > button:hover {
    background-color: #4e3623;  /* Darker shade for hover effect */
}
</style>
"""

# Inject the CSS into the Streamlit app
st.markdown(submit_button, unsafe_allow_html=True)

submit_button = st.button(label='Send')

if submit_button:
        
    with st.spinner("Processing your transcription", show_time=True):
        # try:
        fast_job_status = check_status_of_fast_processing()

        if fast_job_status == 1:
            # st.success("Fast job is active, please wait for the job to complete")
            fast_job_status_code = 1
        else:
            # st.success("Fast job is not active, please wait for the job to complete")
            fast_job_status_code = 0
        # except Exception as e:
        #     st.write(f"An error occurred while checking the status of the fast job: {e}")

        # now we know the status of the fast job we can delete the checking file from the bucket
        try:
            delete_csv_file(f"status_files/is_fast_job_active.csv")
        except Exception as e:
            print(f"Error while deleting status file: {e}")

        
        try:



            # delete any previous transcriptions for this user
            # The bucket on GCS in which to write the CSV file
            bucket_name = st.secrets["gcp_bucket"]["application_bucket"]

            def delete_csv_file(bucket_name, file_name):
                # Create credentials object
                credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

                # Use the credentials to create a client
                client = storage.Client(credentials=credentials)




                bucket = client.bucket(bucket_name)
                blob = bucket.blob(file_name)
                blob.delete()

            try:
                delete_csv_file(bucket_name,f"users/{user_hash}/transcription_successful.csv")
            except Exception as e:
                print(f"{e} file does not exist proceeding to upload new file")
        except Exception as ne:
            print(f"{ne} - the folder does not exist proceeding to upload new file")


        time.sleep(3)

        

        # this is the processing for uploading your own audio

        if processing_type == "upload my own audio":
            if upload_type=="single file" and uploaded_file is not None:

                # check the file is a valid file type

                
                if processing_type=="upload my own audio" and uploaded_file:

                    # Validate file type (basic validation)
                    if uploaded_file.type != "audio/mpeg":
                        st.error("Invalid file type. Please upload a valid MP3 file.")
                        # st.stop()
                    else:

                        # get the details for where the uploaded file is going to go
                        #-----------------------------------------------------------------------------------------------------

                        # Create credentials object
                        credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

                        # Use the credentials to create a client
                        client = storage.Client(credentials=credentials)


                        # The bucket on GCS in which to write the CSV file
                        bucket = client.bucket(st.secrets["gcp_bucket"]["application_bucket"])

                        
                        #-----------------------------------------------------------------------------------------------------


                        # next get the uploaded object ready to be uploaded by renaming it and giving it the correct filepath
                        # what is the filetype of the uploaded file and filename 
                        uploaded_file_type = uploaded_file.name.split(".")[-1]
                        uploaded_file_name_list = uploaded_file.name.split(".")[:-1]
                        uploaded_file_name = " ".join(uploaded_file_name_list)

                        # this makes sure that requests are segregated by each user
                        user_directory = f'users/{user_hash}/'

                        logging_filename = f"{uploaded_file_name}_single_file_notebot_transcription.mp3"
                        full_file_path = f'{user_directory}{logging_filename}'

                        # The name assigned to the CSV file on GCS
                        blob = bucket.blob(full_file_path)
                        # Upload the file
                        blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)



                        # now you need to check in the users bucket for the transcribed file


                        st.success("Successfully uploaded your audio file!")
                        
                        # add in a timing delay to make sure that the file is uploaded before the next step
                        time.sleep(20)



                        with tempfile.TemporaryDirectory() as temp_dir:

                            results_df = get_transcription_from_gcs(user_hash)

                            # convert string to downloadable csv from streamlit with download button
                            csv = results_df.to_csv(index=False)
                            st.download_button(
                                label="Download Fast Job Transcription",
                                data=csv,
                                file_name=f"{uploaded_file_name}.csv",
                                mime="text/csv",
                            )
                            # st.stop()


# ----------------------------------------------------------------------------------
# this section of the code now allows or bulk uploads to the backend
# ----------------------------------------------------------------------------------

            if upload_type=="bulk" and uploaded_files is not None and completed_status == False:

                # check the files in the uploaded files are a valid file type
                for object in uploaded_files:
                    if object.type != "audio/mpeg":
                        st.error("Invalid file type. Please upload a valid MP3 file.")
                        # st.stop()
                    else:
                        pass
                        



                # get the details for where the uploaded file is going to go
                #-----------------------------------------------------------------------------------------------------

                # Create credentials object
                credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

                # Use the credentials to create a client
                client = storage.Client(credentials=credentials)


                # The bucket on GCS in which to write the CSV file
                bucket = client.bucket(st.secrets["gcp_bucket"]["application_bucket"])

                
                #-----------------------------------------------------------------------------------------------------

                # for each of the uploaded files, upload them to the backend
                number_of_files = len(uploaded_files)-1
                # st.write(f"number of files: {number_of_files}")

                # we're adding a split flow for active fast job status and non active fast job status
                if fast_job_status_code == 1:
                    for object_num in range(len(uploaded_files)):
                        if object_num != number_of_files:
                            uploaded_file = uploaded_files[object_num]
                            # st.write(f"this is not the last file: {uploaded_file}")

                            # next get the uploaded object ready to be uploaded by renaming it and giving it the correct filepath
                            # what is the filetype of the uploaded file and filename 
                            uploaded_file_type = uploaded_file.name.split(".")[-1]
                            uploaded_file_name_list = uploaded_file.name.split(".")[:-1]
                            uploaded_file_name = " ".join(uploaded_file_name_list)
                            # this makes sure that requests are segregated by each user
                            user_directory = f'users/{user_hash}/'

                            logging_filename = f"{uploaded_file_name}_bulk_upload_object_{object_num}_notebot_transcription_fast_job_active.mp3"
                            full_file_path = f'{user_directory}{logging_filename}'

                            # The name assigned to the CSV file on GCS
                            blob = bucket.blob(full_file_path)
                            # Upload the file
                            uploaded_file.seek(0)

                            blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
                        # for the last file in the list we will flag that it is the final file as this will be the last file to be uploaded
                        else:

                            uploaded_file = uploaded_files[object_num]
                            # st.write(f"this is the last file: {uploaded_file}")

                            # next get the uploaded object ready to be uploaded by renaming it and giving it the correct filepath
                            # what is the filetype of the uploaded file and filename 
                            uploaded_file_type = uploaded_file.name.split(".")[-1]
                            uploaded_file_name_list = uploaded_file.name.split(".")[:-1]
                            uploaded_file_name = " ".join(uploaded_file_name_list)
                            # this makes sure that requests are segregated by each user
                            user_directory = f'users/{user_hash}/'

                            logging_filename = f"{uploaded_file_name}_bulk_upload_object_{object_num}_final_notebot_transcription_fast_job_active.mp3"
                            full_file_path = f'{user_directory}{logging_filename}'

                            # The name assigned to the CSV file on GCS
                            blob = bucket.blob(full_file_path)
                            # Upload the file
                            uploaded_file.seek(0)
                            blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)




                    # if len(uploaded_files)<5:
                    #     st.success(f"Successfully uploaded your audio file for fast job {uploaded_file_name}.")
                    # else:
                    #     pass
                    
                    # add in a timing delay to make sure that the file is uploaded before the next step
                    st.success("Successfully uploaded your file(s)")
                    # pass

                
                    # st.session_state.files_uploaded = True
                    # st.stop()  # Stop execution here after upload

                    with tempfile.TemporaryDirectory() as temp_dir:

                        results_df = get_transcription_from_gcs(user_hash)

                        # convert string to downloadable csv from streamlit with download button
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            label="Download Transcription",
                            data=csv,
                            file_name=f"bulk_transcription_job.csv",
                            mime="text/csv",
                            key="fast_job_download"
                        )
                        completed_status = True

                        st.success("Successfully processed your bulk audio files!")
                    # st.stop()

                elif fast_job_status_code == 0:
                    for object_num in range(len(uploaded_files)):
                        if object_num != number_of_files:
                            uploaded_file = uploaded_files[object_num]
                            # st.write(f"this is not the last file: {uploaded_file}")

                            # next get the uploaded object ready to be uploaded by renaming it and giving it the correct filepath
                            # what is the filetype of the uploaded file and filename 
                            uploaded_file_type = uploaded_file.name.split(".")[-1]
                            uploaded_file_name_list = uploaded_file.name.split(".")[:-1]
                            uploaded_file_name = " ".join(uploaded_file_name_list)
                            # this makes sure that requests are segregated by each user
                            user_directory = f'users/{user_hash}/'

                            logging_filename = f"{uploaded_file_name}_bulk_upload_object_{object_num}_notebot_transcription.mp3"
                            full_file_path = f'{user_directory}{logging_filename}'

                            # The name assigned to the CSV file on GCS
                            blob = bucket.blob(full_file_path)
                            # Upload the file
                            uploaded_file.seek(0)

                            blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
                        # for the last file in the list we will flag that it is the final file as this will be the last file to be uploaded
                        else:

                            uploaded_file = uploaded_files[object_num]
                            # st.write(f"this is the last file: {uploaded_file}")

                            # next get the uploaded object ready to be uploaded by renaming it and giving it the correct filepath
                            # what is the filetype of the uploaded file and filename 
                            uploaded_file_type = uploaded_file.name.split(".")[-1]
                            uploaded_file_name_list = uploaded_file.name.split(".")[:-1]
                            uploaded_file_name = " ".join(uploaded_file_name_list)
                            # this makes sure that requests are segregated by each user
                            user_directory = f'users/{user_hash}/'

                            logging_filename = f"{uploaded_file_name}_bulk_upload_object_{object_num}_final_notebot_transcription.mp3"
                            full_file_path = f'{user_directory}{logging_filename}'

                            # The name assigned to the CSV file on GCS
                            blob = bucket.blob(full_file_path)
                            # Upload the file
                            uploaded_file.seek(0)
                            blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)




                    # if len(uploaded_files)<5:
                    #     st.success(f"Successfully uploaded your audio file {uploaded_file_name}.")
                    # else:
                    #     pass
                    
                    # add in a timing delay to make sure that the file is uploaded before the next step
                    time.sleep(2)

                    st.success("Successfully uploaded your file(s)")

                    # pass
                    st.session_state.files_uploaded = True
                    # st.stop()  # Stop execution here after upload

                    with tempfile.TemporaryDirectory() as temp_dir:

                        results_df = get_transcription_from_gcs(user_hash)

                        # convert string to downloadable csv from streamlit with download button
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            label="Download Transcription",
                            data=csv,
                            file_name=f"bulk_transcription_job.csv",
                            mime="text/csv",
                            key="regular_job_download"
                        )
                        completed_status = True

                        st.success("Successfully processed your bulk audio files!")
st.stop()

# st.stop()


                    # # Create a temporary file
                    # with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
                    #     # Write the uploaded file content to the temporary file
                    #     temp_file.write(uploaded_file.getbuffer())
                    #     audio_path = temp_file.name  # Get the path to the temporary file
                    # # audio_path = os.path.join(os.getcwd(), uploaded_file.name)
                    # song_name = uploaded_file.name


                    # st.session_state['messages'].append(('You', song_name))
                    # st.markdown("beginning to process your link.")
                    # bot_response = model.transcribe(audio_path, language="en")
                    # bot_response = bot_response["text"]
                    # st.session_state['messages'].append(('Bot', bot_response))

                    # # this is the transcripts directory to save the file to 

                    # category = "Transcripts"


                    # save_note_cloud_version(category, topic_chosen, song_name, bot_response)



                    # st.success("Successfully processed your transcript!")


                    # # save this bot response in the same location as the audio_path
                    # test_lecture_df = pd.DataFrame([bot_response]).rename(columns={0:"lecture_notes"})
                    # test_lecture_df.to_parquet(f"{song_file_directory}/{song_name}_text_from_notebot_part_1.parquet.gzip", compression="gzip")


# for sender, message in st.session_state['messages']:
#     st.write(f"**{sender}:** {message}")