from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
#___________________________________
import logging
from logging import FileHandler
from main import app
import pytz
import time
import logging
# This is the 
# Set a secret key for the session
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=3)

timezone = pytz.timezone('Asia/Manila')
philippine_tz = pytz.timezone('Asia/Manila')


def get_db_connection():
    try:
        conn = sqlite3.connect('trabahanap.db')  # Replace 'your_database.db' with your actual database file
        conn.row_factory = sqlite3.Row  # Allows you to return rows as dictionaries (optional)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None  # Return None if connection fails



otp_storage = {}  # Store OTPs and timestamps in a dictionary
# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def send_otp(email):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND status = ?', (email, 'Approved')).fetchone()

    if not user:
        print(f"No approved user found for email: {email}")
        return False  # Return early if user not found

    otp = str(random.randint(1000, 9999))  # Generate a 4-digit OTP
    sender_email = "reignjosephc.delossantos@gmail.com"
    password = "vfwd oaaz ujog gikm"  # Use app password or OAuth2 for better security

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, password)
            # message = f"Subject: Your OTP Code\n\nYour OTP code is {otp}."
            message = f"Subject: BustosPESO - Password Reset Request\n\nDear Valued User,\n\nWe received a request to reset your password for your BustosPESO account. Please use the following OTP to proceed:\n\nYour OTP Code: {otp}\n\nFor security purposes, this code will expire in 3 minutes. If you did not request this change, please ignore this message or contact our support team immediately.\n\nThank you for using BustosPESO!\n\nBest regards,\nBustosPESO Support Team"


            server.sendmail(sender_email, email, message)
            otp_storage[email] = {'otp': otp, 'timestamp': time.time()}  # Store OTP with timestamp
            print(f"Sent OTP: {otp} to {email}")
            return True  # Return True to indicate OTP sent successfully
    except Exception as e:
        print(f"Error sending email: {e}")
        return False  # Return False on error

