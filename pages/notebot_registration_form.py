import streamlit as st
import pandas as pd
import bcrypt
from google.oauth2 import service_account
from PIL import Image
from google.cloud import storage
import jwt  # To generate and decode tokens
import time
import tempfile
from datetime import datetime

current_date = datetime.now()
formatted_date = current_date.strftime("%d-%m-%Y")
simple_date = str(current_date).split(' ')[0]

SECRET_KEY = st.secrets["general"]["SECRET_KEY"]

im = Image.open('slug_logo.png')
st.set_page_config(
    page_title="PSIL",
    page_icon=im,
    initial_sidebar_state="collapsed",
    ) 

def check_if_user_is_existing_user():
    if len(existing_user_list)==0:


        #download the indices from gcs
        blob = bucket.blob("error_existing_user.csv")
        if blob.exists():

            # Download the file to a destination
            blob.download_to_filename(temp_dir+"error_existing_user.csv")
            login_url = pd.read_csv(temp_dir+"error_existing_user.csv").values[0]
            st.markdown(f"this came from GCS:{login_url}")
            existing_user_list.append(login_url)
            st.error(f"{login_url}")
            time.sleep(3)
            # Redirect to external site with the token as a query parameter
            # redirect_url = f"https://psilproject.streamlit.app/psil_login"
            # st.markdown(f"""
            # <meta http-equiv="refresh" content="0; url={redirect_url}">
            # """, unsafe_allow_html=True)
            
        else:
            time.sleep(3)
            pass




# Hash the password
def hash_password(plain_text_password):
    # Generate a salt
    salt = bcrypt.gensalt()
    # Hash the password with the salt
    hashed_password = bcrypt.hashpw(plain_text_password.encode('utf-8'), salt)
    return hashed_password

# Generate JWT token after login
def generate_token(email):
    token = jwt.encode({"email": email}, SECRET_KEY, algorithm="HS256")
    return token

# Login form
st.title("Register form")

email = st.text_input("Email")
if email:
    if "@" in email:
        if ".com" in email or ".ac.uk" in email:
            pass
    else:
        st.markdown("it looks like your email isn't valid. Please try put in another email")
        

confirm_email = st.text_input("Confirm Email")
if email and confirm_email:
    if email != confirm_email:
        st.markdown("please make sure your emails match")


password = st.text_input("Password", type="password")

confirm_password = st.text_input("Confirm Password", type="password")

if password and confirm_password:
    if password != confirm_password:
        st.markdown("please make sure your passwords match!")

# add all the paypal processing here
# this section will handle the paypal payments

# import paypalrestsdk

# paypalrestsdk.configure({
# "mode": "sandbox",  # Use "live" for production
# "client_id": st.secrets["paypal"]["PAYPAL_CLIENT"],
# "client_secret": st.secrets["paypal"]["PAYPAL_CLIENT_SECRET"]
# })
# ---deprecated code below 
# # Get query parameters to check if the user is returning from PayPal
# params = st.experimental_get_query_params()
# payment_id = params.get('paymentId', [None])[0]
# payer_id = params.get('PayerID', [None])[0]



# Get query parameters to check if the user is returning from PayPal
params = st.query_params
payment_id = params.get('paymentId', [None])[0]
payer_id = params.get('PayerID', [None])[0]

# Check if we're handling the payment execution step
if payment_id and payer_id:
    st.info("Processing your payment. Please wait...")
    # Find and execute the payment
    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        st.success("Payment completed successfully!")
        # Retrieve payer's email
        payer_info = payment.payer.payer_info
        payer_email = payer_info.email

    else:
        st.error("Payment execution failed.")
        st.write(payment.error)

