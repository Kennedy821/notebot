import whisper
import os
from pytube import YouTube, Playlist
import streamlit as st
import openai
# import tensorflow as tf
# import tensorflow_hub as hub
import pandas as pd
# import geopandas as gp
# import h3
import openai
# from shapely.geometry import Polygon
from openai import OpenAI
import os
import tiktoken
# import moviepy.editor as mp
import re
import random
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import markdown2
import textwrap
from PIL import Image
from fuzzywuzzy import fuzz
from google.oauth2 import service_account
from google.cloud import storage
import jwt
import time
import tempfile
from bs4 import BeautifulSoup

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

# load the whisper model
# model = whisper.load_model("large")
# model = whisper.load_model("small")

# load spatial sentences dataframe and convert to list



# Replace with your OpenAI API key
client = OpenAI(api_key=st.secrets["openai"]["OPEN_AI_KEY"])


st.write("<h1 class='black-text'> Notebot: Generate Notes</h1>",unsafe_allow_html=True)

# Input interface
# st.subheader("Input Songs")

# song_link = st.text_input("Enter the YouTube link of the song or playlist:")
#generate_playlist = st.checkbox("Generate spectrograms for a playlist")


if 'messages' not in st.session_state:
    st.session_state['messages'] = []

def sanitize_html_2(html_text):
    # Remove <para> and </para> tags
    cleaned_text = re.sub(r'</?para>', '', html_text)
    
    # Ensure all <em> tags are properly closed
    cleaned_text = re.sub(r'<em>(.*?)</para>', r'<em>\1</em>', cleaned_text)
    
    return cleaned_text

