import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
# import sounddevice as sd
# import soundfile as sf
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
import os
import requests











# # Set device (CUDA for GPU, 'cpu' for CPU)
# try:
#   tts.to('cuda')  # or use 'cpu' if no GPU available
# except:
#   tts.to('cpu')

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
            # load the pdf file and iterate through the pages and then join them together in a dataframe
            # process the pdf 
            pdf_page_container = []

            # Read the content of the uploaded file
            pdf_content = uploaded_file.read()

            # Open the PDF from the content
            doc = fitz.open(stream=pdf_content, filetype="pdf")

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text")
                pdf_page_container.append(text)

            # Close the document
            doc.close()

            # join the text from the pdf
            text = " ".join(pdf_page_container)

        with tempfile.TemporaryDirectory() as temp_dir:

            # Generate speech
            output_wav_path = "reader_output.wav"
            text_to_speak = text

            # tts.tts_to_file(text=text_to_speak, file_path=output_wav_path,speed = 1)
            # we're going to use the API instead for the reader
            model_api = st.secrets["voice_models"]["model_api"]
            audio_resp = requests.post(
                                        model_api,
                                        json={"text": str(text_to_speak)}
                                    )
            # save the audio file to the output path
            with open(output_wav_path, "wb") as f:
                f.write(audio_resp.content)

            # st.write(f"Speech saved to {output_wav_path}")

            # play the audio
            # audio = AudioSegment.from_wav(output_wav_path)
            st.audio(output_wav_path)