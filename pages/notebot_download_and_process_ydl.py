import whisper
import os
import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import tiktoken
import yt_dlp
from PIL import Image
from fuzzywuzzy import fuzz
import tempfile
from google.oauth2 import service_account
from google.cloud import storage

im = Image.open('slug_logo.png') # slug_logo.png is the image file in the same directory as the script
st.set_page_config(
    page_title="Hello",
    page_icon=im,
)


# the code below will be deleted as the transcription will be handled on the backend
# ----------------------------------------------------------------------------------

# load the whisper model
if 'model' not in st.session_state:
    # st.session_state.model = whisper.load_model("large")
    # st.session_state.model = whisper.load_model("medium")
    st.session_state.model = whisper.load_model("small")
else:
    model = st.session_state.model
# model = whisper.load_model("large")
# model = whisper.load_model("medium")
# model = whisper.load_model("small")

# load spatial sentences dataframe and convert to list

# ----------------------------------------------------------------------------------

# delete code block above once the backend is confirmed to be working


# Replace with your OpenAI API key
client = OpenAI(api_key=st.secrets["openai"]["OPEN_AI_KEY"])

# I'm making a random comment to make sure git is working 


st.title("Notebot: Process audio / video to text")

# Input interface
# st.subheader("Input Songs")

# song_link = st.text_input("Enter the YouTube link of the song or playlist:")
#generate_playlist = st.checkbox("Generate spectrograms for a playlist")


if 'messages' not in st.session_state:
    st.session_state['messages'] = []

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
    root_folder = "/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/notebot/"

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
        st.write(blob.name)

        topic_list.append(blob.name.split(".")[0].split("/")[-2])
    return topic_list

# # Example usage
# category = "Transcripts"  # Or "Detailed Notes", "High Level Notes"
# topic = "Topic 1"
# file_name = "transcript_topic1.txt"
# file_content = "This is the content of the transcript for Topic 1."

# # Save the file incrementally
# save_note(category, topic, file_name, file_content)

# Offer two options for the user either they can upload their own audio or they can use a link to a video
processing_type = st.selectbox("Would you like to upload your own audio file or use a link to a video?", options=["","upload my own audio","use a link from a website"],key='type_of_input')

if processing_type == "upload my own audio":
    uploaded_file = st.file_uploader("Choose a file", type=['mp3','wav','m4a','flac','aac','wma','ogg','opus','mp4','mkv','webm','mov','avi','wmv','flv','3gp','m4v','mpg','mpeg','m2v','m4v','mkv','flv','webm','vob','ogv','ogg','drc','gif','gifv','mng','avi','mov','qt','wmv','yuv','rm','rmvb','asf','amv','mp4','m4p','m4v','mpg','mp2','mpeg','mpe','mpv','mpg','mpeg','m2v','m4v','svi','3gp','3g2','mxf','roq','nsv','flv','f4v','f4p','f4a','f4b'])


if processing_type == "use a link from a website":

# with st.form(key='chat_form'):
    user_input = st.text_input("Enter the YouTube link of the song or playlist:", key='input')

# add an option for the user to be able to add a new topic or select from an existing topic

topic_selection_options = st.selectbox("Do you want your transcript to be in a new topic or an existing one?", options=["","New","Existing"])

if topic_selection_options == "New":

    topic_chosen = st.text_input("Add a new topic here")


