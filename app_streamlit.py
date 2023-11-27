# import streamlit as st
# import sqlite3
# from hashlib import sha256
# from PIL import Image
# import pytesseract
# from transformers import AutoTokenizer, AutoModelForSequenceClassification
# import torch
# import multiprocessing
# import streamlit as st
# import sqlite3
# from hashlib import sha256
# from PIL import Image
# import pytesseract
# from transformers import pipeline

# # Initialize the QA pipeline
# # nlp = pipeline('question-answering', model="deepset/roberta-base-squad2", tokenizer="deepset/roberta-base-squad2")
# # nlp = pipeline('question-answering', model="distilbert-base-uncased-distilled-squad", tokenizer="distilbert-base-uncased-distilled-squad")
# # Example for using BERT Mini
# nlp = pipeline('question-answering', model="prajjwal1/bert-mini", tokenizer="prajjwal1/bert-mini")


# # Set the start method for multiprocessing
# def set_multiprocessing_start_method():
#     multiprocessing.set_start_method("spawn", force=True)

# # Function to hash passwords
# def hash_password(password):
#     """Hash a password for storing."""
#     return sha256(password.encode()).hexdigest()

# # Function to get a database connection
# def get_db_connection():
#     conn = sqlite3.connect('users.db', check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     return conn

# # Function to register a new user
# def register_user(username, password):
#     conn = get_db_connection()
#     c = conn.cursor()
#     try:
#         c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
#         conn.commit()
#     except sqlite3.IntegrityError:
#         conn.close()
#         return False
#     conn.close()
#     return True

# # Function to check if a user exists and the password is correct
# def check_user(username, password):
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hash_password(password)))
#     user_exists = c.fetchone() is not None
#     conn.close()
#     return user_exists

# # Initialize ClinicalBERT
# # tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
# # model = AutoModelForSequenceClassification.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")

# # Function to extract text from an image using OCR
# def extract_text(image):
#     return pytesseract.image_to_string(image)

# # Function to analyze text using ClinicalBERT
# def analyze_text(text):
#     pass
#     # inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
#     # outputs = model(**inputs)
#     # predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
#     # return predictions

# # Main function to run the Streamlit app
# def run_streamlit_app():
#     st.title('SmartMedScan: Medical Report Analysis')

#     # Registration Form
#     with st.form("Register"):
#         new_username = st.text_input("New Username")
#         new_password = st.text_input("New Password", type="password")
#         register_button = st.form_submit_button(label='Register')
#         if register_button:
#             if register_user(new_username, new_password):
#                 st.success("User registered successfully.")
#             else:
#                 st.error("Username already exists.")

#     # Login Form
#     with st.form("Login"):
#         username = st.text_input("Username")
#         password = st.text_input("Password", type="password")
#         login_button = st.form_submit_button(label='Login')
#         if login_button:
#             if check_user(username, password):
#                 st.success("Logged in successfully.")
#             else:
#                 st.error("Incorrect username or password.")

#     # ClinicalBERT Analysis
#     st.title("Medical Report Analysis with ClinicalBERT")
#     uploaded_image = st.file_uploader("Upload a medical report image", type=["png", "jpg", "jpeg"])

#     if uploaded_image:
#         image = Image.open(uploaded_image)
#         st.image(image, caption='Uploaded Image', use_column_width=True)
#         st.write("Extracting text...")
#         extracted_text = extract_text(image)
#         st.text_area("Extracted Text", extracted_text, height=150)

#         # if st.button('Analyze Report'):
#         #     st.write("Analyzing text...")
#         #     st.header('Report Summary')
#         #     analysis_result = analyze_text(extracted_text)
#         #     st.write(analysis_result)

#         # Question Answering Section
#     st.title("Question Answering with RoBERTa")
#     context = st.text_area("Context", "Enter the context here")
#     question = st.text_input("Question", "What is your question?")

#     if st.button("Get Answer"):
#         if context and question:
#             answer = nlp({'context': context, 'question': question})
#             st.write("Answer:", answer['answer'])
#             pass
#         else:
#             st.warning("Please provide both context and a question.")

# # Check if the script is running as the main program and set multiprocessing start method
# if __name__ == "__main__":
#     set_multiprocessing_start_method()
#     run_streamlit_app()
import streamlit as st
import sqlite3
from hashlib import sha256
from PIL import Image
import pytesseract
from transformers import pipeline

# Set the start method for multiprocessing
import multiprocessing
multiprocessing.set_start_method("spawn", force=True)

# Function to hash passwords
def hash_password(password):
    """Hash a password for storing."""
    return sha256(password.encode()).hexdigest()

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Function to register a new user
def register_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

# Function to check if a user exists and the password is correct
def check_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hash_password(password)))
    user_exists = c.fetchone() is not None
    conn.close()
    return user_exists

# Initialize MiniBERT for Question Answering
nlp = pipeline('question-answering', model="prajjwal1/bert-mini", tokenizer="prajjwal1/bert-mini")

# Function to extract text from an image using OCR
def extract_text(image):
    return pytesseract.image_to_string(image)

# Main function to run the Streamlit app
def run_streamlit_app():
    st.title('SmartMedScan: Medical Report Analysis')

    # Registration Form
    with st.form("Register"):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        register_button = st.form_submit_button(label='Register')
        if register_button:
            if register_user(new_username, new_password):
                st.success("User registered successfully.")
            else:
                st.error("Username already exists.")

    # Login Form
    with st.form("Login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button(label='Login')
        if login_button:
            if check_user(username, password):
                st.success("Logged in successfully.")
            else:
                st.error("Incorrect username or password.")

    # Image Upload and Text Extraction
    st.title("Medical Report Analysis with OCR")
    uploaded_image = st.file_uploader("Upload a medical report image", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption='Uploaded Image', use_column_width=True)
        st.write("Extracting text...")
        extracted_text = extract_text(image)
        st.text_area("Extracted Text", extracted_text, height=150)

    # Question Answering Section
    st.title("Question Answering with MiniBERT")
    context = st.text_area("Context", "Enter the context here")
    question = st.text_input("Question", "What is your question?")
    if st.button("Get Answer"):
        if context and question:
            answer = nlp({'context': context, 'question': question})
            st.write("Answer:", answer['answer'])
        else:
            st.warning("Please provide both context and a question.")

if __name__ == "__main__":
    run_streamlit_app()
