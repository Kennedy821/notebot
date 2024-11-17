import pandas as pd
import ollama
import os
import polars as pl
import fitz  # PyMuPDF
from tqdm.notebook import tqdm
from langchain_community.llms import Ollama
import openai
# from shapely.geometry import Polygon
from openai import OpenAI
import os
import tiktoken
import streamlit as st
from fuzzywuzzy import fuzz
import time
import numpy as np
import requests
import tempfile
import random
import re

from datetime import datetime
# get today's date in the format dd_mm_yyyy
today = datetime.today()
today = today.strftime("%d_%m_%Y")

# create the functions

def flatten_list(nested_list):
    return [item for sublist in nested_list for item in sublist]

client = OpenAI(api_key=st.secrets["openai"]["OPEN_AI_KEY"])


def stream_data(input_text):
    for word in input_text.split(" "):
        yield word + " "
        time.sleep(0.02)


# Create the llama 3 agents 
class GPT4o_question_and_answer_extractor:
    def __init__(self, model_name, version):
        self.model_name = model_name
        self.version = version
        self.history = []  # Store interaction history

    def send_command(self, command):

        chosen_model = "gpt-4o-mini"


        system_role_prompt = f"""Return two lists, the first with questions only, the second list with answers only.
                                                
                                Separate each question in it's list with a '|' character before and after. Do the same for the answers list as well.
                                
                                Follow this template:
                                'BREAK'
                                Q1. provide question number one here |
                                Q2. provide question number two here | etc...

                                'BREAK'
                                A1. provide answer number one here |
                                A2. provide answer number two here| etc...
                                """
        
        # This is a placeholder for how you might interact with the LLM.
        # In a real implementation, you'd connect to the LLM API and send the command.
        response = client.chat.completions.create(
                                                  model=chosen_model,
                                                  messages=[
                                                    {"role": "system", "content": f"""{system_role_prompt}"""},
                                                    {"role": "user", "content": command}
                                                  ]
                                                )
        response = response.choices[0].message.content
        self.history.append((command, response))
        return response

    def get_history(self):
        return self.history
    
# Create the llama 3 agents 
class GPT4o_question_and_answer_extractor_multiple_choice:
    def __init__(self, model_name, version):
        self.model_name = model_name
        self.version = version
        self.history = []  # Store interaction history

    def send_command(self, command):

        chosen_model = "gpt-4o"


        system_role_prompt = f"""Return two lists, the first with questions only, the second list with answers only but you must generate at least four equally plausible answers so it is a challenge for the reader to pick the correct answer. Only one of these answers can be correct. Each possible answer must be roughly the same number of words. Ensure they all start with the same word. make sure they are answers!
                                                
                                Separate each question in it's list with a '|' character before and after. Do the same for the answers list as well. All questions should be bold!
                                
                                **IMPORTANT**: The correct answer must be randomly assigned to one of the options (a, b, c, or d) for each question. Make sure to shuffle the answers for every question so the correct answer is not always in position "a."

                                Follow this template:
                                'BREAK'
                                Q1. provide question number one here |
                                Q2. provide question number two here | etc...

                                'BREAK'
                                A1@ provide answer number one here # option a  *  provide answer number one here # option b *  provide answer number one here # option c * provide answer number one here # option d|
                                A2@ provide answer number two here # option a  *  provide answer number two here # option b *  provide answer number two here # option c * provide answer number two here # option d|| etc...
                                """
        
        # This is a placeholder for how you might interact with the LLM.
        # In a real implementation, you'd connect to the LLM API and send the command.
        response = client.chat.completions.create(
                                                  model=chosen_model,
                                                  messages=[
                                                    {"role": "system", "content": f"""{system_role_prompt}"""},
                                                    {"role": "user", "content": command}
                                                  ]
                                                )
        response = response.choices[0].message.content
        self.history.append((command, response))
        return response

    def get_history(self):
        return self.history

# Agent to verify output correctness
class QuestionAnswerVerifier:
    def __init__(self):
        self.correct_answer_pattern = re.compile(r'# option (a|b|c|d)')

    def validate_format(self, response):
        # Check the basic format of questions and answers
        if 'BREAK' not in response:
            raise ValueError("Response is missing the 'BREAK' keyword.")
        if not re.search(r'\| \*\*Q[0-9]+', response):
            raise ValueError("Questions are not bolded or properly formatted with '|'.")
        if not re.search(r'A[0-9]+@ Option a:', response):
            raise ValueError("Answers are not in the expected format.")

    def check_randomness_of_correct_answers(self, response):
        # Extract the correct answers using regex
        matches = self.correct_answer_pattern.findall(response)
        if not matches:
            raise ValueError("No correct answers found in response.")

        # Ensure that correct answers are distributed randomly and not always in option 'a'
        if all(answer == 'a' for answer in matches):
            raise ValueError("All correct answers are in position 'a'. This should not happen.")
        
        print(f"Correct answers are distributed across options: {set(matches)}")

    def run_verification(self, response):
        try:
            self.validate_format(response)
            self.check_randomness_of_correct_answers(response)
            print("Verification successful: Response is correctly formatted and answers are randomized.")
        except ValueError as ve:
            print(f"Verification failed: {ve}")

