import streamlit as st
import jwt  # To generate and decode tokens
import bcrypt
from google.oauth2 import service_account
from PIL import Image
from google.cloud import storage
import pandas as pd
import time
import tempfile
import requests

print(jwt.__version__)
SECRET_KEY = st.secrets["general"]["SECRET_KEY"]
bucket_name = st.secrets["gcp_bucket"]["application_bucket"]

im = Image.open('slug_logo.png')
st.set_page_config(
    page_title="Login",
    page_icon=im,
    initial_sidebar_state="collapsed",
    ) 
st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: none
    }
</style>
""",
    unsafe_allow_html=True,
)



def get_login_credentials_for_valid_user():
    while len(redirect_url)==0:


        #download the indices from gcs
        blob = bucket.blob("login_url_data.csv")
        if blob.exists():

            # Download the file to a destination
            blob.download_to_filename(temp_dir+"login_url_data.csv")
            login_url = pd.read_csv(temp_dir+"login_url_data.csv").values[0]
            redirect_url.append(login_url)

            break
        else:
            time.sleep(1)


# Simulate user authentication
def authenticate_user(email, password):
    if email == "test@test.com" and password == "password123":
        return True
    return False

# Generate JWT token after login
def generate_token(email):
    token = jwt.encode({"email": email}, SECRET_KEY, algorithm="HS256")
    return token

# Decode and verify JWT token
def verify_token(token):
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded_token
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token
# Hash the password
def hash_password(plain_text_password):
    # Generate a salt
    salt = bcrypt.gensalt()
    # Hash the password with the salt
    hashed_password = bcrypt.hashpw(plain_text_password.encode('utf-8'), salt)
    return hashed_password
    
def check_password(stored_hashed_password, plain_text_password):
    # Check the provided password against the stored hashed password
    return bcrypt.checkpw(plain_text_password.encode('utf-8'), stored_hashed_password)

# Login form
st.title("Login")
email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login"):
    with st.spinner():
        try:

            with tempfile.TemporaryDirectory() as temp_dir:

                payload = {"website": "notebot",
                        "email": email,
                        "pw":password}
                base_api_web_address = st.secrets["general"]["base_api_web_address"]
                r = requests.post(base_api_web_address+"/get_login_verification_for_user", json=payload, timeout=120)
                if r.ok:
                    redirect_url = r.json()["redirect_url"]


                    time.sleep(5)




                    # token = generate_token(email)  # Generate token after login
                    st.success("Login successful!")
                    
                    # # Redirect to external site with the token as a query parameter
                    # redirect_url = f"https://psilproject.streamlit.app/research_app_gcs_login?token={token}"
                    st.markdown(f"""
                    <meta http-equiv="refresh" content="0; url={redirect_url}">
                    """, unsafe_allow_html=True)



                    # token = generate_token(email)  # Generate token after login
                    st.success("Login successful!")
                    

                    st.markdown(f"""
                    <meta http-equiv="refresh" content="0; url={redirect_url}">
                    """, unsafe_allow_html=True)
                else:
                    st.error("It looks like your login credentials aren't correct or you're either not registered")
                    st.write("redirecting you to our registration page...")
                    time.sleep(10)

                    redirect_url = f"https://notebot.streamlit.app/notebot_registration_form"
                    st.markdown(f"""
                    <meta http-equiv="refresh" content="0; url={redirect_url}">
                    """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"error: {e}")

# comments placeholder