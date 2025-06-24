import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
# import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import time
# from gtts import gTTS
import collections
import threading
import queue
import base64
# from pydub import AudioSegment
# from TTS.api import TTS
import fitz  # PyMuPDF
import os
import requests
from pathlib import Path




def tts_to_file(
                    text: str,
                    api_url: str,
                    out_path: str | Path = "output.wav",
                    *,
                    connect_timeout: float = 8.0,     # seconds to establish TCP/TLS
                    read_timeout: float | None = 300  # seconds to wait for data; None = no limit
                ) -> Path:
    """
    Send text to a TTS endpoint and stream the resulting audio to `out_path`.
    Returns the Path to the written file or raises `requests.HTTPError`.
    """
    payload = {"text": text}
    timeouts = (connect_timeout, read_timeout)

    with requests.post(api_url, json=payload, stream=True, timeout=timeouts) as resp:
        resp.raise_for_status()        # bubble up 4xx/5xx early

        out_path = Path(out_path).expanduser()
        with out_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:              # skip keep-alive chunks
                    f.write(chunk)

    return out_path





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
            wav_list = []

            with tempfile.TemporaryDirectory() as temp_dir:

                # Generate speech
                output_wav_path = "reader_output.wav"
                # text_to_speak = text

                # tts.tts_to_file(text=text_to_speak, file_path=output_wav_path,speed = 1)
                # we're going to use the API instead for the reader
                
                model_api = st.secrets["voice_models"]["model_api"]
                counter = 0
                for text_to_speak in pdf_page_container[:2]:
                    audio_resp = requests.post(
                                                model_api,
                                                json={"text": text_to_speak[:100]},
                                                timeout=600
                                            )
                    output_wav_path = f"reader_output_{counter}.wav"
                    with open(output_wav_path, "wb") as f:
                        f.write(audio_resp.content)
                        time.sleep(2)
                        wav, _ = sf.read(output_wav_path, dtype="float64")  # 44 100 Hz

                        counter += 1
                        wav_list.append(wav)
                
                # audio_resp = tts_to_file(text=text_to_speak, api_url=model_api, out_path=output_wav_path)
                # st.audio(audio_resp)

            combined_wav = np.concatenate(wav_list)
            output_wav_path = "reader_output.wav"
            with open(output_wav_path, "wb") as f:
                sf.write(f, combined_wav, 22050)
                
            st.audio(output_wav_path)   



                # # save the audio file to the output path
                # with open(output_wav_path, "wb") as f:
                #     f.write(audio_resp.content)

                # # st.write(f"Speech saved to {output_wav_path}")

                # # play the audio
                # # audio = AudioSegment.from_wav(output_wav_path)
                # st.audio(output_wav_path)