class GPT4oVerifierAgent:
    def __init__(self, model_name, version):
        self.model_name = model_name
        self.version = version
        self.history = []  # Store interaction history

    def verify_response(self, response):
        # Construct verification prompt
        verification_prompt = f"""
        You are an AI agent responsible for verifying the format and correctness of a multiple-choice question and answer response. The response should follow these criteria:

        1. All questions must be bolded and properly formatted, each separated by '|' before and after.
        2. Each question should have four equally plausible answer options, where only one is correct.
        3. The correct answer must not always be in option 'a'. It must be randomly assigned to one of the options (a, b, c, or d).
        4. The overall format must follow the given template:

        'BREAK'
        | **Q1. Provide the first question here** |
        | **Q2. Provide the second question here** | 
        ...continue for all questions...

        'BREAK'
        A1@ Option a: provide answer option here * Option b: provide answer option here * Option c: provide answer option here * Option d: provide answer option here (shuffle the correct answer's position randomly) |
        A2@ Option a: provide answer option here * Option b: provide answer option here * Option c: provide answer option here * Option d: provide answer option here (shuffle the correct answer's position randomly) |
        ...continue for all answers...

        Based on these criteria, verify if the following response is correct and reply with 'yes' for if it is correctly formatted or 'no':

        RESPONSE:
        {response}
        """

        # Placeholder for GPT interaction (assume this sends the prompt to a model like GPT-4)
        chosen_model = "gpt-4o-mini"
        verification_response = client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": verification_prompt},
            ]
        )

        self.history.append((response, verification_response))
        return verification_response.choices[0].message.content

# Create a function that uses the llm to return a language binary
def generate_questions_bot_GPT4o(reference_material):
    gpt4o_worker = GPT4o_question_and_answer_extractor("gpt_4o","4o")
    response = gpt4o_worker.send_command(f"""You are a study card question generating system.
    
                                                You must extract a 3 questions and answers from the following: {reference_material}. Don't just pick things from the beginning.

                                                These questions should be able to be answered by a 10 year old.
    
                                                """)
    return response

# Create a function that uses the llm to return a language binary
def generate_questions_bot_GPT4o_multiple_choice(reference_material,difficulty, n):
    gpt4o_worker = GPT4o_question_and_answer_extractor_multiple_choice("gpt_4o","4o")
    response = gpt4o_worker.send_command(f"""You are a study card question generating system.
    
                                                You must extract a {n} questions and answers from the following: {reference_material}. Don't just pick questions from the beginning.

                                                If the difficulty requested by the users is High this means the questions you generate should be at the level of a Masters student.
                                                If the difficulty requested by the users is Medium this means the questions you generate should be at the level of a first year undergraduate student.
                                                If the difficulty requested by the users is Easy this means the questions you generate should be at the level of a 10 year old student.

                                                Your user has requested a diffulty of: {difficulty}.
    
                                                """)
    return response

# Create the llama 3 agents 
class GPT4o:
    def __init__(self, model_name, version):
        self.model_name = model_name
        self.version = version
        self.history = []  # Store interaction history

    def send_command(self, command):

        chosen_model = "gpt-4o-mini"


        system_role_prompt = f"You are a teacher / tutor who is helping a student study a topic using study cards."
        
        # This is a placeholder for how you might interact with the LLM.
        # In a real implementation, you'd connect to the LLM API and send the command.
        response = client.chat.completions.create(
                                                  model=chosen_model,
                                                  messages=[
                                                    {"role": "system", "content": f"""{system_role_prompt}"""},
                                                    {"role": "user", "content": command}
                                                  ]
                                                )
        response = response.choices[0].message.content
        self.history.append((command, response))
        return response

    def get_history(self):
        return self.history
    
def review_questions_and_answers_GTP4(question,provided_answer,multiple_choice_options,reference):
    gpt_4o_worker = GPT4o("gpt_4o_worker_teacher_1","4o")
    response = gpt_4o_worker.send_command(f"You are a teacher / tutor who is helping a student study a topic using study cards. The question the student was asked is: {question}. This is the answer the student provided: {provided_answer}. This has been selected from a list of multiple choice options: {multiple_choice_options} Decide if the student got the answer correct and explain your rationale step by step. Use this information to support your decision: {reference}")
    return response

def review_questions_and_answers_GTP4_multiple_choice(question,provided_answer,multiple_choice_options,reference):
    gpt_4o_worker = GPT4o("gpt_4o_worker_teacher_1","4o")
    response = gpt_4o_worker.send_command(f"You are a teacher / tutor who is helping a student study a topic using study cards. The question the student was asked is: {question}. This is the answer the student provided: {provided_answer}. This has been selected from a list of multiple choice options: {multiple_choice_options}.The student could only pick one answer. Decide if the student selected the best possible answer from the provided options.  Explain your rationale step by step. Use this information to support your decision: {reference}")
    return response