else:

    # Display the payment initiation UI
    st.write("Subscribe to access premium features.")
    if st.button("Register"):

        with tempfile.TemporaryDirectory() as temp_dir:



            # upload registration data to user credentials database
            
            credentials_df = pd.DataFrame([email,password]).T
            credentials_df.columns = ["email","pw"]
            credentials_df["hash_pw"] = credentials_df.pw.apply(lambda x: hash_password(x).decode())
            credentials_df["token"] = credentials_df.email.apply(lambda x: generate_token(x))
            credentials_df["registration_date"] = pd.to_datetime(formatted_date,format="%d-%m-%Y")

            # credentials_df.drop(columns="pw",inplace=True)
            # Create credentials object
            credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

            # Use the credentials to create a client
            client = storage.Client(credentials=credentials)


            # The bucket on GCS in which to write the CSV file
            bucket = client.bucket('psil-app-backend-2')
            # The name assigned to the CSV file on GCS
            blob = bucket.blob('new_psil_user_registration.csv')

            # Convert the DataFrame to a CSV string with a specified encoding
            csv_string = credentials_df.to_csv(index=False, encoding='utf-8')

            # Upload the CSV string to GCS
            blob.upload_from_string(csv_string, 'text/csv')

            # check to see if the email address is already registered to the site

            existing_user_list = []

            time.sleep(5)


            check_if_user_is_existing_user()


        # # Create the payment object
        # payment = paypalrestsdk.Payment({
        #     "intent": "sale",
        #     "payer": {
        #         "payment_method": "paypal"
        #     },
        #     "redirect_urls": {
        #         "return_url": "https://psilproject.streamlit.app/psil_login",  # Replace with your app's URL
        #         "cancel_url": "https://psilproject.streamlit.app/psil_registration_form"
        #     },
        #     "transactions": [{
        #         "amount": {
        #             "total": "0.01",
        #             "currency": "GBP"
        #         },
        #         "description": "PSIL - music recommender app subscription"
        #     }]
        # })

        # if payment.create():
        #     st.success("Payment created successfully!")
        #     # Extract approval URL
        #     for link in payment.links:
        #         if link.rel == "approval_url":
        #             approval_url = str(link.href)
        #             # Automatically redirect
        #             st.markdown(f"<meta http-equiv='refresh' content='0; url={approval_url}'>", unsafe_allow_html=True)
        # else:
        #     st.error("Error creating payment")
        #     st.write(payment.error)

        # st.success("Payment created successfully!")

    # if st.button("Register"):
    #     with st.spinner("Processing your registration..."):
    #         with tempfile.TemporaryDirectory() as temp_dir:



    #             # upload registration data to user credentials database
                
    #             credentials_df = pd.DataFrame([email,password]).T
    #             credentials_df.columns = ["email","pw"]
    #             credentials_df["hash_pw"] = credentials_df.pw.apply(lambda x: hash_password(x).decode())
    #             credentials_df["token"] = credentials_df.email.apply(lambda x: generate_token(x))

    #             # credentials_df.drop(columns="pw",inplace=True)
    #             # Create credentials object
    #             credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])

    #             # Use the credentials to create a client
    #             client = storage.Client(credentials=credentials)


    #             # The bucket on GCS in which to write the CSV file
    #             bucket = client.bucket('psil-app-backend-2')
    #             # The name assigned to the CSV file on GCS
    #             blob = bucket.blob('new_psil_user_registration.csv')

    #             # Convert the DataFrame to a CSV string with a specified encoding
    #             csv_string = credentials_df.to_csv(index=False, encoding='utf-8')

    #             # Upload the CSV string to GCS
    #             blob.upload_from_string(csv_string, 'text/csv')

    #             # check to see if the email address is already registered to the site

    #             existing_user_list = []

                # check_if_user_is_existing_user()





# Optionally, handle the cancel URL case
# if 'cancel' in params:
#     st.warning("Payment was cancelled.")

            # # this was the old code before which would direct the user to click the button on the webpage it
            # time.sleep(5)
            st.success("Registration successful!")
            st.markdown("To access your account make a payment using the 'Subscribe' button below")
            st.markdown("\n After we've received your payment you will get a link to the PSIL application in your email.")
            st.markdown("Happy listening!")

            # # Redirect to external site with the token as a query parameter
            # redirect_url = f"https://psilproject.streamlit.app/psil_login"
            # st.markdown(f"""
            # <meta http-equiv="refresh" content="0; url={redirect_url}">
            # """, unsafe_allow_html=True)


