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













# Load the TTS model 
model_path = "/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/project_siren/tts_model_vanilla/best_model_420645.pth"
config_path = "/Users/tariromashongamhende/Documents/Documents - Tariro’s MacBook Pro/ml_projects/project_siren/tts_model_vanilla/config_tts.json"

tts = TTS(model_path=model_path, config_path=config_path)
base_dir = "/Users/tariromashongamhende/Downloads/combination_bea/"
speaker_samples = [base_dir+x for x in os.listdir(base_dir) if "DS" not in x][:]
speaker_samples
# Set device (CUDA for GPU, 'cpu' for CPU)
try:
  tts.to('cuda')  # or use 'cpu' if no GPU available
except:
  tts.to('cpu')

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

            tts.tts_with_vc_to_file(
                text_to_speak,
                speaker_wav=speaker_samples[:500],
                file_path=output_wav_path,
            )

            # st.write(f"Speech saved to {output_wav_path}")

            # play the audio
            # audio = AudioSegment.from_wav(output_wav_path)
            st.audio(output_wav_path)