def provide_additional_context_before_the_question(question, answer, reference):
    gpt_4o_worker = GPT4o("gpt_4o_question_context_provider", "4o")
    response = gpt_4o_worker.send_command(f"""
        You are an AI teacher helping a student prepare to answer a question. 
                                          
        The student is a postgraduate student.
                                           
        Your role is to provide extra context around the question to guide the student toward 
        a thoughtful and relevant answer, but without revealing the answer itself. 
        
        The question the student was asked is: {question}.
        The answer they provided is: {answer}.
        
        Using only the following reference material: {reference}, please provide 3 brief but 
        focused bullet points that give the student additional context for understanding the question. 
        These points should help the student focus their response on key ideas related to the topic, 
        but **do not give away the answer** or directly reference it.
    """)
    return response
# create a summarising agent 

# Create the llama 3 agents 
class GPT4o_adjudicator:
    def __init__(self, model_name, version):
        self.model_name = model_name
        self.version = version
        self.history = []  # Store interaction history

    def send_command(self, command, teacher_marking_1, teacher_marking_2):

        chosen_model = "gpt-4o"


        system_role_prompt = f"""You are a educational assistant who is adjudicating the responses of two teachers and need to provide an answer of correct or incorrect.
                                WOrk through your decision step by step.
                                Provide some guidance explaining how the student could have answered better (only if their answer was incorrect) this should be all on the same line. 
                                Your response should be in the following format:
                                
                                template:
                                QUESTION: [put the original question asked here]
                                *****
                                STUDENT_ANSWER: [put the student answer here]
                                *****
                                DECISION: provide your binary option of 'correct', 'partially correct' and incorrect'
                                *****
                                MARKS: provide a max value of '1' for correct, '0.5' for partially correct and '0' for 'incorrect'. this must be based on your decision
                                *****
                                SUGGESTIONS: [your view here keep it all on the same line. Address the student directly in a polite, objective and encouraging tone. Provide a step by step view of the decision making process to come to the correct answer.].

                                The first teacher has said: {teacher_marking_1}

                                The second teacher has said {teacher_marking_2}

                                """
        # print(system_role_prompt)
        
        # This is a placeholder for how you might interact with the LLM.
        # In a real implementation, you'd connect to the LLM API and send the command.
        response = client.chat.completions.create(
                                                  model=chosen_model,
                                                  messages=[
                                                    {"role": "system", "content": f"""{system_role_prompt}"""},
                                                    {"role": "user", "content": command}
                                                  ],
                                                max_tokens=250,  # Adjust based on the length of the completion
                                                temperature=0.1  # Controls randomness (lower = more focused)
                                                )
        response = response.choices[0].message.content
        self.history.append((command, response))
        return response

    def get_history(self):
        return self.history
    
def get_adjudicators_view(teacher_1_comments, teacher_2_comments):
    gpt_4o_adjudicator = GPT4o_adjudicator("gpt_4o_adjudicator_1","4o")
    response = gpt_4o_adjudicator.send_command(f"You are a educational AI system who is adjudicating the responses of two teachers and need to provide an answer of correct or incorrect.",teacher_1_comments,teacher_2_comments )
    return response


# Create the llama 3 agents 
class GPT4o_test_performance_reviewer:
    def __init__(self, model_name, version):
        self.model_name = model_name
        self.version = version
        self.history = []  # Store interaction history

    def send_command(self, command):

        chosen_model = "gpt-4o"


        system_role_prompt = f"""You are a educational assistant who is summarise how the student performed in particular have a look the feedback provided.

                                Provide a step by step view of the decision making process to come to the correct answer. 

                                Help the student identify where they went wrong and how they could improve. In particular how they can cement some of the ideas they may be struggling with (Only if they got the question wrong!)

                                """
        # print(system_role_prompt)
        
        # This is a placeholder for how you might interact with the LLM.
        # In a real implementation, you'd connect to the LLM API and send the command.
        response = client.chat.completions.create(
                                                  model=chosen_model,
                                                  messages=[
                                                    {"role": "system", "content": f"""{system_role_prompt}"""},
                                                    {"role": "user", "content": command}
                                                  ],
                                                max_tokens=500,  # Adjust based on the length of the completion
                                                temperature=0.1  # Controls randomness (lower = more focused)
                                                )
        response = response.choices[0].message.content
        self.history.append((command, response))
        return response

def get_overall_student_performance_provide_feedback(summary_df):
    # convert each row into a reasonable sentence
    overall_performance = []
    for i in range(len(summary_df)):
        question = summary_df.iloc[i,0]
        answer = summary_df.iloc[i,1]
        feedback = summary_df.iloc[i,-1]

        summary_sentence = f"""
        
                                For question {i} The student was asked {question}

                                The student answered: {answer}

                                The teacher provided the following feedback: {feedback}
                            """
        overall_performance.append(summary_sentence)

    # join the sentences together
    combined_sentences = ' '.join(overall_performance)

    gpt_4o_summariser = GPT4o_test_performance_reviewer("gpt_4o_test_summariser","4o")
    response = gpt_4o_summariser.send_command(f"You are a educational AI system who is summarise how the student performed in particular have a look the feedback provided. Where are their strengths and where could they improve? Here is the information you have been given about their most recent test performance: {combined_sentences}" )
    return response

# def generate_audio_elevenlabs(text, voice_id, xi_api_key, file_name):
#     # API endpoint and headers
#     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
#     headers = {
#         "Accept": "audio/mpeg",
#         "Content-Type": "application/json",
#         "xi-api-key": xi_api_key
#     }

