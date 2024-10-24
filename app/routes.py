from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, logout_user, current_user
from .forms import LoginForm  # Import the form
from flask_bcrypt import Bcrypt
import psycopg2
import os
from .models import User
import datetime
from flask import Blueprint, current_app

main = Blueprint('main', __name__)
bcrypt = Bcrypt()

# Establish database connection
connection = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    database=os.getenv('DB_NAME', 'hospital_db'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', '')
)
cursor = connection.cursor()

@main.route('/')
@main.route('/home')
def home():
    return render_template('home.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        name = request.form['name']

        # Hash the password using bcrypt
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        print(f"Inserting user with hashed password: {hashed_password}")

        # Store the hashed password in the database
        cursor.execute("""
            INSERT INTO users (username, name, email, password, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, name, email, hashed_password, role))
        
        connection.commit()
        flash('Your account has been created! You can now log in', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        role = form.role.data.lower()
        username = form.username.data
        password = form.password.data

        # Fetch the user from the database
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(%s) AND LOWER(role) = LOWER(%s)", (username, role.lower()))
        user = cursor.fetchone()

        if user:
            print(f"User fetched: {user}")  # Debugging
            print(f"User role fetched: {user[5]}")  # Debugging role

            if bcrypt.check_password_hash(user[4], password):
                user_obj = User(id=user[0], username=user[1], email=user[3], password=user[4], role=user[5])
                print(f"Logged in user role: {user_obj.role}")
                login_user(user_obj)

                # Redirect based on role
                if user_obj.role == 'admin':
                    return redirect(url_for('main.admin_dashboard'))
                elif user_obj.role == 'doctor':
                    return redirect(url_for('main.doctor_dashboard'))
                elif user_obj.role == 'patient':
                    return redirect(url_for('main.patient_dashboard'))
                elif user_obj.role == 'ambulance':
                    return redirect(url_for('main.ambulance_dashboard'))
                elif user_obj.role == 'medical_store':
                    return redirect(url_for('main.medical_store_dashboard'))
                elif user_obj.role in ['nurse', 'staff']:
                    return redirect(url_for('main.nurse_dashboard'))
                else:
                    flash('Unauthorized role. Please contact support.', 'danger')
                    return redirect(url_for('main.home'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        else:
            flash('Username does not exist. Please check your username.', 'danger')

    return render_template('login.html', form=form)

@main.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # Logic for sending password reset instructions to the user's email
        flash('If your email is registered, you will receive password reset instructions.', 'info')
        return redirect(url_for('main.login'))
    return render_template('forgot_password.html')

@main.route('/forgot_username', methods=['GET', 'POST'])
def forgot_username():
    if request.method == 'POST':  # Corrected the line here
        email = request.form['email']
        # Logic for sending username recovery instructions to the user's email
        flash('If your email is registered, you will receive your username.', 'info')
        return redirect(url_for('main.login'))
    return render_template('forgot_username.html')

@main.route('/admin_dashboard')
@login_required
def admin_dashboard():
    print(f"Current user role in admin_dashboard: {current_user.role}")  # Debugging

    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))  # Fixed infinite redirect loop

    # Fetch and display admin data if the user is authorized
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.execute("SELECT * FROM hospitals")
    hospitals = cursor.fetchall()
    cursor.execute("SELECT * FROM appointments")
    appointments = cursor.fetchall()
    return render_template('admin_dashboard.html', users=users, hospitals=hospitals, appointments=appointments)


@main.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))
    cursor.execute("SELECT * FROM appointments WHERE doctor_id = %s", (current_user.id,))
    appointments = cursor.fetchall()
    return render_template('doctor_dashboard.html', appointments=appointments)

@main.route('/patient_records')
@login_required
def patient_records():
    # Fetch patient records from the database
    cursor.execute("SELECT name, age, disease, blood_group, email FROM patients")
    patients = cursor.fetchall()

    # Render the template to display patient records
    return render_template('patient_records.html', patients=patients)

@main.route('/patient_dashboard')
@login_required
def patient_dashboard():
    return render_template('patient_dashboard.html')


@main.route('/ambulance_dashboard')
@login_required
def ambulance_dashboard():
    if current_user.role != 'ambulance':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))
    cursor.execute("SELECT * FROM ambulance_bookings")
    bookings = cursor.fetchall()
    return render_template('ambulance_dashboard.html', bookings=bookings)

@main.route('/medical_store_dashboard')
@login_required
def medical_store_dashboard():
    if current_user.role != 'medical_store':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))
    
    try:
        # Fetch medical orders
        cursor.execute("SELECT * FROM medical_orders")
        orders = cursor.fetchall()

        return render_template('medical_store_dashboard.html', orders=orders)

    except psycopg2.Error as e:
        # Roll back the transaction if there's an error
        connection.rollback()
        flash(f"Database error: {e}", 'danger')
        return redirect(url_for('main.home'))


@main.route('/nurse_dashboard')
@login_required
def nurse_dashboard():
    if current_user.role not in ['nurse', 'staff']:
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))
    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()
    return render_template('nurse_dashboard.html', patients=patients)

@main.route('/reports_analytics_dashboard')
@login_required
def reports_analytics_dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))
    # Fetch data for reports and analytics
    return render_template('reports_analytics_dashboard.html')

@main.route('/notifications_dashboard')
@login_required
def notifications_dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch active notifications
    cursor.execute("SELECT * FROM notifications WHERE is_active = TRUE")
    notifications = cursor.fetchall()

    return render_template('notifications_dashboard.html', notifications=notifications)

@main.route('/notifications')
@login_required
def notifications():
    if current_user.role not in ['admin', 'doctor', 'patient', 'nurse','ambulance','medical store']:
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch notifications from the database
    cursor.execute("SELECT * FROM notifications WHERE is_active = TRUE")
    notifications = cursor.fetchall()

    # Render the notifications.html template, passing the notifications data
    return render_template('notifications.html', notifications=notifications)


@main.route('/manage_users')
@login_required
def manage_users():
    # Make sure only admins can access this route
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.home'))

    # Fetch user details from the database
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    return render_template('manage_users.html', users=users)


@main.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    # Only allow admin to edit users
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the user from the database
    cursor.execute("SELECT id, username, email, role FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        # Update the user details based on form submission
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']

        cursor.execute("""
            UPDATE users 
            SET username = %s, email = %s, role = %s 
            WHERE id = %s
        """, (username, email, role, user_id))
        connection.commit()

        flash('User updated successfully!', 'success')
        return redirect(url_for('main.manage_users'))

    return render_template('edit_user.html', user=user)

@main.route('/delete_user/<int:user_id>', methods=['POST', 'GET'])
@login_required
def delete_user(user_id):
    # Only allow admin to delete users
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    connection.commit()

    flash('User deleted successfully!', 'success')
    return redirect(url_for('main.manage_users'))


@main.route('/manage_hospitals')
@login_required
def manage_hospitals():
    # Check if the current user is an admin
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch all hospitals from the database
    cursor.execute("SELECT id, name, location, services, rating FROM hospitals")
    hospitals = cursor.fetchall()  # This will return a list of tuples with hospital details

    # Render the manage_hospitals.html template, passing the hospitals data
    return render_template('manage_hospitals.html', hospitals=hospitals)


@main.route('/edit_hospital/<int:hospital_id>', methods=['GET', 'POST'])
@login_required
def edit_hospital(hospital_id):
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the hospital details from the database
    cursor.execute("SELECT id, name, location, services, rating FROM hospitals WHERE id = %s", (hospital_id,))
    hospital = cursor.fetchone()

    if request.method == 'POST':
        # Update the hospital details based on form submission
        name = request.form['name']
        location = request.form['location']
        services = request.form['services']
        rating = request.form['rating']

        cursor.execute("""
            UPDATE hospitals 
            SET name = %s, location = %s, services = %s, rating = %s
            WHERE id = %s
        """, (name, location, services, rating, hospital_id))
        connection.commit()

        flash('Hospital updated successfully!', 'success')
        return redirect(url_for('main.manage_hospitals'))

    return render_template('edit_hospital.html', hospital=hospital)

@main.route('/delete_hospital/<int:hospital_id>', methods=['POST', 'GET'])
@login_required
def delete_hospital(hospital_id):
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    cursor.execute("DELETE FROM hospitals WHERE id = %s", (hospital_id,))
    connection.commit()

    flash('Hospital deleted successfully!', 'success')
    return redirect(url_for('main.manage_hospitals'))

@main.route('/appointment_overview')
@login_required
def appointment_overview():
    if current_user.role != 'admin':  # Only allow admin access
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch all appointments from the database
    cursor.execute("SELECT * FROM appointments")
    appointments = cursor.fetchall()

    # Render the appointment_overview.html template with the appointments data
    return render_template('appointment_overview.html', appointments=appointments)

@main.route('/resource_allocation')
@login_required
def resource_allocation():
    # Check if the current user is an admin
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch resource allocation details from the database (adjust this logic as needed)
    cursor.execute("SELECT * FROM resource_allocation")
    resources = cursor.fetchall()

    # Render the resource_allocation.html template with the resource data
    return render_template('resource_allocation.html', resources=resources)

@main.route('/update_resource/<int:resource_id>', methods=['GET', 'POST'])
@login_required
def update_resource(resource_id):
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the resource details
    cursor.execute("SELECT * FROM resource_allocation WHERE id = %s", (resource_id,))
    resource = cursor.fetchone()

    if request.method == 'POST':
        # Update the resource allocation status
        new_status = request.form['allocation_status']
        cursor.execute("""
            UPDATE resource_allocation 
            SET allocation_status = %s 
            WHERE id = %s
        """, (new_status, resource_id))
        connection.commit()

        flash('Resource status updated successfully!', 'success')
        return redirect(url_for('main.resource_allocation'))

    return render_template('update_resource.html', resource=resource)

@main.route('/prescription_management')
@login_required
def prescription_management():
    try:
        # Fetch prescriptions from the database
        cursor.execute("""
            SELECT p.prescription_id, p.medicines, p.instructions, u.username AS doctor_name, pat.name AS patient_name 
            FROM prescriptions p
            JOIN users u ON p.doctor_id = u.id
            JOIN patients pat ON p.patient_id = pat.patient_id
        """)
        prescriptions = cursor.fetchall()

        # Render the template to manage prescriptions
        return render_template('prescription_management.html', prescriptions=prescriptions)

    except psycopg2.Error as e:
        # If an error occurs, rollback the transaction
        connection.rollback()
        # Log or print the error for debugging
        print(f"Database error: {e}")
        flash('An error occurred while fetching prescriptions.', 'danger')
        return redirect(url_for('main.home'))


@main.route('/otp_verification', methods=['GET', 'POST'])
@login_required
def otp_verification():
    if request.method == 'POST':
        otp_code = request.form.get('otp_code')
        user_id = current_user.id

        # Logic to verify OTP for the current user
        cursor.execute("""
            SELECT * FROM otp_verifications 
            WHERE user_id = %s AND otp_code = %s AND expires_at > NOW() AND verified = FALSE
        """, (user_id, otp_code))
        
        otp_record = cursor.fetchone()
        if otp_record:
            # Mark OTP as verified
            cursor.execute("""
                UPDATE otp_verifications SET verified = TRUE WHERE id = %s
            """, (otp_record[0],))
            connection.commit()
            flash('OTP verified successfully!', 'success')
        else:
            flash('Invalid or expired OTP.', 'danger')

        return redirect(url_for('main.otp_verification'))

    return render_template('otp_verification.html')

@main.route('/consultation_notes')
@login_required
def consultation_notes():
    if current_user.role != 'doctor':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch consultation notes for the logged-in doctor
    cursor.execute("""
        SELECT cn.note_id, cn.note_content, u.username AS doctor_name, p.name AS patient_name, cn.timestamp 
        FROM consultation_notes cn
        JOIN users u ON cn.doctor_id = u.id
        JOIN patients p ON cn.patient_id = p.patient_id  -- Use patient_id instead of id
    """)
    notes = cursor.fetchall()

    return render_template('consultation_notes.html', notes=notes)


@main.route('/add_consultation_note/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def add_consultation_note(patient_id):
    if current_user.role != 'doctor':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        note_content = request.form['note_content']

        # Insert new consultation note into the database
        cursor.execute("""
            INSERT INTO consultation_notes (doctor_id, patient_id, note_content, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (current_user.id, patient_id, note_content, datetime.utcnow()))
        connection.commit()

        flash('Consultation note added successfully!', 'success')
        return redirect(url_for('main.consultation_notes'))

    # Fetch the patient info for display
    cursor.execute("SELECT name FROM patients WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()

    return render_template('add_consultation_note.html', patient=patient)


@main.route('/edit_consultation_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_consultation_note(note_id):
    if current_user.role != 'doctor':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the note details
    cursor.execute("SELECT note_content FROM consultation_notes WHERE note_id = %s", (note_id,))
    note = cursor.fetchone()

    if request.method == 'POST':
        updated_content = request.form['note_content']

        # Update the consultation note
        cursor.execute("""
            UPDATE consultation_notes 
            SET note_content = %s, timestamp = %s 
            WHERE note_id = %s
        """, (updated_content, datetime.utcnow(), note_id))
        connection.commit()

        flash('Consultation note updated successfully!', 'success')
        return redirect(url_for('main.consultation_notes'))

    return render_template('edit_consultation_note.html', note=note)


@main.route('/delete_consultation_note/<int:note_id>', methods=['POST'])
@login_required
def delete_consultation_note(note_id):
    if current_user.role != 'doctor':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Delete the consultation note
    cursor.execute("DELETE FROM consultation_notes WHERE note_id = %s", (note_id,))
    connection.commit()

    flash('Consultation note deleted successfully!', 'success')
    return redirect(url_for('main.consultation_notes'))

@main.route('/availability_calendar', methods=['GET', 'POST'])
@login_required
def availability_calendar():
    if current_user.role != 'doctor':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the doctor's availability from the database
    cursor.execute("SELECT * FROM availability WHERE doctor_id = %s ORDER BY date, time", (current_user.id,))
    availability = cursor.fetchall()

    if request.method == 'POST':
        # Get the form data from the POST request
        date = request.form['date']
        time = request.form['time']
        status = request.form['status']

        # Insert new availability entry for the doctor
        cursor.execute("""
            INSERT INTO availability (doctor_id, date, time, status) 
            VALUES (%s, %s, %s, %s)
        """, (current_user.id, date, time, status))
        connection.commit()

        flash('Availability updated successfully!', 'success')
        return redirect(url_for('main.availability_calendar'))

    return render_template('availability_calendar.html', availability=availability)

@main.route('/edit_availability/<int:availability_id>', methods=['GET', 'POST'])
@login_required
def edit_availability(availability_id):
    if current_user.role != 'doctor':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the availability entry by ID
    cursor.execute("SELECT * FROM availability WHERE id = %s", (availability_id,))
    availability = cursor.fetchone()

    if request.method == 'POST':
        # Update the entry with new data
        date = request.form['date']
        time = request.form['time']
        status = request.form['status']

        cursor.execute("""
            UPDATE availability
            SET date = %s, time = %s, status = %s
            WHERE id = %s
        """, (date, time, status, availability_id))
        connection.commit()

        flash('Availability updated successfully!', 'success')
        return redirect(url_for('main.availability_calendar'))

    return render_template('edit_availability.html', availability=availability)

@main.route('/profile_management', methods=['GET', 'POST'])
@login_required
def profile_management():
    user_id = current_user.id
    cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Update user info in the database
        if password:  # If the password is provided, hash and update it
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("""
                UPDATE users 
                SET username = %s, email = %s, password = %s 
                WHERE id = %s
            """, (username, email, hashed_password, user_id))
        else:  # If no password is provided, just update the username and email
            cursor.execute("""
                UPDATE users 
                SET username = %s, email = %s
                WHERE id = %s
            """, (username, email, user_id))

        connection.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile_management'))

    return render_template('profile_management.html', user=user)

@main.route('/search_hospitals', methods=['GET', 'POST'])
@login_required
def search_hospitals():
    if request.method == 'POST':
        # Fetch search criteria from the form
        location = request.form.get('location')
        services = request.form.get('services')

        # Query the hospitals based on search criteria
        cursor.execute("""
            SELECT * FROM hospitals 
            WHERE location ILIKE %s AND services ILIKE %s
        """, ('%' + location + '%', '%' + services + '%'))

        hospitals = cursor.fetchall()

        return render_template('search_results.html', hospitals=hospitals)

    return render_template('search_hospitals.html')

@main.route('/book_appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if request.method == 'POST':
        patient_id = current_user.id  # Assuming the patient is the logged-in user
        doctor_id = request.form['doctor_id']  # Get doctor_id from the form
        hospital_id = request.form['hospital_id']  # Get hospital_id from the form
        appointment_date = request.form['date']  # Get the appointment date from the form
        status = 'Pending'

        # Insert the appointment into the database
        cursor.execute("""
            INSERT INTO appointments (patient_id, doctor_id, hospital_id, date, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (patient_id, doctor_id, hospital_id, appointment_date, status))
        connection.commit()

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('main.patient_dashboard'))

    # If it's a GET request, render the appointment booking form
    cursor.execute("SELECT id, name FROM hospitals")
    hospitals = cursor.fetchall()
    cursor.execute("SELECT id, username FROM users WHERE role = 'doctor'")
    doctors = cursor.fetchall()

    return render_template('book_appointment.html', hospitals=hospitals, doctors=doctors)

@main.route('/book_ambulance', methods=['GET', 'POST'])
@login_required
def book_ambulance():
    if request.method == 'POST':
        patient_id = current_user.id  # Assuming the patient is the logged-in user
        hospital_id = request.form['hospital_id']  # Get hospital_id from the form
        pickup_location = request.form['pickup_location']  # Get the pickup location from the form
        status = 'Pending'

        # Insert the ambulance booking into the database
        cursor.execute("""
            INSERT INTO ambulance_bookings (patient_id, hospital_id, pickup_location, status)
            VALUES (%s, %s, %s, %s)
        """, (patient_id, hospital_id, pickup_location, status))
        connection.commit()

        flash('Ambulance booked successfully!', 'success')
        return redirect(url_for('main.patient_dashboard'))

    # If it's a GET request, render the ambulance booking form
    cursor.execute("SELECT id, name FROM hospitals")
    hospitals = cursor.fetchall()

    return render_template('book_ambulance.html', hospitals=hospitals)

@main.route('/view_prescriptions')
@login_required
def view_prescriptions():
    # Fetch the prescriptions for the current user (assuming they're a patient)
    cursor.execute("""
        SELECT p.prescription_id, p.medicines, p.instructions, u.username AS doctor_name
        FROM prescriptions p
        JOIN users u ON p.doctor_id = u.id
        WHERE p.patient_id = %s
    """, (current_user.id,))
    prescriptions = cursor.fetchall()

    # Render a template to display prescriptions
    return render_template('view_prescriptions.html', prescriptions=prescriptions)

@main.route('/manage_orders')
@login_required
def manage_orders():
    if current_user.role != 'medical_store':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the medical orders from the database
    cursor.execute("SELECT * FROM medical_orders WHERE patient_id = %s", (current_user.id,))
    orders = cursor.fetchall()

    # Render the manage_orders.html template, passing the orders data
    return render_template('manage_orders.html', orders=orders)

@main.route('/manage_patients')
@login_required
def manage_patients():
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the list of patients from the database
    cursor.execute("SELECT id, name, age, disease, blood_group, email FROM patients")
    patients = cursor.fetchall()

    return render_template('manage_patients.html', patients=patients)

@main.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Logic for editing patient details
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        disease = request.form['disease']
        blood_group = request.form['blood_group']
        email = request.form['email']

        cursor.execute("""
            UPDATE patients SET name = %s, age = %s, disease = %s, blood_group = %s, email = %s WHERE id = %s
        """, (name, age, disease, blood_group, email, patient_id))
        connection.commit()

        flash('Patient details updated successfully!', 'success')
        return redirect(url_for('main.manage_patients'))

    cursor.execute("SELECT name, age, disease, blood_group, email FROM patients WHERE id = %s", (patient_id,))
    patient = cursor.fetchone()

    return render_template('edit_patient.html', patient=patient)

@main.route('/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    cursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
    connection.commit()

    flash('Patient deleted successfully!', 'success')
    return redirect(url_for('main.manage_patients'))

@main.route('/manage_tasks')
@login_required
def manage_tasks():
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch the list of tasks assigned to the nurse
    cursor.execute("SELECT id, task_description, assigned_by, status FROM tasks WHERE nurse_id = %s", (current_user.id,))
    tasks = cursor.fetchall()

    return render_template('manage_tasks.html', tasks=tasks)

@main.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        task_description = request.form['task_description']
        status = request.form['status']

        cursor.execute("""
            UPDATE tasks SET task_description = %s, status = %s WHERE id = %s
        """, (task_description, status, task_id))
        connection.commit()

        flash('Task updated successfully!', 'success')
        return redirect(url_for('main.manage_tasks'))

    cursor.execute("SELECT task_description, status FROM tasks WHERE id = %s", (task_id,))
    task = cursor.fetchone()

    return render_template('edit_task.html', task=task)


@main.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    connection.commit()

    flash('Task deleted successfully!', 'success')
    return redirect(url_for('main.manage_tasks'))

@main.route('/shift_scheduling')
@login_required
def shift_scheduling():
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch shifts assigned to the nurse
    cursor.execute("""
        SELECT shift_id, shift_date, start_time, end_time, nurse_name 
        FROM shifts WHERE nurse_id = %s
    """, (current_user.id,))
    shifts = cursor.fetchall()

    return render_template('shift_scheduling.html', shifts=shifts)

@main.route('/edit_shift/<int:shift_id>', methods=['GET', 'POST'])
@login_required
def edit_shift(shift_id):
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        shift_date = request.form['shift_date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        cursor.execute("""
            UPDATE shifts SET shift_date = %s, start_time = %s, end_time = %s 
            WHERE shift_id = %s
        """, (shift_date, start_time, end_time, shift_id))
        connection.commit()

        flash('Shift updated successfully!', 'success')
        return redirect(url_for('main.shift_scheduling'))

    cursor.execute("SELECT shift_date, start_time, end_time FROM shifts WHERE shift_id = %s", (shift_id,))
    shift = cursor.fetchone()

    return render_template('edit_shift.html', shift=shift)


@main.route('/delete_shift/<int:shift_id>', methods=['POST'])
@login_required
def delete_shift(shift_id):
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    cursor.execute("DELETE FROM shifts WHERE shift_id = %s", (shift_id,))
    connection.commit()

    flash('Shift deleted successfully!', 'success')
    return redirect(url_for('main.shift_scheduling'))

@main.route('/patient_monitoring')
@login_required
def patient_monitoring():
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch patient data for monitoring
    cursor.execute("""
        SELECT p.patient_id, p.name, p.age, p.health_status, p.monitoring_notes 
        FROM patients p
    """)
    patients = cursor.fetchall()

    return render_template('patient_monitoring.html', patients=patients)

@main.route('/edit_patient_monitoring/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient_monitoring(patient_id):
    if current_user.role != 'nurse':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        health_status = request.form['health_status']
        monitoring_notes = request.form['monitoring_notes']

        cursor.execute("""
            UPDATE patients SET health_status = %s, monitoring_notes = %s WHERE patient_id = %s
        """, (health_status, monitoring_notes, patient_id))
        connection.commit()

        flash('Patient monitoring updated successfully!', 'success')
        return redirect(url_for('main.patient_monitoring'))

    cursor.execute("SELECT name, health_status, monitoring_notes FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cursor.fetchone()

    return render_template('edit_patient_monitoring.html', patient=patient)


@main.route('/view_patient_details/<int:patient_id>')
@login_required
def view_patient_details(patient_id):
    cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    patient = cursor.fetchone()

    return render_template('view_patient_details.html', patient=patient)

@main.route('/manage_bookings')
@login_required
def manage_bookings():
    if current_user.role != 'ambulance':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))
    
    # Fetch ambulance bookings from the database
    cursor.execute("SELECT * FROM ambulance_bookings")
    bookings = cursor.fetchall()
    
    return render_template('manage_bookings.html', bookings=bookings)


@main.route('/live_tracking')
@login_required
def live_tracking():
    if current_user.role != 'ambulance':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch ambulance tracking data from the database (replace with your own logic)
    cursor.execute("""
        SELECT ambulance_id, location, status 
        FROM ambulance_tracking
    """)
    tracking_data = cursor.fetchall()

    return render_template('live_tracking.html', tracking_data=tracking_data)

@main.route('/emergency_response')
@login_required
def emergency_response():
    if current_user.role != 'ambulance':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch emergency response data from the database (replace with your own logic)
    cursor.execute("""
        SELECT response_id, location, status, time 
        FROM emergency_responses
    """)
    responses = cursor.fetchall()

    return render_template('emergency_response.html', responses=responses)

@main.route('/communication')
@login_required
def communication():
    if current_user.role != 'ambulance':  # Assuming communication is for ambulance role
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('main.home'))

    # Fetch communication data from the communications table
    cursor.execute("""
        SELECT communication_id, message, timestamp 
        FROM communications
        ORDER BY timestamp DESC
    """)
    communications = cursor.fetchall()

    return render_template('communication.html', communications=communications)

@main.route('/manage_inventory')
@login_required
def manage_inventory():
    # Fetch inventory items from the database
    cursor.execute("SELECT item_name, quantity, expiry_date FROM inventory")
    inventory = cursor.fetchall()
    
    # Render the manage_inventory.html template and pass the fetched inventory
    return render_template('manage_inventory.html', inventory=inventory)

@main.route('/verify_prescriptions')
@login_required
def verify_prescriptions():
    # Fetch prescriptions that need to be verified
    cursor.execute("""
    SELECT p.prescription_id, pat.name AS patient_name, p.medicines, p.instructions
    FROM prescriptions p
    JOIN patients pat ON p.patient_id = pat.patient_id
""")
    prescriptions = cursor.fetchall()

    # Render the verify_prescriptions.html template and pass the prescriptions data
    return render_template('verify_prescriptions.html', prescriptions=prescriptions)

@main.route('/manage_pickups')
@login_required
def manage_pickups():
    try:
        cursor.execute("Select * from pickups")
        pickups = cursor.fetchall()

        return render_template('manage_pickups.html', pickups=pickups)
    except Exception as e:
        flash(f"Error retrieving pickups: {e}", 'danger')
        return redirect(url_for('main.medical_store_dashboard'))

# @main.route('/test')
# def test():
#     return current_app.send_static_file('css/styles.css')