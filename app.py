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
import os

Session(app)
from transformers import T5Tokenizer, T5ForConditionalGeneration
# Set Tesseract path (update this to your Tesseract path)
os.environ['TESSDATA_PREFIX'] = '/Users/ikowsar/anaconda3/envs/flask_env/share/tessdata/'

# Initialize T5 for Summarization
summarization_tokenizer = T5Tokenizer.from_pretrained('t5-small')
summarization_model = T5ForConditionalGeneration.from_pretrained('t5-small')

def is_image_file(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))

def extract_text(image_path):
    try:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image)
    except Exception as e:
        print("Error in OCR extraction:", e)
        return None

def summarize_text(text):
    if len(text.split()) < 5:  # Minimum length check
        return text

    inputs = summarization_tokenizer("summarize: " + text, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = summarization_model.generate(inputs['input_ids'], max_length=150, min_length=40, length_penalty=2.0, num_beams=4, early_stopping=True)
    summary = summarization_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary


# Other functions (hash_password, get_db_connection, register_user, check_user)
# Function to hash passwords
def hash_password(password):
    """Hash a password for storing."""
    return sha256(password.encode()).hexdigest()

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('medical_app_new.db', check_same_thread=False)
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
# def extract_text(image):
#     return pytesseract.image_to_string(image)
def is_image_file(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))

# def extract_text(image_path):
#     try:
#         # Load the image from the file path
#         image = Image.open(image_path)

#         # Convert the image to the expected format
#         if image.format == 'WEBP':
#             image = image.convert('RGB')

#         # Extract text using PyTesseract
#         extracted_text = pytesseract.image_to_string(image)
#         return extracted_text
#     except Exception as e:
#         print("Error in OCR extraction:", e)
#         return "OCR extraction error"

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
        return redirect(url_for('login'))

    # Ensure username is correctly fetched from session
    username = session.get('username')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch patient's ID using username
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    patient_id = cursor.fetchone()['id']

    # Fetch appointments for the logged-in patient
    cursor.execute("""
        SELECT a.date, a.time_slot, d.name, d.specialization 
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ?
    """, (patient_id,))

    appointments = cursor.fetchall()
    print("Patient ID:", patient_id)
    print("Appointments:", appointments)

    conn.close()


    extracted_text = session.get('extracted_text', '')
    summary = session.get('summary', '')
    answer = session.get('answer', '')
    image_path = session.get('image_path', '')

    if request.method == 'POST':
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and is_image_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)

                extracted_text = extract_text(image_path)
                if extracted_text:
                    summary = summarize_text(extracted_text)
                    session['extracted_text'] = extracted_text
                    session['summary'] = summary
                    print("Extracted Text: ", extracted_text)  # Debug print
                    print("Summary: ", summary)  # Debug print
                else:
                    flash('Failed to extract text from image', 'error')
            else:
                flash('Invalid file format', 'error')
        else:
            flash('No file selected', 'error')

    # Add debug prints to check session variables
    print("Session Extracted Text: ", session.get('extracted_text', 'No text'))
    print("Session Summary: ", session.get('summary', 'No summary'))
    session.pop('extracted_text', None)
    session.pop('summary', None)
    return render_template('patient_home.html', 
                           image_path=image_path, 
                           extracted_text=extracted_text, 
                           summary=summary, 
                           answer=answer, 
                           appointments=appointments)

@app.route('/patient_home_test', methods=['GET', 'POST'])
def patient_home_t():

    extracted_text = session.get('extracted_text', '')
    summary = session.get('summary', '')
    answer = session.get('answer', '')
    image_path = session.get('image_path', '')

    if request.method == 'POST':
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and is_image_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)

                extracted_text = extract_text(image_path)
                if extracted_text:
                    summary = summarize_text(extracted_text)
                    session['extracted_text'] = extracted_text
                    session['summary'] = summary
                    print("Extracted Text: ", extracted_text)  # Debug print
                    print("Summary: ", summary)  # Debug print
                else:
                    flash('Failed to extract text from image', 'error')
            else:
                flash('Invalid file format', 'error')
        else:
            flash('No file selected', 'error')

    # Add debug prints to check session variables
    print("Session Extracted Text: ", session.get('extracted_text', 'No text'))
    print("Session Summary: ", session.get('summary', 'No summary'))
    session.pop('extracted_text', None)
    session.pop('summary', None)
    x= jsonify({'extracted_text': extracted_text, 'summary': summary})
    return x

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

    # Ensure the user is logged in and has a patient role
    if 'user_id' not in session:
        flash('Please log in to book an appointment', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Retrieve patient ID from session and other details from the form
        patient_id = session['user_id']
        chosen_time_slot = request.form['time_slot']
        doctor_id = request.form.get('doctor_id')
        appointment_date = datetime.now().date()  # Use current date or a selected date

        # Connect to the database and insert the appointment
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO appointments (patient_id, doctor_id, date, time_slot) VALUES (?, ?, ?, ?)",
                           (patient_id, doctor_id, appointment_date, chosen_time_slot))
            conn.commit()
            flash('Appointment booked successfully!', 'success')
        except sqlite3.Error as e:
            return redirect(url_for('doctors_list'))
        finally:
            conn.close()

        return redirect(url_for('patient_home'))
    # If the form is not submitted, redirect to a relevant page or show a message
    return redirect(url_for('doctors_list'))

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