#     # Data payload with text and voice settings
#     data = {
#         "text": text,
#         "model_id": "eleven_turbo_v2_5",
#         "voice_settings": {
#             "stability": 0.5,
#             "similarity_boost": 0.5
#         }
#     }

#     # Make the request to the API
#     response = requests.post(url, json=data, headers=headers)

#     # Save the audio file as .mp3 in the provided file path
#     with open(file_name, 'wb') as f:
#         for chunk in response.iter_content(chunk_size=1024):
#             if chunk:
#                 f.write(chunk)

#     return file_name

# def flatten_list(nested_list):
#     flattened = []
#     for item in nested_list:
#         if isinstance(item, list):
#             flattened.extend(flatten_list(item))
#         else:
#             flattened.append(item)
#     return flattened


# transcript directory
transcript_directory = os.getcwd()+'/Detailed Notes/'
transcript_directory_list = os.listdir(transcript_directory)
transcript_directory_list = [x for x in transcript_directory_list if "." not in x]
transcripts_list = [""]+transcript_directory_list

st.header("Select which topic you'd like to study")
# chosen_topic = st.selectbox("Choose topic here", options=transcripts_list)

chosen_topics = st.multiselect("Choose what you'd like to study today",transcripts_list)
# st.write(f"you have chosen to study: {chosen_topics}, type({type(chosen_topics)})")



st.write("Would you like open-ended questions or multiple choice?")
chosen_type_of_test = st.selectbox("Choose type of test", options=["","open-ended","multiple-choice"])