def create_pdf(html_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []

    # Convert HTML to ReportLab Paragraphs
    for line in html_text.split('\n'):
        if line.strip():
            story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer

def create_pdf(html_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )
    styles = getSampleStyleSheet()
    story = []

    # Sanitize the HTML input
    cleaned_text = sanitize_html(html_text)

    # Convert HTML to ReportLab Paragraphs
    for line in cleaned_text.split('\n'):
        if line.strip():
            try:
                story.append(Paragraph(line, styles['Normal']))
                story.append(Spacer(1, 12))
            except ValueError as e:
                print(f"Error processing line: {line}")
                print(e)

    doc.build(story)
    buffer.seek(0)
    return buffer

# def create_pdf(text):
#     buffer = io.BytesIO()
#     c = canvas.Canvas(buffer, pagesize=letter)
#     width, height = letter
#     margin = 1 * inch
#     max_width = width - 2 * margin
#     lines = textwrap.wrap(text, width=95)

#     y = height - margin
#     for line in lines:
#         if y <= margin:
#             c.showPage()
#             y = height - margin
#         c.drawString(margin, y, line)
#         y -= 14  # Move down by 14 points for the next line

#     c.save()
#     buffer.seek(0)
#     return buffer

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

def add_newline_before_bold(text):
    # Regular expression to find bold text (denoted by **)
    bold_pattern = re.compile(r'(\*\*[^*]+\*\*)')

    # Function to add newline before each bold text
    def add_newline(match):
        return '\n' + match.group(0)

    # Substitute each bold text with newline + bold text
    result = re.sub(bold_pattern, add_newline, text)
    
    return result


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

def generate_combined_prompt_hidden(user_prompt, input_string): 
    intro_block_phrase = ["You have been asked the following:"]
    
    data_intro_phrase = ["Your goal is to maintain as much information and coherence as possible and return notes summaries of 20000 characters. Use the idea of chunking mentioned by Cal Newport"]
    # data_context = location_intelligence_sentences_list[:4000]
    data_context = [input_string]
    print(f"number of sentences is : {len(data_context)}")
    model_archetype = ["When giving your answer try to be as plain speaking words as possible and imagine you are speaking to a 10 year old. Your user has some understanding of the field but don't take any prior knowledge for granted, so be clear and avoid using jargon in your response. Speak in the tone of the 3Blue1Brown youtube channel."]
    prompt_given_by_user = [user_prompt]
    system_role_context = str(flatten([data_intro_phrase,data_context,model_archetype])).replace(",",".").replace("[","").replace("]","")
    
    return user_prompt,system_role_context

def generate_combined_prompt_final(user_prompt, input_context): 
    intro_block_phrase = ["You have been asked the following:"]
    
    data_intro_phrase = ["You are a helping someone make notes from a lecture and your goal is to identify key concepts provided to you and use the idea of chunking mentioned by Cal Newport. Your goal is to standardise the format of the notes you've been provided to be able to make them logically structured and easy to understand for someone to be able to learn a complicated topic. Convert the chunks the following format: question, answer, evidence and conclusion. Provide some further reading at the end of the evidence section by suggesting likely papers and further reading where relevant. Make sure question is on it's a new line, answer is as well and so on. Also don't tell the reader that you're using chunking or Cal Newport's approach. Also don't reduce the word count too much from the input and write back approx 20000 characters. Make sure further reading is on its own line and in bullet points at the end of your response."]
    # data_context = location_intelligence_sentences_list[:4000]
    data_context = input_context
    print(f"number of sentences is : {len(data_context)}")

    model_archetype = ["When giving your answer try to be as plain speaking words as possible and discuss concepts step by step. Your user has some understanding of the field but don't take any prior knowledge for granted, so be clear and avoid using jargon in your response. Speak in the tone of the 3Blue1Brown youtube channel."]

    # model_archetype = ["When giving your answer try to be as plain speaking words as possible and imagine you are speaking to a 10 year old. Your user has some understanding of the field but don't take any prior knowledge for granted, so be clear and avoid using jargon in your response. Speak in the tone of the 3Blue1Brown youtube channel."]
    prompt_given_by_user = [user_prompt]
    system_role_context = str(flatten([data_intro_phrase,data_context,model_archetype])).replace(",",".").replace("[","").replace("]","")
    
    return user_prompt,system_role_context

def generate_combined_prompt_iterative(user_prompt, input_string,lower_bound_value, upper_bound_value): 
    
    intro_block_phrase = ["You have been asked the following:"]
    
    data_intro_phrase = ["You are a helping someone make notes from a lecture and your goal is to identify key concepts provided to you and use the idea of chunking mentioned by Cal Newport to be able to make the lecture logically structured and easy to understand for someone to be able to learn a complicated topic. Convert the chunks the following format: question, answer, and evidence. In the evidence section suggest likely papers and further reading where relevant"]
    # data_context = location_intelligence_sentences_list[:4000]
    data_context = [input_string[lower_bound_value:upper_bound_value]]
    print(f"number of sentences is : {len(data_context)}")
    model_archetype = ["When giving your answer try to be as plain speaking words as possible and discuss concepts step by step. Your user has some understanding of the field but don't take any prior knowledge for granted, so be clear and avoid using jargon in your response. Speak in the tone of the 3Blue1Brown youtube channel."]

    # model_archetype = ["When giving your answer try to be as plain speaking words as possible and imagine you are speaking to a 10 year old. Your user has some understanding of the field but don't take any prior knowledge for granted, so be clear and avoid using jargon in your response. Speak in the tone of the 3Blue1Brown youtube channel."]
    prompt_given_by_user = [user_prompt]
    system_role_context = str(flatten([data_intro_phrase,data_context,model_archetype])).replace(",",".").replace("[","").replace("]","")
    
    return user_prompt,system_role_context

def get_gpt4_response(prompt, input_string, lower_string_chunk_value, upper_string_chunk_value):
    """
    Send a prompt to the OpenAI API to get a response from GPT-4.

    Parameters:
    prompt (str): The prompt to send to GPT-4.

    Returns:
    str: The response from GPT-4.
    """

    chosen_model = "gpt-4o"
    # chosen_model = "gpt-4o-2024-08-06"
    # chosen_model = "gpt-4o-mini"
    
    # user_prompt, system_role_prompt = generate_combined_prompt(prompt)
    user_prompt, system_role_prompt = generate_combined_prompt_iterative(prompt,input_string,lower_string_chunk_value,upper_string_chunk_value)


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

    chosen_model = "gpt-4o-mini"
    
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

def get_gpt4_response_hidden(prompt, input_string):
    """
    Send a prompt to the OpenAI API to get a response from GPT-4.

    Parameters:
    prompt (str): The prompt to send to GPT-4.

    Returns:
    str: The response from GPT-4.
    """

    chosen_model = "gpt-4o"
    
    # user_prompt, system_role_prompt = generate_combined_prompt(prompt)
    user_prompt, system_role_prompt = generate_combined_prompt_hidden(prompt,input_string)


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

def get_random_chunks(s, chunk_size=40000, num_chunks=3):
    chunks = []
    
    if len(s) < chunk_size:
        raise ValueError("The string is too short to extract the desired chunk size.")
    
    while len(chunks) < num_chunks:
        start_idx = random.randint(0, len(s) - chunk_size)
        chunk = s[start_idx:start_idx + chunk_size]
        chunks.append(chunk)
    
    return chunks


def sanitize_html(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')
    return str(soup)



def save_detailed_notes(category, topic, file_name, file_content):
    """
    Save detailed notes in the appropriate category and topic folder as a PDF.

    Args:
    category (str): The category to save the note under (e.g., 'Transcripts').
    topic (str): The topic to save the note under.
    file_name (str): The name of the file to be saved.
    file_content (str): The content to be written in the PDF (HTML text).
    """
    
    # Define the root folder
    root_folder = "/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/notebot/"

    # Create the category folder if it doesn't exist
    category_path = os.path.join(root_folder, category)
    os.makedirs(category_path, exist_ok=True)

    # Create the topic folder if it doesn't exist
    topic_folder = os.path.join(category_path, topic)
    os.makedirs(topic_folder, exist_ok=True)

    # Define the full file path for the PDF
    pdf_file_path = os.path.join(topic_folder, f"{file_name}_detailed_notes.pdf")

    st.markdown(f"your detailed notes have the location: {pdf_file_path}")

    # Create the PDF from the HTML content
    pdf_buffer = create_pdf(file_content)

    # Save the PDF to the specified file path
    with open(pdf_file_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())

    print(f"File '{pdf_file_path}' saved successfully as a PDF.")

def save_summary_notes(category, topic, file_name, file_content):
    """
    Save detailed notes in the appropriate category and topic folder as a PDF.

    Args:
    category (str): The category to save the note under (e.g., 'Transcripts').
    topic (str): The topic to save the note under.
    file_name (str): The name of the file to be saved.
    file_content (str): The content to be written in the PDF (HTML text).
    """
    
    # Define the root folder
    root_folder = "/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/notebot/"

    # Create the category folder if it doesn't exist
    category_path = os.path.join(root_folder, category)
    os.makedirs(category_path, exist_ok=True)

    # Create the topic folder if it doesn't exist
    topic_folder = os.path.join(category_path, topic)
    os.makedirs(topic_folder, exist_ok=True)

    # Define the full file path for the PDF
    pdf_file_path = os.path.join(topic_folder, f"{file_name}_summary_notes.pdf")

    # Create the PDF from the HTML content
    pdf_buffer = create_pdf(file_content)

    # Save the PDF to the specified file path
    with open(pdf_file_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())

    print(f"File '{pdf_file_path}' saved successfully as a PDF.")


def save_transcript(category, topic, file_name, file_content):
    """
    Save detailed notes in the appropriate category and topic folder as a PDF.

    Args:
    category (str): The category to save the note under (e.g., 'Transcripts').
    topic (str): The topic to save the note under.
    file_name (str): The name of the file to be saved.
    file_content (str): The content to be written in the PDF (HTML text).
    """
    
    # Define the root folder
    root_folder = "/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/notebot/"

    # Create the category folder if it doesn't exist
    category_path = os.path.join(root_folder, category)
    os.makedirs(category_path, exist_ok=True)

    # Create the topic folder if it doesn't exist
    topic_folder = os.path.join(category_path, topic)
    os.makedirs(topic_folder, exist_ok=True)

    # Define the full file path for the PDF
    pdf_file_path = os.path.join(topic_folder, f"{file_name.replace('_transcript','')}_transcript.pdf")

    # Create the PDF from the HTML content
    pdf_buffer = create_pdf(file_content)

    # Save the PDF to the specified file path
    with open(pdf_file_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())

    print(f"File '{pdf_file_path}' saved successfully as a PDF.")


def get_most_similar_fuzz_ratio_of_file_in_directory(input_name, song_directory):
    fuzz_df_chunk_container = []
    for directory_filename in os.listdir(song_directory):
        # st.markdown(f"{input_name},'|',{directory_filename}")
        try:

            ratio = fuzz.ratio(input_name, directory_filename)
            # st.markdown(ratio)
            int_df = pd.DataFrame([input_name])
            int_df.columns = ["clean_name"]
            # int_df["clean_name"] = input_name
            int_df["file_in_dir"] = directory_filename
            int_df["fuzz_ratio_score"] = ratio
            # st.dataframe(int_df)
            fuzz_df_chunk_container.append(int_df)
        except Exception as e:
            pass
        
    fuzz_comp_df = pd.concat(fuzz_df_chunk_container, ignore_index=True).sort_values("fuzz_ratio_score", ascending=False).head(1)
    # file_to_open = fuzz_comp_df.sort_values("fuzz_ratio_score", ascending=False).head(1).file_in_dir.values[0]
    return fuzz_comp_df.fuzz_ratio_score.values[0]



# Function to upload a file to GCS
def upload_pdf_to_gcs(bucket_name, source_file, destination_blob_name):
    """
    Uploads a file to the Google Cloud Storage bucket.

    Args:
        bucket_name (str): Name of the GCS bucket.
        source_file (file-like object): The uploaded PDF file from the user.
        destination_blob_name (str): The name to save the file as in the bucket.
    """
    # Initialize the GCS client

    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)

    # Specify your bucket name
    bucket_name = st.secrets["notebot"]["bucket_name"]
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    # Upload the file
    blob.upload_from_file(source_file, content_type='application/pdf')

    print(f"File uploaded to GCS bucket {bucket_name} as {destination_blob_name}")


def get_detailed_notes_from_gcs(user_hash):

    # Initialize the GCS client

    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)

    # Specify your bucket name
    bucket_name = st.secrets["notebot"]["bucket_name"]
    bucket = client.bucket(bucket_name)

    start_time = time.time()
    
    
    while True:



        #download the indices from gcs
        blob = bucket.blob(f"users/{user_hash}/detailed_notes.csv")
        if blob.exists():

            # Download the file to a destination
            blob.download_to_filename(temp_dir+"detailed_notes.csv")
            detailed_notes_df = pd.read_csv(temp_dir+"detailed_notes.csv")
            detailed_notes_string = detailed_notes_df.iloc[0,0]
            break
        else:
            time.sleep(10)
    end_time = time.time()

    return detailed_notes_string


