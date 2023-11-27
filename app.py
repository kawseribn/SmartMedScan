from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import sqlite3
from hashlib import sha256
import pytesseract
from PIL import Image
from transformers import pipeline
import io
from werkzeug.utils import secure_filename
import os
from flask_session import Session

app = Flask(__name__)
# app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for security purposes
# app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder to store uploaded images
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max upload size, here it's set to 16MB
# Configure Flask-Session or other session settings if needed
app.config['SESSION_TYPE'] = 'filesystem'  # Example for using file-based sessions

Session(app)

# Initialize MiniBERT for Question Answering
# qa_pipeline = pipeline('question-answering', model="prajjwal1/bert-mini", tokenizer="prajjwal1/bert-mini")
# qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
nlp = pipeline('question-answering', model="prajjwal1/bert-mini", tokenizer="prajjwal1/bert-mini")

# Other functions (hash_password, get_db_connection, register_user, check_user)
# Function to hash passwords
def hash_password(password):
    """Hash a password for storing."""
    return sha256(password.encode()).hexdigest()

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('medical_app.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def register_user(username, password, role):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, hash_password(password), role))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

def username_exists(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    exists = c.fetchone() is not None
    conn.close()
    return exists


# Function to check if a user exists and the password is correct
def check_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users WHERE username = ? AND password_hash = ?", (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user if user else None



# Function to extract text from an image using OCR
def extract_text(image):
    return pytesseract.image_to_string(image)


def get_current_user_details():
    username = session.get('username')
    if not username:
        return None

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_details = c.fetchone()
    conn.close()

    return user_details

def update_user_details(username, email, phone, blood_group, age):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET email = ?, phone = ?, blood_group = ?, age = ? WHERE username = ?", (email, phone, blood_group, age, username))
    conn.commit()
    conn.close()

@app.route('/patient_profile', methods=['GET', 'POST'])
def patient_profile():
    user_data = get_current_user_details()

    if request.method == 'POST':
        # Logic to handle profile update
        email = request.form.get('email')
        phone = request.form.get('phone')
        blood_group = request.form.get('blood_group')
        age = request.form.get('age')

        update_user_details(session['username'], email, phone, blood_group, age)
        flash('Profile updated successfully', 'success')
        return redirect(url_for('patient_home'))

    return render_template('patient_profile.html', user_data=user_data)



@app.route('/patient_home', methods=['GET', 'POST'])
def patient_home():
    if 'username' not in session or session.get('role') != 'patient':
        # User not logged in as patient, redirect to login
        return redirect(url_for('login'))
    
    username = session.get('username')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve patient's ID based on username
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    patient_id = cursor.fetchone()['id']
    # Query to retrieve booked appointments for the logged-in patient
    cursor.execute("""
        SELECT a.date, a.time_slot, d.name, d.specialization 
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ?
    """, (patient_id,))
    
    appointments = cursor.fetchall()
    conn.close()

    extracted_text = session.get('extracted_text', '')
    answer = session.get('answer', '')
    image_path = session.get('image_path', '')

    if request.method == 'POST':
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                filename = secure_filename(image_file.filename)
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(full_path)
                session['image_path'] = filename  # Store just the filename
                session.pop('extracted_text', None)  # Clear previous extracted text
                session.pop('answer', None)  # Clear previous answer

        if 'extract_text' in request.form and image_path:
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
            try:
                image = Image.open(full_path)
                extracted_text = extract_text(image)
                print(extracted_text)
                session['extracted_text'] = extracted_text
                session.pop('answer', None)  # Clear previous answer
            except Exception as e:
                print("Error in extraction:", e)

        elif 'ask_question' in request.form and extracted_text:
            question = request.form['question']
            if question:
                answer = nlp({'question': question, 'context': extracted_text})['answer']
                session['answer'] = answer

    return render_template('patient_home.html', 
                           image_path=image_path, 
                           extracted_text=extracted_text, 
                           answer=answer, appointments=appointments)

def get_doctors_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors")  # Modify query based on your database schema
    doctors = cursor.fetchall()
    conn.close()
    return doctors


# @app.route('/doctors_list')
# def doctors_list():
#     # Logic to retrieve doctors' information from the database
#     doctors = get_doctors_list()  # You need to define this function

#     return render_template('doctors_list.html', doctors=doctors)

def get_doctors_by_specialization(specialization):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors WHERE specialization = ?", (specialization,))
    doctors = cursor.fetchall()
    conn.close()
    return doctors

def get_all_doctors():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors")  # Adjust the query based on your database schema
    doctors = cursor.fetchall()
    conn.close()
    return doctors


@app.route('/doctors_list', methods=['GET'])
def doctors_list():
    specialization_query = request.args.get('specialization')
    
    # Assuming a function that gets doctors based on specialization
    doctors = get_doctors_by_specialization(specialization_query) if specialization_query else get_all_doctors()

    return render_template('doctors_list.html', doctors=doctors)

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    from datetime import datetime
    # Check if user_id is in session
    if 'user_id' not in session:
        flash('Please log in to book an appointment', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        patient_id = session['user_id']
        chosen_time_slot = request.form['time_slot']
        doctor_id = request.form.get('doctor_id')
        appointment_date = datetime.now().date()  # Get today's date


        # Save the appointment in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO appointments (doctor_id, patient_id, time_slot, date) VALUES (?, ?, ?, ?)",
                       (doctor_id, patient_id, chosen_time_slot, appointment_date))
        conn.commit()
        conn.close()

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient_home'))

    # Retrieve doctor details and available time slots
    doctor = get_doctor_details(doctor_id)
    time_slots = get_available_time_slots(doctor_id)

    return render_template('book_appointment.html', doctor=doctor, time_slots=time_slots)

def get_doctor_details(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
    doctor = cursor.fetchone()
    conn.close()
    return doctor
@app.route('/get_time_slots/<int:doctor_id>')
def get_time_slots(doctor_id):
    # Assuming get_available_time_slots is a function that returns available time slots for a doctor
    time_slots = get_available_time_slots(doctor_id)
    return jsonify(time_slots)

@app.route('/get_available_time_slots/<int:doctor_id>')
def get_available_time_slots(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT time_slot FROM time_slots")
    all_slots = [slot['time_slot'] for slot in cursor.fetchall()]

    cursor.execute("SELECT time_slot FROM appointments WHERE doctor_id = ? AND date = CURRENT_DATE", (doctor_id,))
    booked_slots = [slot['time_slot'] for slot in cursor.fetchall()]

    available_slots = list(set(all_slots) - set(booked_slots))
    # print((available_slots))
    conn.close()
    test_slots = ['09:00', '10:00']
    return jsonify(test_slots)
    # return jsonify({"available_slots": "success"})



@app.route('/doctor_home')
def doctor_home():
    # Add logic specific to doctor home page
    return render_template('doctor_home.html')

@app.route('/admin_home')
def admin_home():
    # Add logic specific to admin home page
    return render_template('admin_home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Username or password not provided", "error")
            return redirect(url_for('login'))

        user = check_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('redirect_to_home'))
        else:
            flash("Incorrect username or password.", "error")

    return render_template('login.html')





@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']
        role = request.form['role']

        # Check if the username already exists
        if username_exists(new_username):
            flash("Username already exists.", "error")
            return redirect(url_for('register'))

        if register_user(new_username, new_password, role):
            flash("User registered successfully.", "success")
            return redirect(url_for('login'))
        else:
            flash("Registration failed.", "error")

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# ... [previous imports and setup]
@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    if role == 'patient':
        return redirect(url_for('patient_home'))
    elif role == 'doctor':
        return redirect(url_for('doctor_home'))
    elif role == 'admin':
        return redirect(url_for('admin_home'))
    else:
        return "Unauthorized Access"

@app.route('/redirect_to_home')
def redirect_to_home():
    role = session.get('role')
    print('role', role)
    if role == 'patient':
        return redirect(url_for('patient_home'))
    elif role == 'doctor':
        return redirect(url_for('doctor_home'))
    elif role == 'admin':
        return redirect(url_for('admin_home'))
    else:
        # Role is not set, redirect to login
        return redirect(url_for('login'))

# @app.route('/home', methods=['GET', 'POST'])
# def home():
#     if 'username' not in session:
#         return redirect(url_for('login'))

#     role = session.get('role')
#     extracted_text = session.get('extracted_text')  # Get extracted text if available
#     answer = None
#     image_path = session.get('image_path')  # Get image path if available

#     if request.method == 'POST':
#         if 'extract_text' in request.form and image_path:
#             image = Image.open(image_path)
#             extracted_text = extract_text(image)
#             session['extracted_text'] = extracted_text  # Store extracted text in session

#         elif 'image' in request.files:
#             image_file = request.files['image']
#             if image_file:
#                 filename = secure_filename(image_file.filename)
#                 image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 image_file.save(image_path)
#                 session['image_path'] = image_path
#                 session.pop('extracted_text', None)  # Clear previous extracted text

#         elif 'ask_question' in request.form and extracted_text:
#             question = request.form['question']
#             answer = nlp({'context': extracted_text, 'question': question})['answer']

#     # Render different templates based on user role
#     if role == 'patient':
#         return render_template('patient_home.html', image_path=image_path, extracted_text=extracted_text, answer=answer)
#     elif role == 'doctor':
#         return render_template('doctor_home.html')  # Pass any necessary data
#     elif role == 'admin':
#         return render_template('admin_home.html')  # Pass any necessary data
#     else:
#         return "Unauthorized Access"



# ... [rest of the code including login and logout routes]

if __name__ == '__main__':
    app.run(debug=True)