@app.route('/doctor_home', methods=['GET', 'POST'])
def doctor_home():
    if 'username' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    doctor_username = session.get('username')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch doctor's ID using username
    cursor.execute("SELECT id FROM users WHERE username = ?", (doctor_username,))
    doctor_data = cursor.fetchone()
    # print(doctor_data)
    # Ensure that the doctor data is available
    if doctor_data is None:
        flash("Doctor data not found.", "error")
        return redirect(url_for('login'))

    doctor_id = doctor_data['id']
    print(doctor_id)
    # Fetch booked appointments for the logged-in doctor
    cursor.execute("""
        SELECT id, date, time_slot, patient_id, doctor_id
        FROM appointments
        WHERE doctor_id = ?
    """, (doctor_id,))

    appointments = cursor.fetchall()
    print(appointments)
    conn.close()

    return render_template('doctor_home.html', appointments=appointments)





@app.route('/admin_home')
def admin_home():
    # Ensure the user is logged in and has an admin role
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    # Fetch data to display on the admin dashboard
    # Example: count of users, doctors, and appointments
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM doctors")
    doctors_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM appointments")
    appointments_count = cursor.fetchone()[0]
    conn.close()

    return render_template('admin_home.html', users_count=users_count, doctors_count=doctors_count, appointments_count=appointments_count)


from werkzeug.security import generate_password_hash

def create_password_hash(password):
    return generate_password_hash(password, method='sha256')


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password_hash = generate_password_hash(request.form['password'])
        role = request.form['role']
        email = request.form['email']
        phone = request.form['phone']
        blood_group = request.form['blood_group']
        age = request.form['age']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash, role, email, phone, blood_group, age) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (username, password_hash, role, email, phone, blood_group, int(age)))
        conn.commit()
        conn.close()

        return redirect(url_for('admin_home'))

    # Display the form for adding a user
    return render_template('add_user_form.html')


@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_home'))


@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO doctors (name, specialization) VALUES (?, ?)", (name, specialization))
        conn.commit()
        conn.close()

        return redirect(url_for('admin_home'))

    # Display the form for adding a doctor
    return render_template('add_doctor_form.html')

@app.route('/delete_doctor/<int:doctor_id>')
def delete_doctor(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_home'))


@app.route('/add_appointment', methods=['GET', 'POST'])
def add_appointment():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time_slot = request.form['time_slot']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO appointments (patient_id, doctor_id, date, time_slot) VALUES (?, ?, ?, ?)", 
                       (patient_id, doctor_id, date, time_slot))
        conn.commit()
        conn.close()

        return redirect(url_for('admin_home'))

    # Display the form for adding an appointment
    return render_template('add_appointment_form.html')

@app.route('/delete_appointment/<int:appointment_id>')
def delete_appointment(appointment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_home'))

# Additional routes for specific admin tasks, like managing users, doctors, etc.
# These might include routes for adding/editing/deleting users, viewing detailed reports, etc.




def register_doctor(username, password, name, specialization):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # First, register the user
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'doctor')", (username, hash_password(password)))
        user_id = c.lastrowid  # Fetch the last inserted id

        # Then, add entry to the doctors table
        c.execute("INSERT INTO doctors (user_id, name, specialization) VALUES (?, ?, ?)", (user_id, name, specialization))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

@app.route('/register', methods=['GET', 'POST'])
def register():
    # ... [Existing registration code]

    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']
        role = request.form['role']

        if username_exists(new_username):
            flash("Username already exists.", "error")
            return redirect(url_for('register'))

        if role == 'doctor':
            # Handle doctor registration
            doctor_name = request.form.get('doctor_name')
            specialization = request.form.get('specialization')
            if register_doctor(new_username, new_password, doctor_name, specialization):
                flash("Doctor registered successfully.", "success")
            else:
                flash("Doctor registration failed.", "error")
        else:
            # Handle patient registration
            if register_user(new_username, new_password, role):
                flash("User registered successfully.", "success")
            else:
                flash("Registration failed.", "error")

        return redirect(url_for('login'))

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
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Username or password not provided", "error")
            return render_template('login.html')

        user = check_user(username, password)

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            if user['role'] == 'patient':
                return redirect(url_for('patient_home'))
            elif user['role'] == 'doctor':
                return redirect(url_for('doctor_home'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_home'))
            else:
                flash("Invalid role", "error")
        else:
            flash("Incorrect username or password.", "error")

    return render_template('login.html')





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