@app.route('/send_otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    email = data.get('forgot_password_email').strip()  # Trim any spaces

    conn = get_db_connection()
    
    if conn is None:
        return jsonify({"error": "Database connection failed."}), 500  # Handle the failed connection
    
    # Check if email exists in the users table with status "Approved"
    user = conn.execute('SELECT * FROM users WHERE email = ? AND status = ?', (email, "Approved")).fetchone()

    if user:
        # Get the current cooldown time from the database
        current_cooldown = user['cooldown']  # Assuming 'cooldown' is the column name
        current_time = datetime.now(timezone)  # Get current time in Philippine timezone

        if current_cooldown:
            cooldown_time = datetime.strptime(current_cooldown, "%Y-%m-%d %H:%M:%S")  # Convert from string to datetime
            cooldown_time = timezone.localize(cooldown_time)  # Make cooldown_time timezone-aware

            if current_time < cooldown_time:
                remaining_time = (cooldown_time - current_time).total_seconds()
                return jsonify({"error": f"Cooldown active. Please wait {remaining_time:.0f} seconds."}), 400  # Handle active cooldown

        # Send the OTP
        print(f"Received request to send OTP to email: {email}")
        send_otp(email)

        # Set new cooldown time (3 minutes from now)
        new_cooldown = current_time + timedelta(minutes=3)
        conn.execute('UPDATE users SET cooldown = ? WHERE email = ?', (new_cooldown.strftime("%Y-%m-%d %H:%M:%S"), email))
        conn.commit()  # Commit the changes

        return jsonify({"message": "OTP sent successfully!"}), 200
    else:
        print(f"No user found with email: {email}")
        return jsonify({"error": "Email not found or not approved."}), 404

@app.route('/forgot_password_update', methods=['POST'])
def forgot_password_update():
    data = request.get_json()  # Use get_json to parse the JSON body
    email = data.get('forgot_password_email')
    otp_entered = data.get('otp')
    new_password = data.get('forgot_password_new')

    print(f"Received request to update password for email: {email}")
    print(f"Entered OTP: {otp_entered}")
    print(f"New Password: {new_password}")

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND status = ?', (email, "Approved")).fetchone()

    if user:
        print(f"User found: {user}")

        # Validate the OTP
        if email in otp_storage:
            stored_data = otp_storage[email]
            current_time = time.time()

            if stored_data['otp'] != otp_entered:
                print("Entered OTP does not match the stored OTP.")
                return jsonify({"error": "Wrong OTP!"}), 400  # Return wrong OTP error
            elif current_time - stored_data['timestamp'] >= 180:
                print("OTP has expired.")
                return jsonify({"error": "OTP expired!"}), 400  # Return expired OTP error

            # If OTP is valid, proceed to update the password
            del otp_storage[email]  # Invalidate the OTP
            conn.execute('UPDATE users SET password = ?, otp = NULL WHERE email = ?', (new_password, email))  # Clear OTP after use
            conn.commit()
            print(f"Password updated for email: {email}")
            conn.close()
            return jsonify({"message": "Password updated successfully!"}), 200
        else:
            print("No OTP found for the provided email.")
            return jsonify({"error": "Invalid OTP!"}), 400  # No OTP found error
    else:
        print("No user found with the provided email.")
        return jsonify({"error": "Email not found or not approved."}), 404











def validate_otp(email, entered_otp):
    if email in otp_storage:
        stored_data = otp_storage[email]
        current_time = time.time()
        
        if stored_data['otp'] == entered_otp:
            if current_time - stored_data['timestamp'] < 180:  # Check for expiration
                del otp_storage[email]  # Invalidate the OTP
                print(f"OTP validation successful for {email}. OTP is valid.")
                return True  # OTP is valid
            else:
                print(f"OTP for {email} has expired. Current time: {current_time}, Timestamp: {stored_data['timestamp']}")
        else:
            print(f"Entered OTP for {email} does not match the stored OTP.")
    else:
        print(f"No OTP found for {email}.")

    print(f"OTP validation failed for {email}.")
    return False  # OTP is invalid or expired












@app.route('/forgot_password_check_email', methods=['POST'])
def forgot_password_check_email():
    data = request.get_json()
    email = data.get('email')

    print(f"Received email: {email}")  # Debugging print statement

    # Check if the email is empty
    if not email:
        print("Email field is empty")  # Debugging print statement
        return jsonify({'message': 'Please enter the email first'})

    conn = get_db_connection()
    cursor = conn.execute('SELECT email, status, cooldown FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"No registered email found for: {email}")  # Debugging print statement
        return jsonify({'message': 'No registered email was found'})
    
    email_status = row['status']
    current_cooldown = row['cooldown']
    current_time = datetime.now(timezone)  # Get current time in Philippine timezone

    if email_status == 'Pending':
        print(f"Email {email} is pending")  # Debugging print statement
        return jsonify({'message': 'Registered email is pending'})
    
    elif email_status == 'Approved':
        print(f"Email {email} is approved")  # Debugging print statement
        
        if current_cooldown:
            cooldown_time = datetime.strptime(current_cooldown, "%Y-%m-%d %H:%M:%S")  # Convert from string to datetime
            cooldown_time = timezone.localize(cooldown_time)  # Make cooldown_time timezone-aware

            if current_time < cooldown_time:
                remaining_time = (cooldown_time - current_time).total_seconds()
                return jsonify({
                    'cooldown': f'This email cannot request a password reset for {remaining_time:.0f} seconds.'
                }), 200  # Return cooldown message

        return jsonify({'message': 'Approved'})  # Proceed if no cooldown
    else:
        print(f"Unknown status for email: {email}")  # Debugging print statement
        return jsonify({'message': 'Unknown status'})













































@app.route('/announcement')
def announcement():
    return render_template('/menu/announcement.html')


# @app.route('/update_announcement_status', methods=['POST'])
# def update_announcement_status():
#     try:
#         # Get current date in the Philippines timezone
#         timezone = pytz.timezone('Asia/Manila')
#         current_date_ph = datetime.now(timezone)

#         # Connect to the database
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # Fetch all announcements
#         cursor.execute('SELECT announcementID, "When" FROM announcement')
#         announcements = cursor.fetchall()

#         for row in announcements:
#             announcement_id = row[0]
#             when_range = row[1]

#             # Ensure the when_range is valid
#             if ' to ' in when_range:
#                 # Parse the date range
#                 start_date_str, end_date_str = when_range.split(' to ')
#                 start_date = timezone.localize(datetime.strptime(start_date_str, '%Y-%m-%d'))
#                 end_date = timezone.localize(datetime.strptime(end_date_str, '%Y-%m-%d')) + timedelta(days=1)  # Extend to the end of the day
#             else:
#                 # Handle the case of a single date
#                 start_date = timezone.localize(datetime.strptime(when_range, '%Y-%m-%d'))
#                 end_date = start_date + timedelta(days=1)  # End of the same day

#             # Debugging: Print current date and the start/end dates
#             print(f"Current date: {current_date_ph}, Start date: {start_date}, End date: {end_date}")

#             # Determine the new status
#             new_status = "Available" if start_date <= current_date_ph < end_date else "Unavailable"

#             # Fetch current status and print it
#             cursor.execute('SELECT status FROM announcement WHERE announcementID = ?', (announcement_id,))
#             current_status = cursor.fetchone()[0]
#             print(f"Announcement ID: {announcement_id}, Current Status: {current_status}")

#             # Check if status has changed and print
#             if current_status != new_status:
#                 print(f"Announcement ID: {announcement_id}, Status changed from {current_status} to {new_status}")
#                 # Update the announcement status
#                 cursor.execute('UPDATE announcement SET status = ? WHERE announcementID = ?', (new_status, announcement_id))

#         conn.commit()
#         conn.close()

#         return jsonify(success=True)

#     except Exception as e:
#         print(f"Error updating announcement status: {e}")
#         return jsonify(success=False), 500



@app.route('/fetch_announcements', methods=['GET'])
def fetch_announcements():
    try:
        # Connect to the database
        # update_announcement_status() 
        print("Announcement status updated.")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch only available announcements
        cursor.execute('SELECT image, "What", "When", "Where", "Requirement", "Description", "status" FROM announcement WHERE status = ?', ('Available',))
        announcements = cursor.fetchall()
        conn.close()

        # Convert to a list of dicts
        announcement_list = []
        for row in announcements:
            announcement = {
                'image': row[0],
                'what': row[1],
                'when': row[2],
                'where': row[3],
                'requirement': row[4],
                'description': row[5],
            }
            announcement_list.append(announcement)

        # Return the announcements in the expected format
        return jsonify(announcements=announcement_list)

    except Exception as e:
        print(f"Error fetching announcements: {e}")
        return jsonify(success=False), 500













@app.route('/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({'logged_in': True})
    else:
        return jsonify({'logged_in': False})






@app.route('/send_otp_for_signin', methods=['POST'])
def send_otp_for_signin():
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('trabahanap.db')
    cursor = conn.cursor()

    try:
        # Check if the user exists with the given email
        cursor.execute('''SELECT * FROM users WHERE email = ?''', (email,))
        user = cursor.fetchone()
        print(f"Attempting to sign in user: {email}")  # Debugging print

        if user:
            print(f"User found: {user}")

            # Check if the password matches
            if user[2] != password:  # Assuming user[2] is the password column
                return jsonify({"success": False, "error_message": 'Cannot send OTP, wrong password or email.'}), 403
            
            if user[7] == 'Pending':
                return jsonify({"success": False, "error_message": 'Your account is pending approval.'}), 403
            
            # Generate a 4-digit OTP
            otp = str(random.randint(1000, 9999))
            
            # Send OTP via email
            sender_email = "reignjosephc.delossantos@gmail.com"
            app_password = "vfwd oaaz ujog gikm"  # Use app password or OAuth2 for better security

            # Update the email message
            # message = f"Subject: BustosPESO - Request OTP Login at BustosPESO \n\nYour OTP for signing in is: {otp}"
            message = f"Subject: BustosPESO - Request OTP Login at BustosPESO\n\nDear User,\n\nYour OTP for signing in is: {otp}\n\nIf you did not request this OTP code, please ignore this email.\n\nRegards,\nThe BustosPESO Team"

            
            try:
                # Connect to the email server and send the OTP
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender_email, app_password)
                    server.sendmail(sender_email, email, message)  # Use sendmail instead of send_message
                
                # Store OTP in session for verification
                session['otp'] = otp
                session['user_email'] = email  # Store the email in session if needed
                return jsonify({"success": True}), 200
            
            except Exception as e:
                print("Error sending OTP:", e)
                return jsonify({"success": False, "error_message": "Failed to send OTP. Please try again."}), 500
        
        else:
            # If user does not exist, return this message
            return jsonify({"success": False, "error_message": 'The email is not registered.'}), 404
            
    finally:
        cursor.close()
        conn.close()



@app.route('/confirm_signin_otp', methods=['POST'])
def confirm_signin_otp():
    entered_otp = request.form['otp']
    email = request.form['email']  # Get email if you want to use it later
    password = request.form['password']  # Get password if needed
    
    if 'otp' not in session:
        return jsonify({"success": False, "error_message": "No OTP generated."}), 400
    
    if entered_otp == session['otp']:
        # If OTP is valid, clear OTP from session
        session.pop('otp', None)  # Clear the OTP from the session
        return jsonify({"success": True}), 200  # Indicate success
    else:
        return jsonify({"success": False, "error_message": "Invalid OTP."}), 400

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''SELECT * FROM users WHERE email = ?''', (email,))
            user = cursor.fetchone()
            print(f"Attempting to sign in user: {email}")  # Debugging print

            if user:
                print(f"User found: {user}") 
                if user[2] != password:  # Check password
                    return render_template('/menu/signin.html', error_message='Invalid password.')

                if user[7] == 'Pending':
                    return render_template('/menu/signin.html', error_message='Your account is pending approval.')
                
                # Clear existing session data
                session.clear()
                
                # Set new session data
                session['user_id'] = user[0]
                session['user_email'] = user[1]
                session['user_password'] = user[2]
                session['user_fname'] = user[3]
                session['user_type'] = user[4]
                session['user_contact'] = user[5]
                session['user_profile'] = user[6]
                session['user_status'] = user[7]
                session['user_dateRegister'] = user[8]
                session['user_bio'] = user[9]
                session['user_address'] = user[10]
                session.permanent = True  # Make the session permanent
                session['session_start'] = datetime.now()  # Track session start time

                print("User signed in successfully.")
                
                # Set currentState to Active
                cursor.execute('''UPDATE users SET currentState = 'Active' WHERE User_ID = ?''', (user[0],))
                conn.commit()

                # Debugging prints
                print(user)

                if user[4] == 'Jobseeker':
                    return redirect(url_for('jobseeker'))
                elif user[4] == 'Employer':
                    return redirect(url_for('employer'))
                elif user[4] == 'Admin':
                    return redirect(url_for('admin'))
                else:
                    return render_template('/menu/signin.html', error_message='Invalid user type.')
            else:
                print("No registered email found.")
                return render_template('/menu/signin.html', error_message='Not registered email.')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('/menu/signin.html')























































@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    print(f"User ID before logout: {user_id}")  # Debugging print

    if user_id:
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()
        
        try:
            # Update currentState to Inactive
            cursor.execute('''UPDATE users SET currentState = 'Inactive' WHERE User_ID = ?''', (user_id,))
            conn.commit()
            print("User state updated to Inactive.")  # Successful state update
        finally:
            cursor.close()
            conn.close()

    # Clear session data
    session.clear()  
    print("User logged out and session cleared.")  # Logout confirmation
    
    return redirect(url_for('signin'))


 














@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get data from the form
        role = request.form.get('role')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Debugging: Print form data to check if it was retrieved correctly
        print(f"Received data - Role: {role}, Name: {name}, Email: {email}, Password: {password}")
        
        try:
            # Connect to the database
            conn = sqlite3.connect('trabahanap.db')
            cursor = conn.cursor()

            # Insert the user into the database
            cursor.execute('''
                INSERT INTO users (email, password, fname, userType, contactnum, dateRegister, AccountStatus)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (email, password, name, role, None, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Active'))
            
            # Commit the transaction
            conn.commit()

            # Debugging: Print a success message after the insert
            print(f"User '{name}' inserted successfully with role '{role}'.")

        except Exception as e:
            # Print the error message for debugging
            print(f"Error inserting user: {e}")
        
        finally:
            # Close the cursor and connection
            cursor.close()
            conn.close()

        return render_template('/menu/signup.html', show_modal=True)

    # Render the form for GET requests
    return render_template('/menu/signup.html', show_modal=False)





@app.route('/')
def index():
    return render_template('/menu/index.html')

@app.route('/about')
def about_and_contact():
    return render_template('/menu/about.html')






@app.route('/create_account', methods=['POST'])
def create_account():
    # For creating account
    role = request.form.get('role')
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    
    # Establish database connection
    conn = get_db_connection()
    cursor = conn.cursor()

        # Get current time in Philippine Time (PHT)
    # philippine_tz = timezone(timedelta(hours=8))
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    # user_id = None  # Initialize user_id to None
    
    if role == 'Jobseeker':
        # Insert data into the users table
        cursor.execute('''
            INSERT INTO users (email, password, fname, userType, status, dateRegister)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, password, name, role, 'Pending',current_time_pht))


        # Get the newly created User_ID
        user_id = cursor.lastrowid
        #I. Personal Information
        surname = request.form.get('surname')
        firstname = request.form.get('firstname')
        middlename = request.form.get('middlename')
        suffix = request.form.get('suffix')
        birthdate = request.form.get('birthdate')
        sex = request.form.get('sex')

        # Address Information
        address = request.form.get('address')
        barangay = request.form.get('barangay')
        municipality = request.form.get('municipality')
        province = request.form.get('province')

        # Additional Information
        religion = request.form.get('religion')
        civilstatus = request.form.get('civilstatus')
        tin = request.form.get('tin')
        height = request.form.get('height')

        disability = request.form.getlist('disability')
        disability_str = ', '.join(disability) 

        contact_no = request.form.get('contact_no')
        emailaddress = request.form.get('emailaddress')

        # Employment Status
        employment_status = request.form.getlist('employment_status')
        employment_status_str = ', '.join(employment_status)

        ofw =  request.form.getlist('ofw')
        ofw_str = ', '.join(ofw)
        
        former_ofw =  request.form.getlist('former-ofw')
        former_ofw_str = ', '.join(former_ofw)
        # 4Ps Beneficiary
        four_ps =  request.form.getlist('4ps')
        four_ps_str = ', '.join(four_ps)
        

        #II. Preferred Work Location
        work_location_type = request.form.get('preferred_work_location')
        if work_location_type == 'local':
            work_locations = request.form.getlist('local_city[]')
            work_locations_str = f"Local, " + ", ".join(work_locations)
        elif work_location_type == 'overseas':
            work_locations = request.form.getlist('overseas_country[]')
            work_locations_str = f"Overseas, " + ", ".join(work_locations)
        else:
            work_locations_str = None


        #III. Languages
        read_languages = request.form.getlist('read_language[]')
        write_languages = request.form.getlist('write_language[]')
        speak_languages = request.form.getlist('speak_language[]')
        understand_languages = request.form.getlist('understand_language[]')
        
        # Retrieve the 'Others' language input if it's been filled
        other_language = request.form.get('other_language', '').strip()
        
        if 'Other' in read_languages:
            read_languages.remove('Other')
            if other_language:
                read_languages.append(other_language)
        
        if 'Other' in write_languages:
            write_languages.remove('Other')
            if other_language:
                write_languages.append(other_language)
        
        if 'Other' in speak_languages:
            speak_languages.remove('Other')
            if other_language:
                speak_languages.append(other_language)
        
        if 'Other' in understand_languages:
            understand_languages.remove('Other')
            if other_language:
                understand_languages.append(other_language)

        # Convert lists to comma-separated strings
        read_languages_str = f"Read: [{', '.join(read_languages)}]"
        write_languages_str = f"Write: [{', '.join(write_languages)}]"
        speak_languages_str = f"Speak: [{', '.join(speak_languages)}]"
        understand_languages_str = f"Understand: [{', '.join(understand_languages)}]"

        language_proficiency_str = f"{read_languages_str}, {write_languages_str}, {speak_languages_str}, {understand_languages_str}"

        #IV. Educational Background
        currently_in_school = request.form.get('educational')
        course = request.form['course']

        elementary_school = request.form.get('elementary_school', None)
        elementary_graduated = request.form.get('elementary_graduated', None)
        elementary_reached = request.form.get('elementary_reached', None)
        elementary_last_attended = request.form.get('elementary_last_attended', None)
        elementary_values = [
            value for value in [
            elementary_school,
            elementary_graduated,
            elementary_reached,
            elementary_last_attended
            ] if value
        ]
        elementary_str = f"{', '.join(elementary_values)}"

        secondary_type = request.form.get('secondary')
        senior_strand = request.form.get('senior_strand')
        senior_graduated = request.form.get('senior_graduated')
        senior_reached = request.form.get('senior_reached')
        senior_last_attended = request.form.get('senior_last_attended')
        senior_high_values = [
            value for value in [
            secondary_type,
            senior_strand,
            senior_graduated,
            senior_reached,
            senior_last_attended
            ] if value
        ]
        senior_high_info = f"{', '.join(senior_high_values)}"



        tertiary_school = request.form.get('tertiary_school', None)
        tertiary_graduated = request.form.get('tertiary_graduated', None)
        tertiary_reached = request.form.get('tertiary_reached', None)
        tertiary_last_attended = request.form.get('tertiary_last_attended', None)
        tertiary_values = [
            value for value in [
            tertiary_school,
            tertiary_graduated,
            tertiary_reached,
            tertiary_last_attended
            ] if value
        ]
        tertiary_str = f"{', '.join(tertiary_values)}"



        graduate_studies_school = request.form.get('graduate_studies_school', None)
        graduate_studies_graduated = request.form.get('graduate_studies_graduated', None)
        graduate_studies_reached = request.form.get('graduate_studies_reached', None)
        graduate_studies_last_attended = request.form.get('graduate_studies_last_attended', None)
        graduate_studies_values = [
            value for value in [
            graduate_studies_school,
            graduate_studies_graduated,
            graduate_studies_reached,
            graduate_studies_last_attended
            ] if value
        ]
        graduate_studies_str = f"{', '.join(graduate_studies_values)}"

        #V. Technical
        vocational_course_1 = request.form.get('vocational_course_1', None)
        hours_of_training_1 = request.form.get('hours_of_training_1', None)
        training_institution_1 = request.form.get('training_institution_1', None)
        skills_aquired_1 = request.form.get('skills_aquired_1', None)
        certificate_received_1 = request.form.get('certificate_received_1', None)

        vocational_course_2 = request.form.get('vocational_course_2', None)
        hours_of_training_2 = request.form.get('hours_of_training_2', None)
        training_institution_2 = request.form.get('training_institution_2', None)
        skills_aquired_2 = request.form.get('skills_aquired_2', None)
        certificate_received_2 = request.form.get('certificate_received_2', None)

        vocational_course_3 = request.form.get('vocational_course_3', None)
        hours_of_training_3 = request.form.get('hours_of_training_3', None)
        training_institution_3 = request.form.get('training_institution_3', None)
        skills_aquired_3 = request.form.get('skills_aquired_3', None)
        certificate_received_3 = request.form.get('certificate_received_3', None)

        # Create a list of the non-empty vocational training entries
        vocational_training_entries = []

        # Append each training entry if it has at least one non-empty field
        for i in range(1, 4):
            # Directly retrieve values for each field
            v_course = request.form.get(f'vocational_course_{i}', None)
            v_hours = request.form.get(f'hours_of_training_{i}', None)
            v_institution = request.form.get(f'training_institution_{i}', None)
            v_skills = request.form.get(f'skills_aquired_{i}', None)
            v_certificate = request.form.get(f'certificate_received_{i}', None)

            entry = [v_course, v_hours, v_institution, v_skills, v_certificate]
            
            # Filter out empty values and join with commas
            entry_str = ', '.join([value for value in entry if value])
            
            if entry_str:
                vocational_training_entries.append(entry_str)

        # Join all non-empty entries with a separator (e.g., " | ") to store them in the 'vocational_training' field
        vocational_training_str = ' | '.join(vocational_training_entries)


        # VI. Professional License
        eligibility_1 = request.form.get('eligibility_1')
        eligibility_date_taken_1 = request.form.get('eligibility_date_taken_1')
        eligibility_prc_1 = request.form.get('eligibility_prc_1')
        eligibility_valid_until_1 = request.form.get('eligibility_valid_until_1')

        eligibility_2 = request.form.get('eligibility_2')
        eligibility_date_taken_2 = request.form.get('eligibility_date_taken_2')
        eligibility_prc_2 = request.form.get('eligibility_prc_2')
        eligibility_valid_until_2 = request.form.get('eligibility_valid_until_2')

        eligibility_professional_license = []

        # Create entries for eligibility 1 and eligibility 2 if they have any non-empty fields
        if eligibility_1 or eligibility_date_taken_1 or eligibility_prc_1 or eligibility_valid_until_1:
            entry_1 = f"[1] " + ', '.join([value for value in [eligibility_1, eligibility_date_taken_1, eligibility_prc_1, eligibility_valid_until_1] if value])
            eligibility_professional_license.append(entry_1)

        if eligibility_2 or eligibility_date_taken_2 or eligibility_prc_2 or eligibility_valid_until_2:
            entry_2 = f"[2] " + ', '.join([value for value in [eligibility_2, eligibility_date_taken_2, eligibility_prc_2, eligibility_valid_until_2] if value])
            eligibility_professional_license.append(entry_2)

        # Join all entries into a single string with ' | ' as the separator
        eligibility_professional_license_str = ' | '.join(eligibility_professional_license)





        #VIII. Work Experience
        work_experience = []

        for i in range(1, 4):  # Assuming you're collecting up to 3 work experiences
            company = request.form.get(f'work_experience_company_{i}')
            address = request.form.get(f'work_experience_address_{i}')
            position = request.form.get(f'work_experience_position_{i}')
            months = request.form.get(f'work_experience_months_{i}')
            status = request.form.get(f'work_experience_status_{i}')

            if company or address or position or months or status:
                entry = f"[{i}] " + ', '.join([value for value in [company, address, position, months, status] if value])
                work_experience.append(entry)

        work_experience_str = ' | '.join(work_experience)
            
        #VIII. Work Experience
        selected_skills = request.form.getlist('skills_acquired')
        other_skill = request.form.get('skills_acquired_other', '')

        # Format the skills
        formatted_skills = ', '.join([f'[{skill}]' for skill in selected_skills])
        if other_skill:
            formatted_skills += f', [ {other_skill} ]'

        # Prepend with "Skill: "
        formatted_skills = f'Skill: {formatted_skills}'




        cursor.execute('''
        INSERT INTO form101 (jobseeker_id, surname, firstname, middlename, suffix, birthdate, sex, address, barangay, municipality, province, religion, civilstatus, tin, contact_no, emailaddress,disability,employment_status,ofw,former_ofw,four_ps, preferred_work_location,language_proficiency,currently_school,course,elementary,senior_high,tertiary,graduate_studies,vocational_training,eligibility_license,work_experience,skills)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (user_id, surname, firstname, middlename, suffix, birthdate, sex, address, barangay, municipality, province, religion, civilstatus, tin, contact_no, emailaddress, disability_str, employment_status_str, ofw_str, former_ofw_str, four_ps_str, work_locations_str,language_proficiency_str,currently_in_school,course,elementary_str,senior_high_info,tertiary_str,graduate_studies_str,vocational_training_str,eligibility_professional_license_str,work_experience_str,formatted_skills))

        # Commit and close connection
        # Create the notification text
        notification_text = f"{name} created an account as an {role}"

        # Insert into the `admin_notification` table
        cursor.execute(''' 
            INSERT INTO admin_notification (user_id, userType, fname, picture, notification_text, notification_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, role, name, None, notification_text, current_time_pht))  # Set picture to None or use a default

        # Commit the notification insert
        conn.commit()
        print(f"Notification for user '{name}' inserted into admin_notification table.")


        print(f"Received data - Role: {role}, Name: {name}, Email: {email}, Password: {password}, User_ID: {user_id}")
        print(f"Received data - Strand: {senior_strand}")
        print(f"Received data - COURSE: {course}")
        print(f"Received data - Skills: {formatted_skills}")
        cursor.close()
        conn.close()

    # print(f"Received data - User_ID: {user_id}, Surname: {surname}, Firstname: {firstname}, Middlename: {middlename}, Suffix: {suffix}, Birthdate: {birthdate}, Sex: {sex}, Address: {address}, Barangay: {barangay}, Municipality: {municipality}, Province: {province}, Religion: {religion}, Civil Status: {civilstatus}, TIN: {tin}, Height: {height}, Disability: {', '.join(disability)}, Contact No: {contact_no}, Email Address: {emailaddress}, Employment Status: {employment_status}, OFW: {ofw}, Specify Country: {specify_country}, Former OFW: {former_ofw}, Latest Country: {latest_country}, Return Date: {return_date}, 4Ps: {four_ps}, Household ID: {household_id}")

    elif role == 'Employer':
        # Insert data into the users table
        cursor.execute(''' 
            INSERT INTO users (email, password, fname, userType, status, dateRegister)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, password, name, role, 'Pending', current_time_pht))
        
        # Commit the changes and get the last inserted user ID
        user_id = cursor.lastrowid
        conn.commit()

        # Create the notification text
        notification_text = f"{name} created an account as an {role}"

        # Insert into the `admin_notification` table
        cursor.execute(''' 
            INSERT INTO admin_notification (user_id, userType, fname, picture, notification_text, notification_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, role, name, None, notification_text, current_time_pht))  # Set picture to None or use a default

        # Commit the notification insert
        conn.commit()
        print(f"Notification for user '{name}' inserted into admin_notification table.")

        # Print the User_ID for debugging purposes
        print(f"User ID created: {user_id}")
        print(f"Received data - Role: {role}, Name: {name}, Email: {email}, Password: {password}, User_ID: {user_id}")

        # Close the cursor and connection
        cursor.close()
        conn.close()



    return redirect('/signin')