elif topic_selection_options == "Existing":
    # check the existing directory of transcripts for this user:

    existing_topics_list = check_for_topics()
    existing_topics_list = [x for x in existing_topics_list if "." not in x]
    existing_topics_list = [""] + existing_topics_list

    topic_chosen = st.selectbox("Select which existing topic you'd like to add your transcript to", options=existing_topics_list)

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
        
        with st.spinner("Processing your transcription"):

            # this is the processing for uploading your own audio

            if processing_type == "upload my own audio":
                if uploaded_file is not None:
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
                        # Write the uploaded file content to the temporary file
                        temp_file.write(uploaded_file.getbuffer())
                        audio_path = temp_file.name  # Get the path to the temporary file
                    # audio_path = os.path.join(os.getcwd(), uploaded_file.name)
                    song_name = uploaded_file.name


                    st.session_state['messages'].append(('You', song_name))
                    st.markdown("beginning to process your link.")
                    bot_response = model.transcribe(audio_path, language="en")
                    bot_response = bot_response["text"]
                    st.session_state['messages'].append(('Bot', bot_response))

                    # this is the transcripts directory to save the file to 

                    category = "Transcripts"


                    save_note(category, topic_chosen, song_name, bot_response)


            # this is the processing for using a link from a website
            if processing_type == "use a link from a website":
                if user_input:
                    # load a yt link
                    yt_link = user_input
                    # temp_song_dir = '/'.join(os.getcwd().split("/")[:])

                    with tempfile.TemporaryDirectory() as temp_song_dir:



                        # yt = YouTube(yt_link)
                        url = yt_link
                        # st.markdown(yt_link)
                        song_directory = temp_song_dir
                        # Define the download options to extract audio
                        ydl_opts = {
                            'format': 'bestaudio/best',
                            'outtmpl': f'{song_directory}/%(title)s.%(ext)s',  # Save to 'downloads' folder with title as filename
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',  # You can also use 'wav'
                                'preferredquality': '192',
                            }],
                            'replace_in_metadata': [
                                                    ('title', r' \:', ''),
                                                    
                                                    ],

                            'restrictfilenames': True,  # Optional: further sanitize filenames

                        }

                        # url = 'https://www.youtube.com/watch?v=Xg618pb_hwQ'

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            # ydl.download([url])
                            info_dict = ydl.extract_info(url, download=True)
                            video_title = info_dict.get('title', None)
                            st.markdown(video_title)


                        st.markdown(f"Here is what is in the tempdir: {os.listdir(song_directory)}")

                        valid_file_name = []
                        for i in os.listdir(song_directory):
                            st.markdown(i)

                            ratio = fuzz.ratio(video_title, i)
                            if ratio>60:
                                valid_file_name.append(i)


                        st.markdown(f"here is the output of the fuzzy match: {valid_file_name}")
                        # Get the full path of the downloaded MP3 file
                        downloaded_file = os.path.join(temp_song_dir, f"{valid_file_name}.mp3")
                        audio_path = os.path.join(song_directory,valid_file_name[-1])
                        st.markdown(f"old filepath: {audio_path}")
                        st.markdown(f"new filepath: {downloaded_file}")
                        # audio_stream = yt.streams.filter(only_audio=True).first()
                        # audio_path = audio_stream.download(output_path=temp_song_dir)
                        # st.markdown(audio_path)
                        # song_name = audio_path.title().split("/")[-1].split(".")[0]
                        # mp3_song_name = yt.title.replace('.mp4','.mp3').replace('.Mp4','.mp3').replace('.MP4','.mp3').replace("|","")
                        # this is the working version
                        # song_file_directory = os.getcwd()
                        song_name = video_title
                        
                        song_file_directory = temp_song_dir

                        list_of_items_in_temp_dir = [x for x in os.listdir(song_file_directory)]

                        # result = model.transcribe(song_file_directory)

                        st.session_state['messages'].append(('You', user_input))
                        st.markdown("beginning to process your link.")
                        bot_response = model.transcribe(audio_path, language="en")
                        bot_response = bot_response["text"]
                        st.session_state['messages'].append(('Bot', bot_response))

                        # this is the transcripts directory to save the file to 

                        category = "Transcripts"


                        save_note(category, topic_chosen, song_name, bot_response)



                        st.success("Successfully processed your transcript!")


                        # # save this bot response in the same location as the audio_path
                        # test_lecture_df = pd.DataFrame([bot_response]).rename(columns={0:"lecture_notes"})
                        # test_lecture_df.to_parquet(f"{song_file_directory}/{song_name}_text_from_notebot_part_1.parquet.gzip", compression="gzip")


for sender, message in st.session_state['messages']:
    st.write(f"**{sender}:** {message}")