def get_summary_notes_from_gcs(user_hash):

    # Initialize the GCS client

    # Create credentials object
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    # Use the credentials to create a client
    client = storage.Client(credentials=credentials)

    # Specify your bucket name
    bucket_name = st.secrets["notebot"]["bucket_name"]
    bucket = client.bucket(bucket_name)

    start_time = time.time()
    
    
    while True:



        #download the indices from gcs
        blob = bucket.blob(f"users/{user_hash}/summary_notes.csv")
        if blob.exists():

            # Download the file to a destination
            blob.download_to_filename(temp_dir+"summary_notes.csv")
            summary_notes_df = pd.read_csv(temp_dir+"summary_notes.csv")
            summary_notes_string = summary_notes_df.iloc[0,0]
            break
        else:
            time.sleep(10)
    end_time = time.time()

    return summary_notes_string













# with st.form(key='chat_form'):
st.write("Upload the file you would like to generate notes for:")


# Define the CSS for the file uploader
file_uploader_css = """
<style>
div.stFileUploader label {
    color: #654321;  /* Dark brown color for text */
    background-color: #f5efd6;  /* Background color */
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 16px;
}

div.stFileUploader label:hover {
    color: #37474F;  /* White text color on hover */
    background-color: #4e3623;  /* Darker brown background on hover */
}
</style>
"""

