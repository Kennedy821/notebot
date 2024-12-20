import streamlit as st
import jwt  # To generate and decode tokens
import bcrypt
from google.oauth2 import service_account
from PIL import Image
from google.cloud import storage
import pandas as pd
import time
import tempfile

print(jwt.__version__)
SECRET_KEY = st.secrets["general"]["SECRET_KEY"]
bucket_name = st.secrets["gcp_bucket"]["application_bucket"]

im = Image.open('slug_logo.png')
st.set_page_config(
    page_title="Notebot",
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

                credentials_df = pd.DataFrame([email,password]).T
                credentials_df.columns = ["email","pw"]


                # Create credentials object
                credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

                # Use the credentials to create a client
                client = storage.Client(credentials=credentials)


                # The bucket on GCS in which to write the CSV file
                bucket = client.bucket(bucket_name)
                # The name assigned to the CSV file on GCS
                blob = bucket.blob('user_login_request.csv')

                # Convert the DataFrame to a CSV string with a specified encoding
                csv_string = credentials_df.to_csv(index=False, encoding='utf-8')

                # Upload the CSV string to GCS
                blob.upload_from_string(csv_string, 'text/csv')


                # wait for the valid url to appear in the bucket
                redirect_url = []
                get_login_credentials_for_valid_user()
                time.sleep(5)
                if len(redirect_url)>0:
                    # st.markdown(redirect_url)
                    redirect_url = str(redirect_url[0]).split(" ")[1]
                    # st.markdown(redirect_url)




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