if len(chosen_topics)>=1 and len(chosen_type_of_test)>5:
    multiple_transcript_options_container = [""]
    for chosen_topic in chosen_topics:

        # select the file you'd like to study in the chosen directory 
        transcript_file_directory = os.getcwd()+f'/Transcripts/{chosen_topic}/'
        transcript_file_directory_list = os.listdir(transcript_file_directory)
        # st.markdown(transcript_file_directory_list)
        # transcript_file_directory_list_clean = [x.split('.')[0].replace("_"," ") for x in transcript_file_directory_list if "gzip" not in x]
        transcript_file_directory_list_clean = [x.split('.')[0].replace("_"," ") for x in transcript_file_directory_list]

        transcript_file_directory_list_clean = list(set([x.replace("transcript","").strip() for x in transcript_file_directory_list_clean]))
        transcripts_file_list = transcript_file_directory_list_clean
        transcripts_file_list = list(set(transcripts_file_list))
        multiple_transcript_options_container.append(transcripts_file_list)
    # st.write(transcripts_file_list)
    transcripts_file_list = list(set(flatten_list([x for x in multiple_transcript_options_container if ".DS_Store" not in x])))


    multiple_detailed_notes_options_container = []
    for chosen_topic in chosen_topics:

        # detailed notes directory 
        detailed_notes_directory = os.getcwd()+f'/Detailed Notes/{chosen_topic}/'
        detailed_notes_directory_valid_list = os.listdir(detailed_notes_directory)
        detailed_notes_list = detailed_notes_directory_valid_list
        multiple_detailed_notes_options_container.append(detailed_notes_list)

    # st.markdown(flatten_list(multiple_detailed_notes_options_container))

    detailed_notes_list = flatten_list(multiple_detailed_notes_options_container)


    # # detailed notes directory 
    # detailed_notes_directory = os.getcwd()+f'/Detailed Notes/{chosen_topic}/'
    # detailed_notes_directory_valid_list = os.listdir(detailed_notes_directory)
    # detailed_notes_list = detailed_notes_directory_valid_list

    # st.markdown(detailed_notes_list)

    # below is the code for the actual streamlit application 


    # chosen_transcript = st.selectbox("Choose what you'd like to study today",options=transcripts_file_list)

    chosen_transcripts = st.multiselect("Choose what you'd like to study today",transcripts_file_list)
    # chosen_transcripts = st.multiselect("Choose what you'd like to study today",transcripts_file_list)

    # st.write(f"you have chosen to study: {chosen_transcripts}, type({type(chosen_transcripts)})")



    chosen_difficulty = st.selectbox("Choose how difficult you want the test to be",options=["","High","Medium","Easy"])

    chosen_number_of_questions = st.selectbox("Choose how many questions you want to answer",options=["","3","5","10","20"])

    # run a fuzzy match to match the chosen name to the original file name in the directory

    def get_most_similar_name_of_file_in_directory(input_name, song_directory):
        fuzz_df_chunk_container = []
        for directory_filename in os.listdir(song_directory):
            # st.markdown(directory_filename)
            try:

                ratio = fuzz.ratio(input_name, directory_filename)
                int_df = pd.DataFrame([input_name])
                int_df.columns = ["clean_name"]
                # int_df["clean_name"] = input_name
                int_df["file_in_dir"] = directory_filename
                int_df["fuzz_ratio_score"] = ratio
                # st.dataframe(int_df)
                fuzz_df_chunk_container.append(int_df)
            except Exception as e:
                pass
            
        fuzz_comp_df = pd.concat(fuzz_df_chunk_container, ignore_index=True)
        file_to_open = fuzz_comp_df.sort_values("fuzz_ratio_score", ascending=False).head(1).file_in_dir.values[0]
        return file_to_open

    # run the fuzzy match function to get the actual name of the file to open
    if len(chosen_transcripts)>=1 and len(chosen_difficulty)>2 and len(chosen_number_of_questions)>0:
        container_of_actual_file_paths = []
        for chosen_topic in chosen_topics:
            detailed_notes_directory = os.getcwd()+f'/Detailed Notes/{chosen_topic}/'
            for chosen_transcript in chosen_transcripts:
                actual_transcript_file_to_open = get_most_similar_name_of_file_in_directory(chosen_transcript,detailed_notes_directory )
                # st.write(detailed_notes_directory,actual_transcript_file_to_open)
                full_filepath = detailed_notes_directory+actual_transcript_file_to_open
                container_of_actual_file_paths.append(full_filepath)
        # clean this up by only allowing pdfs to be used from this point on and having a unique list of filepaths
        container_of_actual_file_paths = [x for x in container_of_actual_file_paths if "pdf" in x]
        container_of_actual_file_paths = list(set(container_of_actual_file_paths))


        # st.markdown(f"these are the filepaths to open: {container_of_actual_file_paths}")

        # below is the old code to do this
        # actual_transcript_file_to_open = get_most_similar_name_of_file_in_directory(chosen_transcript,detailed_notes_directory )
        # st.markdown(actual_transcript_file_to_open)

        # st.markdown(actual_transcript_file_to_open)

        # df = pd.read_parquet(transcript_directory+chosen_topic+'/'+actual_transcript_file_to_open)

        # full_filepath_of_chosen_document = transcript_directory+chosen_topic+'/'+actual_transcript_file_to_open

        # st.write(f"Here is the full filepath for the seleccted transcrip: {full_filepath_of_chosen_document}")

        # Load the reference materials for each transcript

        reference_material_container = []

        for full_filepath_of_chosen_document in container_of_actual_file_paths:
            try:

            
                pdf_page_container = []

                # Read the content of the uploaded file
                # st.write(f"opening the file: {full_filepath_of_chosen_document}")
                pdf_content = full_filepath_of_chosen_document

                # Open the PDF from the content
                doc = fitz.open(pdf_content)

                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text = page.get_text("text")
                    pdf_page_container.append(text)

                # Close the document
                doc.close()


                
                reference_materials = pd.DataFrame([','.join(pdf_page_container)]).iloc[0,0]

                reference_material_container.append(reference_materials)
            except  Exception as e:
                st.write(e)

        # combine the strings together in the reference material container
        # shuffle the topic strings 
        random.shuffle(reference_material_container)
        reference_materials = ','.join(reference_material_container)

        # st.markdown(reference_materials)
        
        # reference_materials = df.iloc[0,0]

        # look in the detailed notes and find the appropriate detailed notes
        if chosen_transcript:
            detailed_notes_df = pd.DataFrame(detailed_notes_list)
            detailed_notes_df.columns = ["detailed_notes_names"]
            detailed_notes_df["chosen_transcript"] = chosen_transcript
            detailed_notes_df["fuzz_ratio"] = detailed_notes_df.apply(lambda x: fuzz.ratio(x.chosen_transcript, x.detailed_notes_names), axis=1)
            detailed_notes_name = detailed_notes_df.sort_values("fuzz_ratio", ascending=False).head(1).detailed_notes_names.values

            uploaded_detailed_notes_pdf = detailed_notes_directory+detailed_notes_name
            uploaded_detailed_notes_pdf = uploaded_detailed_notes_pdf[0]
            # st.markdown(uploaded_detailed_notes_pdf)


        # the uploaded detailed notes are now the same as the reference materials
        uploaded_detailed_notes_pdf = reference_materials
        questions_data_corpus = reference_materials
        #  load the original transcript 

        #---------------------------------------------------------------------------------------------------------------------
        # student_response_df_container = []

        # st.write("Load the transcript file")

        # reference_materials_file = st.file_uploader("", accept_multiple_files=True, type=['gzip', 'pdf'], key="transcript")
        # if len(reference_materials_file)>0:
        #     df = pd.read_parquet(reference_materials_file[0])
        #     reference_materials = df.iloc[0,0]



        # # load the detailed notes for this transcript - this will have been created by Notebot

        # st.write("Load the detailed notes for the transcript")

        # uploaded_detailed_notes_pdf = st.file_uploader("", accept_multiple_files=True, type=['gzip', 'pdf'],key="detailed_notes")
        #---------------------------------------------------------------------------------------------------------------------

        if len(chosen_transcripts)>0 and len(chosen_difficulty)>2:
            if len(uploaded_detailed_notes_pdf)>0:

                # # process the pdf 
                # pdf_page_container = []

                # # Read the content of the uploaded file
                # pdf_content = uploaded_detailed_notes_pdf

                # # Open the PDF from the content
                # doc = fitz.open(pdf_content)

                # for page_num in range(len(doc)):
                #     page = doc.load_page(page_num)
                #     text = page.get_text("text")
                #     pdf_page_container.append(text)

                # # Close the document
                # doc.close()


                # # doc = fitz.open(stream=uploaded_detailed_notes_pdf[0], filetype="pdf")

                # # for page_num in range(len(doc)):
                # #     page = doc.load_page(page_num)
                # #     text = page.get_text("text")
                # #     # print(f"Page {page_num+1}:\n{text}")
                # #     pdf_page_container.append(text)

                # # [','.join(pdf_page_container)]
                    
                # questions_data_corpus = pd.DataFrame([','.join(pdf_page_container)]).iloc[0,0]
                # questions_data_corpus
                
                # Load questions into session state
                if 'questions' not in st.session_state:
                    if chosen_type_of_test=="open-ended":
                        # This will only run once per session
                        st.session_state.questions = generate_questions_bot_GPT4o(questions_data_corpus).split("'BREAK'")
                        # Generate the questions and answers for the student to answer 
                        study_card_lists = st.session_state.questions
                    elif chosen_type_of_test!="open-ended":
                        check_value = 0
                        verification_result = "no"
                        while check_value!=4 and verification_result != "yes":
                            try:
                                # This will only run once per session
                                st.session_state.questions = generate_questions_bot_GPT4o_multiple_choice(questions_data_corpus,chosen_difficulty,chosen_number_of_questions).split("'BREAK'")
                                # validate that these questions all conform to the correct format
                                verifier_agent = GPT4oVerifierAgent("gpt-4o", "1.0")
                                verification_result = verifier_agent.verify_response(st.session_state.questions)
                                # st.markdown(verification_result)
                                if verification_result == "yes":
                                    st.success("All questions and answers are correctly formatted.")

                                test_cleaned_generated_output = [x for x in st.session_state.questions if len(x)>1]

                                # st.markdown(test_cleaned_generated_output)
                                # random.shuffle(cleaned_generated_output)

                                test_list_of_questions = [x for x in test_cleaned_generated_output[0].split("|") if len(x)>5][:]
                                
                                test_list_of_answers = [x for x in test_cleaned_generated_output[1].split("|") if len(x)>5][:]

                                check_container = []
                                for _ in range(len(test_list_of_questions)):

                                    test_multiple_choice_answers = test_list_of_answers[_].split("@")[1].strip()[:].split("*")
                                    # st.markdown(f":{len(test_multiple_choice_answers)}")
                                    check_container.append(len(test_multiple_choice_answers))
                                check_value = np.array(check_container).sum() / len(test_list_of_questions)
                                # st.markdown(f"check value: {check_value}")


                                # list_of_answer_options = []
                                
                                # Generate the questions and answers for the student to answer 
                                study_card_lists = st.session_state.questions
                            except Exception as e:
                                pass


                # this is the version for multiple choice
                # Generate the questions and answers for the student to answer 
                # study_card_lists = generate_questions_bot_GPT4o_multiple_choice(questions_data_corpus).split("'BREAK'")


                study_card_lists = st.session_state.questions

                # remove any empty string characteres
                cleaned_generated_output = [x for x in study_card_lists if len(x)>1]

                # st.markdown(cleaned_generated_output)
                # random.shuffle(cleaned_generated_output)

                # use random shuffle on the list of questions and answers making sure they remain matched in the same order

                list_of_questions = [x for x in cleaned_generated_output[0].split("|") if len(x)>5][:]
                
                list_of_answers = [x for x in cleaned_generated_output[1].split("|") if len(x)>5][:]

                # Zip the lists together
                # paired_list = list(zip(list_of_questions, list_of_answers))

                # # Shuffle the paired list
                # random.shuffle(paired_list)

                # # Unzip the paired list back into two separate lists
                # list_of_questions, list_of_answers = zip(*paired_list)

                # # If you need them back as lists (since zip returns tuples):
                # list_of_questions = list(list_of_questions)
                # list_of_answers = list(list_of_answers)

                # if the multiple choice version has been used 

                # st.write("these are the questions")
                # st.markdown(list_of_questions)

                # st.write("these are the answers")
                # st.markdown(list_of_answers)

                # Initialize session state variables
                # Use session state to store the shuffled order

                # Initialize shuffled orders for each question
                for index, question in enumerate(list_of_questions):
                    key = f"shuffled_order_{index}"
                    if key not in st.session_state:
                        st.session_state[key] = random.sample(range(4), 4)
                # deprecated version of code above
                # for value in range(len(list_of_questions)):
                #     if 'shuffled_order' not in st.session_state:
                #         st.session_state[f"shuffled_order_{value}"] = random.sample(range(4), 4)
                if 'answers' not in st.session_state:
                    st.session_state.answers = [''] * len(list_of_questions)
                if 'submitted' not in st.session_state:
                    st.session_state.submitted = [False] * len(list_of_questions)
                if 'student_response_df_container' not in st.session_state:
                    st.session_state.student_response_df_container = []



                for value in range(len(list_of_questions)):

                    # the next line will display the quesion in bold 
                    st.markdown(f"{list_of_questions[value]}")
                    with st.expander("Read out the question"):
                        pass

                        # with tempfile.TemporaryDirectory() as temp_dir:

                            
                            
                        #     voice_id = "pFZP5JQG7iQjIQuC4Bku"
                        #     xi_api_key = SECRET_KEY = st.secrets["elevenlabs"]["SECRET_KEY"]
                        #     text_for_audio_generation = list_of_questions[value].split(".")[1]
                        #     temp_file_path = os.path.join(temp_dir, "output.mp3")

                        #     # Generate the audio and save it in the temporary file
                        #     generate_audio_elevenlabs(text_for_audio_generation, voice_id, xi_api_key, file_name=temp_file_path)

                        #     # Display the audio in Streamlit using the temp file
                        #     st.audio(temp_file_path, format="audio/mp3")

                    # if chosen_type_of_test=="open-ended":

                        

                    if chosen_type_of_test!="open-ended":

                        print(f"{list_of_questions[value]}\n")

                    # else:



                        multiple_choice_answers = list_of_answers[value].split("@")[1].strip()[:].split("*")

                        list_of_answer_options = []
                        #  Check if the answer has already been submitted
                        # random.shuffle(multiple_choice_answers)
                        letter_option_list = ["A","B","C","D"]
                        for _ in range(len(multiple_choice_answers)):
                            clean_answer_option = multiple_choice_answers[_].split("#")[0].strip()
                            try: 
                                # st.write(f"{letter_option_list[_]}:\t{clean_answer_option}\n")
                                list_of_answer_options.append(f"\t{clean_answer_option}\n")
                                # deprecated version below:
                                # list_of_answer_options.append(f"{letter_option_list[_]}:\t{clean_answer_option}\n")

                            except Exception as e:
                                print(f'{e}')
                        print("---------------------------------------------------------------------------------------------------------")

                        key = f"answer_{value}"


                        # Function to create shuffled radio buttons
                        def create_shuffled_radio(options, index):
                            shuffled_order = st.session_state[f"shuffled_order_{index}"]
                            shuffled_options = [options[i] for i in shuffled_order]
                            return shuffled_options
                        # st.markdown(f"key: {key}")
                        # Shuffle the options randomly

                        shuffled_elements = create_shuffled_radio(list_of_answer_options, value)
                        # deprecated version below:
                        # shuffled_elements = [list_of_answer_options[i] for i in st.session_state.shuffled_order]
                        # below is an attempt to try and use the streamlit radio button to select the answer
                        student_answer = st.radio("Choose the correct answer", options=shuffled_elements, index=None,key = key)
                        with st.expander("Read out the possible answers"):

                            pass

                            # with tempfile.TemporaryDirectory() as temp_dir:
                                    
                            #         voice_id = "pFZP5JQG7iQjIQuC4Bku"
                            #         xi_api_key = SECRET_KEY = st.secrets["elevenlabs"]["SECRET_KEY"]
                            #         text_for_audio_generation = ''.join(list_of_answer_options)
                            #         temp_file_path = os.path.join(temp_dir, "output.mp3")

                            #         # Generate the audio and save it in the temporary file
                            #         generate_audio_elevenlabs(text_for_audio_generation, voice_id, xi_api_key, file_name=temp_file_path)

                            #         # Display the audio in Streamlit using the temp file
                            #         st.audio(temp_file_path, format="audio/mp3")

                    else:
                        pass

                    # if they need additional help for the open ended questions
                    if chosen_type_of_test=="open-ended":
                        with st.expander("Open here if you need some hints"):
                            additional_context_statement = provide_additional_context_before_the_question(list_of_questions[value],list_of_answers[value],reference_materials)

                            st.write_stream(stream_data(additional_context_statement))

                    # # Use a unique key for each text input
                    # key = f"answer_{value}"

                    # st.markdown("""
                    #             <style>
                    #                 textarea {
                    #                     background-color: #f0f0f0 !important;
                    #                 }
                    #             </style>
                    #             """, unsafe_allow_html=True)
                    
                    # student_answer = st.text_area(f"Write your answer here", 
                    #                             key=key, 
                    #                             value=st.session_state.answers[value])

                    # Update the answer in session state
                    st.session_state.answers[value] = student_answer

                    # Add a button to submit their response
                    # submit_button = st.button(f"Submit your answer for question {value+1}", key=f"submit_{value+1}")

                    

                    # Check if the answer has already been submitted
                    if not st.session_state.submitted[value]:
                        if student_answer:
                            if len(student_answer) >= 1:
                                st.session_state.submitted[value] = True
                                st.success("Your answer has been submitted for review.")

                                # if the student is using open-ended questions use these teachers
                                if chosen_type_of_test=="open-ended":
                                    # Process the student's response
                                    teacher_1_marking_sheet = review_questions_and_answers_GTP4(list_of_questions[value], student_answer,list_of_answers[value], reference_materials)
                                    teacher_2_marking_sheet = review_questions_and_answers_GTP4(list_of_questions[value], student_answer,list_of_answers[value], reference_materials)
                                
                                elif chosen_type_of_test=="multiple-choice":
                                    # Process the student's response
                                    teacher_1_marking_sheet = review_questions_and_answers_GTP4_multiple_choice(list_of_questions[value], student_answer,multiple_choice_answers, reference_materials)
                                    teacher_2_marking_sheet = review_questions_and_answers_GTP4_multiple_choice(list_of_questions[value], student_answer,multiple_choice_answers, reference_materials)

                                    # st.write(teacher_1_marking_sheet)
                                    # st.markdown("---------------------------")
                                    # st.write(teacher_2_marking_sheet)
                                    # st.markdown("---------------------------")


                                

                                max_retries = 5  # Set a limit for retries
                                retry_count = 0
                                status = "failed"  # Initialize status

                                while status != "success" and retry_count < max_retries:
                                    try:
                                        # Get the verdict from the adjudicators
                                        judge_verdict = get_adjudicators_view(teacher_1_marking_sheet, teacher_2_marking_sheet)

                                        # Extract structured data from the output
                                        structured_extract = [y for y in [x for x in judge_verdict.split('\n') if len(x) > 2][:] if y != "*****"][:4] + [''.join([y for y in [x for x in judge_verdict.split('\n') if len(x) > 2][:] if y != "*****"][4:])]

                                        # Convert to a DataFrame
                                        judge_scorecard_df = pd.DataFrame(structured_extract, columns=["raw_judge_response"])
                                        judge_scorecard_df["heading"] = judge_scorecard_df.iloc[:, 0].str.split(":").str[0]
                                        judge_scorecard_df["value"] = judge_scorecard_df.iloc[:, 0].str.split(":").str[1]
                                        judge_scorecard_df = judge_scorecard_df.drop(columns="raw_judge_response").set_index("heading").T.reset_index().drop(columns="index")
                                        judge_scorecard_df.columns = ['QUESTION', 'STUDENT_ANSWER', 'DECISION', 'MARKS', 'SUGGESTIONS']
                                        
                                        # Set success if everything worked
                                        status = "success"
                                    except (IndexError, AttributeError) as e:  # Catch specific exceptions
                                        retry_count += 1
                                        if retry_count == max_retries:
                                            print(f"Failed after {max_retries} retries due to: {str(e)}")
                                            break  # Break the loop if max retries are reached
                                        continue  # Retry the loop

                                if (judge_scorecard_df["DECISION"].str.lower().values[0]).replace(' ','')!="correct":
                                    st.error("Not quite.")
                                    suggestions_for_student = judge_scorecard_df.SUGGESTIONS.values[0]
                                    st.write_stream(stream_data(suggestions_for_student))

                                    # with tempfile.TemporaryDirectory() as temp_dir:
                                        
                                    #     voice_id = "pFZP5JQG7iQjIQuC4Bku"
                                    #     xi_api_key = SECRET_KEY = st.secrets["elevenlabs"]["SECRET_KEY"]
                                    #     text_for_audio_generation = suggestions_for_student
                                    #     temp_file_path = os.path.join(temp_dir, "output.mp3")

                                    #     # Generate the audio and save it in the temporary file
                                    #     generate_audio_elevenlabs(text_for_audio_generation, voice_id, xi_api_key, file_name=temp_file_path)

                                    #     # Display the audio in Streamlit using the temp file
                                    #     st.audio(temp_file_path, format="audio/mp3")
                                    
                                else:
                                    st.success("Well done!")
                                    suggestions_for_student = judge_scorecard_df.SUGGESTIONS.values[0]
                                    st.write_stream(stream_data(suggestions_for_student))

                                    # with tempfile.TemporaryDirectory() as temp_dir:
                                        
                                    #     voice_id = "pFZP5JQG7iQjIQuC4Bku"
                                    #     xi_api_key = SECRET_KEY = st.secrets["elevenlabs"]["SECRET_KEY"]
                                    #     text_for_audio_generation = suggestions_for_student
                                    #     temp_file_path = os.path.join(temp_dir, "output.mp3")

                                    #     # Generate the audio and save it in the temporary file
                                    #     generate_audio_elevenlabs(text_for_audio_generation, voice_id, xi_api_key, file_name=temp_file_path)

                                    #     # Display the audio in Streamlit using the temp file
                                    #     st.audio(temp_file_path, format="audio/mp3")

        

                                # Add the response to the container 
                                st.session_state.student_response_df_container.append(judge_scorecard_df)
                            else:
                                st.warning("Please provide an answer with more than 5 characters.")
                    else:
                        st.info("This question has already been submitted.")

                # Display all submitted answers
                if False not in st.session_state.submitted:
                    if st.button("Show all submitted answers"):
                        for df in st.session_state.student_response_df_container:
                            output_df = pd.concat(st.session_state.student_response_df_container, ignore_index=True)
                            output_df["MARKS"] = output_df["MARKS"].astype(float)

                        st.write(output_df)

                        st.write(f"you got a total score of: {output_df['MARKS'].sum()}/{len(output_df)}")
                        st.write(f"this means you got {round(((output_df['MARKS'].sum()/len(output_df))*100),2)} % correct !")

                        output_df.to_csv(f"{today}_pop_quiz_{'_'.join(chosen_topics)}_{'_'.join(chosen_transcripts)}_output_df.csv",index=False)

                        # summarise how the student performed in particular have a look the feedback provided. Where are their strengths and where could they improve?

                        overall_summary = get_overall_student_performance_provide_feedback(output_df)

                        st.write_stream(stream_data(overall_summary))


                        