# Inject the CSS into the Streamlit app
st.markdown(file_uploader_css, unsafe_allow_html=True)

# Create the file uploader using Streamlit's file_uploader function
uploaded_file = st.file_uploader("", type=[ 'pdf'])


# --------------------------------------------------
# all the code below will be removed
# if uploaded_file:



    # # user_input = st.text_input("Enter the YouTube link of the song or playlist:", key='input')
    # # add an option for the user to be able to add a new topic or select from an existing topic

    # topic_selection_options = st.selectbox("Do you want to add your notes to a new topic or an existing one?", options=["","New","Existing"])

    # if topic_selection_options == "New":

    #     topic_chosen = st.text_input("Add a new topic here")
    # elif topic_selection_options =="Existing":
    #     # check the existing directory of transcripts for this user:
    #     topic_list_filepath = '/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/notebot/Transcripts/'
    #     existing_topics_list = os.listdir(topic_list_filepath)
    #     existing_topics_list = [""] + existing_topics_list

    #     topic_chosen = st.selectbox("Select which existing topic you'd like to add your transcript to", options=existing_topics_list)


    # # submit_button = st.form_submit_button(label='Make me some notes')
    # Define the CSS for the dark brown button

# --------------------------------------------------

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

submit_button = st.button(label='Make me some notes')

if submit_button and uploaded_file:
    with st.spinner("Processing your notes"):








        # the following code section will be a change to upload the file to the backend using the user's credentials


        # next get the uploaded object ready to be uploaded by renaming it and giving it the correct filepath
        # what is the filetype of the uploaded file and filename 
        uploaded_file_type = uploaded_file.name.split(".")[-1]
        uploaded_file_name = uploaded_file.name.split(".")[0]

        # this makes sure that requests are segregated by each user
        user_directory = f'users/{user_hash}/'

        logging_filename = f"{uploaded_file_name}_notebot_note_generation.pdf"
        full_file_path = f'{user_directory}{logging_filename}'


        # now upload the pdf to the backend using the user's credentials
        upload_pdf_to_gcs(st.secrets["notebot"]["bucket_name"], uploaded_file, full_file_path)











    # # --------------------------------------------------


    #     # if the uploaded file is a parquet then load the dataframe
    #     uploaded_file_suffix = uploaded_file.name.split(".")[-1]
    #     uploaded_file_name = uploaded_file.name.split(".")[0]




    #     if uploaded_file_suffix == 'gzip':
    #         df = pd.read_parquet(uploaded_files[0])
    #         uploaded_text_string = df.lecture_notes.values[0]

    #     elif uploaded_file_suffix == 'pdf':

    #         uploaded_text_string = extract_text_from_pdf(uploaded_files[0])  

    #     with st.spinner(':grey[Generating your notes...]'):

    #         transcripts_dir = f"/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/notebot/Transcripts/{topic_chosen}/"
    #         max_fuzz_score_in_transcripts_directory = get_most_similar_fuzz_ratio_of_file_in_directory(uploaded_file_name, transcripts_dir)
    #         st.markdown(f"the max fuzz score is {max_fuzz_score_in_transcripts_directory}")
            
    #         if max_fuzz_score_in_transcripts_directory<60:

    #             save_transcript(category="Transcripts", topic=topic_chosen, file_name=uploaded_file_name, file_content=uploaded_text_string)
    #         else:
    #             st.info(f"Transcript for {uploaded_file_name} already exists in the {topic_chosen} topic folder")
    #             pass

    #         import time
    #         bag_of_model_result_chunks = []

    #         safe_chunk_increment = 40000
    #         lower_bound = 0
    #         upper_bound = lower_bound + safe_chunk_increment

    #         number_of_estimated_chunks_of_input_string = round((len(uploaded_text_string)/upper_bound))+1

    #         input_lecture_notes = uploaded_text_string

    #         progress_bar = st.progress(0, text=":grey[Generating you some notes!]")

    #         # st.markdown(number_of_estimated_chunks_of_input_string)
    #         for i in range(0,number_of_estimated_chunks_of_input_string):
    #             # print(f"lower bound: {lower_bound}")
    #             # print(f"upper bound: {upper_bound}")

    #             # send the query to gpt-4o
    #             # progress_bar.progress(i/number_of_estimated_chunks_of_input_string)

    #             # st.markdown(input_lecture_notes[lower_bound:upper_bound])
    #             if len(input_lecture_notes[lower_bound:upper_bound])>300:
    #                 gpt_4_prompt_response = get_gpt4_response("Help me understand what was in the lecture I just had?", input_lecture_notes,lower_bound, upper_bound)
    #                 gpt_4_prompt_response = '\n'.join(gpt_4_prompt_response.split('\n')[1:])
    #                 gpt_4_prompt_response = gpt_4_prompt_response.replace("Question:","\nQuestion:").replace("Evidence:","\nEvidence:").replace("Answer:","\nAnswer:")
    #                 # st.markdown('\n'.join(gpt_4_prompt_response.split('\n')[1:]))
    #                 bag_of_model_result_chunks.append(gpt_4_prompt_response)
    #                 print(f"finished processing chunk {i}")
                    
    #                 # now add the chunk increment to both the upper and lower bound values
    #                 lower_bound += safe_chunk_increment
    #                 upper_bound += safe_chunk_increment
    #                 time.sleep(65)
    #             if number_of_estimated_chunks_of_input_string>1:
    #                 progress_bar.progress(i/(number_of_estimated_chunks_of_input_string-1))
    #             else:
    #                 pass

            # time.sleep(65)


        # check the backend for the detailed notes 
        with tempfile.TemporaryDirectory() as temp_dir:

            detailed_notes_string = get_detailed_notes_from_gcs(user_hash)

        if len(detailed_notes_string)>0:
            with st.expander("Here are your detailed notes"):
                st.markdown(detailed_notes_string)


                    # the code below will be deprecated and will work by receiving a file from backend loading that file and displaying the detailed notes

                    # --------------------------------------------------------------------------------------------- 











            #         detailed_llm_reponse_container = []
            #         for i in bag_of_model_result_chunks:
            #             int_i = i
            #             int_i = add_newline_before_bold(int_i)
            #             # for any case where question, answer or evidence is has ** before or after it we need to remove it
            #             int_i = int_i.replace("**Question:**","Question:").replace("**Answer:**","Answer:").replace("**Evidence:**","Evidence:").replace("**\nQuestion:**","**Question:**").replace("**\nAnswer:**","**Answer:**").replace("**\nEvidence:**","**Evidence:**").replace("**Question: **","Question:").replace("**Answer: **","Answer:").replace("**Evidence: **","Evidence:").replace("**\nQuestion: **","Question:").replace("**\nAnswer: **","Answer:").replace("**\nEvidence: **","Evidence:")
            #             st.markdown(int_i)
                        
            #             # st.write(f"---------------------------------------------------")
            #             # st.write(f"original: {i}")
            #             # st.write(f"---------------------------------------------------")
            #             # st.write(f"updated: {int_i}")
            #             detailed_llm_reponse_container.append(int_i)

            #         # Convert Markdown to HTML
            #         detailed_html_text = markdown2.markdown(add_newline_before_bold(''.join(detailed_llm_reponse_container)))

                    

            #         # this is the original version that is also used for the summary notes
            #         # modified_gpt_4_prompt_response = sanitize_html(detailed_html_text)

            #         # this was an updated version but that periodically failed 
            #         modified_gpt_4_prompt_response = sanitize_html_2(detailed_html_text)


            #         # Convert Markdown to HTML
            #         html_text = markdown2.markdown(modified_gpt_4_prompt_response)


            #         # this should be saved to the detailed_notes folder

            #         save_detailed_notes(category="Detailed Notes", topic=topic_chosen, file_name=uploaded_file_name, file_content=html_text)

            #         st.success("Your detailed notes have been saved as a pdf!")


            #         # # Create PDF from the HTML text
            #         # detailed_pdf_buffer = create_pdf(modified_gpt_4_prompt_response)

            #         # # Add a download button
            #         # st.download_button(
            #         #     label="Download Detailed Notes",
            #         #     data=detailed_pdf_buffer,
            #         #     file_name=f"{uploaded_file_name}_notebot_detailed_notes.pdf",
            #         #     mime="application/pdf"
            #                             # )                
            #     # now what we'll do is send this combined summary of notes into a final request to combine, standardise and generate a single result
            #     # which accurately reflects the whole lecture
            

            # combined_initial_notes_string = ''.join(bag_of_model_result_chunks)

            # # st.markdown(len(combined_initial_notes_string))


            # if len(combined_initial_notes_string)>safe_chunk_increment:
            #     # the notes are still to large to be put into the output layer so run a further reduction 


            #     bag_of_model_result_chunks = []

            #     safe_chunk_increment = 20000
            #     lower_bound = 0
            #     upper_bound = lower_bound + safe_chunk_increment

            #     number_of_estimated_chunks_of_input_string = round((len(combined_initial_notes_string)/upper_bound))+1

            #     input_lecture_notes = combined_initial_notes_string

            #     note_string_chunks = get_random_chunks(input_lecture_notes)

            #     progress_bar = st.progress(0, text="Generating you some notes!")

            #     for i in range(len(note_string_chunks)):
                    
            #         gpt_4_prompt_response = get_gpt4_response_hidden("Help me understand what was in the lecture I just had?",note_string_chunks[i])
            #         bag_of_model_result_chunks.append(gpt_4_prompt_response)
            #         print(f"finished processing chunk {i}")
                    
            #         # now add the chunk increment to both the upper and lower bound values
            #         # lower_bound += safe_chunk_increment
            #         # upper_bound += safe_chunk_increment
            #         time.sleep(65)

            #         progress_bar.progress(i/(len(note_string_chunks)-1))

            
            # combined_initial_notes_string = ''.join(bag_of_model_result_chunks)

            # st.markdown(len(combined_initial_notes_string))
            # check the backend for the detailed notes 
        with tempfile.TemporaryDirectory() as temp_dir:

            summary_notes_string = get_summary_notes_from_gcs(user_hash)
        with st.expander("Here is your high level summary"):
            st.markdown(summary_notes_string)
                # the code below will be deprecated and will work by receiving a file from backend loading that file and displaying the detailed notes

                # --------------------------------------------------------------------------------------------- 



                # gpt_4_prompt_response = get_gpt4_response_final("Help me understand what was in the lecture I just had?", combined_initial_notes_string)
                # st.success("Your high level summary has been generated")
                # st.markdown(f"{add_newline_before_bold(gpt_4_prompt_response)}")

            modified_gpt_4_prompt_response = sanitize_html_2(summary_notes_string)


            # Convert Markdown to HTML
            html_text = markdown2.markdown(modified_gpt_4_prompt_response)


            # save_summary_notes(category="Summary Notes", topic=topic_chosen, file_name=uploaded_file_name, file_content=html_text)

            # st.success("Your summary notes have been saved as a pdf!")

            # Create PDF from the HTML text
            pdf_buffer = create_pdf(html_text)


            # Add a download button
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name=f"{uploaded_file_name}_notebot_high_level_summary_notes.pdf",
                mime="application/pdf"
                                )

            # st.session_state['messages'].append(('You', user_input))
            # st.markdown("beginning to process your link.")
            # bot_response = model.transcribe(audio_path)
            # bot_response = bot_response["text"]
            # st.session_state['messages'].append(('Bot', bot_response))


            # save this bot response in the same location as the audio_path
            # test_lecture_df = pd.DataFrame([bot_response]).rename(columns={0:"lecture_notes"})
            # test_lecture_df.to_parquet(f"{song_file_directory}/{song_name}_text_from_notebot_part_1.parquet.gzip", compression="gzip")


    # for sender, message in st.session_state['messages']:
    #     st.write(f"**{sender}:** {message}")