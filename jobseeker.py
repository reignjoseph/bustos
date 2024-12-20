# import re
from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify,send_from_directory
import sqlite3
import os
import time
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import random
#___________________________________
import logging
from logging import FileHandler
from main import app
# import pdfkit   # Import the pdfkit library
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

timezone = pytz.timezone('Asia/Manila')
philippine_tz = pytz.timezone('Asia/Manila')


# Configure logging
if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(file_handler)

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'An error occurred: {error}')
    return "Internal Server Error", 500


app.secret_key = 'your_secret_key'  # Add a secret key for flashing messages
app.permanent_session_lifetime = timedelta(minutes=1800)

app.config['JOBSEEKER_UPLOAD_FOLDER'] = 'static/images/jobseeker-uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif','pdf'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# This is the jobseeker
def get_db_connection():
    conn = sqlite3.connect('trabahanap.db')
    conn.row_factory = sqlite3.Row
    return conn








@app.route('/view_nstp_form', methods=['GET'])
def view_nstp_form():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({'error': 'User not logged in.'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT pdf_form FROM users WHERE User_ID = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            pdf_filename = result[0]  # Assuming this contains the filename
            pdf_path = os.path.join('static', 'images', 'jobseeker-uploads', pdf_filename)

            # Check if the file exists before trying to send it
            if os.path.exists(pdf_path):
                # This should serve the PDF correctly
                return send_from_directory(os.path.dirname(pdf_path), os.path.basename(pdf_path), as_attachment=False)
            else:
                return jsonify({'error': 'PDF not found.'}), 404
        else:
            return jsonify({'error': 'PDF not found.'}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred while retrieving the PDF.'}), 500
    finally:
        cursor.close()
        conn.close()



@app.route('/view_resume_form', methods=['GET'])
def view_resume_form():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({'error': 'User not logged in.'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT resume_form FROM users WHERE User_ID = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            resume_filename = result[0]  # Assuming this contains the filename
            resume_path = os.path.join('static', 'images', 'jobseeker-uploads', resume_filename)

            # Check if the file exists before trying to send it
            if os.path.exists(resume_path):
                # This should serve the PDF correctly
                return send_from_directory(os.path.dirname(resume_path), os.path.basename(resume_path), as_attachment=False)
            else:
                return jsonify({'error': 'PDF not found.'}), 404
        else:
            return jsonify({'error': 'PDF not found.'}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'An error occurred while retrieving the PDF.'}), 500
    finally:
        cursor.close()
        conn.close()






























@app.route('/fetch_all_hidden_jobseeker_notification', methods=['GET'])
def fetch_hidden_notifications():
    try:
        # Check if user_id is in session
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401  # Unauthorized

        user_id = session['user_id']  # Get the jobseeker's ID from the session

        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to fetch all notifications for the specific jobseeker where popup is false
        cursor.execute('''
            SELECT *, u.profile AS employer_profile FROM jobseeker_notifications jn
            JOIN users u ON jn.employer_id = u.User_ID
            WHERE jn.jobseeker_id = ? AND jn.popup = "false"
        ''', (user_id,))

        notifications = cursor.fetchall()
        conn.close()

        # Prepare the notifications list with all columns
        notifications_list = [{
            'NotifID': notification['NotifID'],
            'jobseeker_id': notification['jobseeker_id'],
            'Job_ID': notification['Job_ID'],
            'employer_id': notification['employer_id'],
            'profile_picture': notification['employer_profile'] if notification['employer_profile'] else '/static/images/employer-images/avatar.png',
            'employer_fname': notification['employer_fname'],
            'text': notification['text'],
            'company': notification['company'],
            'job_title': notification['job_title'],
            'popup': notification['popup'],
            'date_created': notification['date_created']
        } for notification in notifications]

        # Print the number of fetched notifications and their details to the console for debugging
        print(f"Fetched Archived Notifications: {len(notifications_list)} items")
        for notif in notifications_list:
            print(f"NotifID: {notif['NotifID']}, Employer Name: {notif['employer_fname']}, Profile Picture: {notif['profile_picture']}")

        # Return the notifications or an empty list if none found
        return jsonify({'notifications': notifications_list})

    except Exception as e:
        print(f"Error fetching hidden notifications: {e}")
        return jsonify({'error': 'An error occurred while retrieving notifications'}), 500
@app.route('/unarchive_jobseeker_notifications', methods=['POST'])
def unarchive_notification():
    # Get the notification ID from the request
    notif_id = request.json.get('NotifID')
    
    # Ensure a valid notification ID is provided
    if not notif_id:
        return jsonify({'error': 'Notification ID is required'}), 400
    
    # Get the user_id from session
    user_id = session.get('user_id')  # Use user_id instead of jobseeker_id
    
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401  # 401 Unauthorized

    # Connect to the database
    conn = get_db_connection()

    # Update the popup field to an empty string for the specified notification ID
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE jobseeker_notifications SET popup = "" WHERE NotifID = ? AND jobseeker_id = ?',
        (notif_id, user_id)  # Use user_id for the query
    )
    
    # Check if any row was updated
    if cursor.rowcount == 0:
        return jsonify({'error': 'No notification found or already unarchived'}), 404
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    return jsonify({'success': 'Notification unarchived successfully'})





@app.route('/fetch_all_hidden_status', methods=['GET'])
def fetch_all_hidden_status():
    try:
        # Check if user_id is in session
        if 'user_id' not in session:
            print("User is not logged in.")
            return jsonify({'error': 'Not logged in'}), 401  # Unauthorized

        user_id = session['user_id']  # Get the jobseeker's ID from the session
        print(f"User ID: {user_id}")  # Print the user ID for debugging

        conn = get_db_connection()
        cursor = conn.cursor()

        print("Database connection established.")

        # Query to fetch detailed information for hidden statuses
        cursor.execute('''
            SELECT a.status_id, a.applicant_id, a.job_id, a.jobseeker_id, a.employer_id, a.status_description, 
                   a.status_type, a.date_posted, u.profile AS profile_picture, u.fname AS employer_name
            FROM application_status a
            JOIN users u ON a.employer_id = u.User_ID
            WHERE jobseeker_id = ? AND jobseeker_popup = "false"
        ''', (user_id,))  # Filter by jobseeker_id

        statuses = cursor.fetchall()
        conn.close()

        # Prepare the statuses list
        statuses_list = []
        for row in statuses:
            profile_picture = row[8]  # Profile picture URL
            if profile_picture:
                profile_url = url_for('static', filename=f'images/employer-images/{profile_picture}')
            else:
                profile_url = url_for('static', filename='images/employer-images/woman.png')

            statuses_list.append({
                'status_id': row[0],
                'applicant_id': row[1],
                'job_id': row[2],
                'jobseeker_id': row[3],
                'employer_id': row[4],
                'status_description': row[5],
                'status_type': row[6],
                'date_posted': row[7],
                'profile_picture': profile_url,
                'employer_name': row[9]
            })

        # Print the fetched statuses for debugging
        print(f"Fetched Archived Statuses: {len(statuses_list)} items")
        for status in statuses_list:
            print(f"Status ID: {status['status_id']}, Employer Name: {status['employer_name']}, Description: {status['status_description']}")

        # Return the statuses or an empty list if none found
        return jsonify({'statuses': statuses_list})

    except Exception as e:
        print(f"Error fetching hidden statuses: {e}")
        return jsonify({'error': 'An error occurred while retrieving statuses'}), 500


@app.route('/unarchive_status', methods=['POST'])
def unarchive_status():
    # Get the status ID from the request
    status_id = request.json.get('status_id')

    # Ensure a valid status ID is provided
    if not status_id:
        return jsonify({'error': 'Status ID is required'}), 400

    # Connect to the database
    conn = get_db_connection()

    # Update the jobseeker_popup field to an empty string for the specified status ID
    conn.execute(
        'UPDATE application_status SET jobseeker_popup = "" WHERE status_id = ?',
        (status_id,)  # Only status_id is used for the query
    )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    return jsonify({'success': 'Status unarchived successfully'})



















@app.route('/insert_html2pdf_jobseeker', methods=['POST'])
def insert_html2pdf_jobseeker():
    if 'pdf' not in request.files:
        print("No file part")
        return redirect('/signin')

    file = request.files['pdf']

    if file.filename == '':
        print("No selected file")
        return redirect('/signin')

    if file:
        # Secure the filename
        filename = secure_filename('form-content-jobseeker.pdf')
        file_path = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], filename)

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Assuming you have the user's email in the request data
        user_email = request.form.get('email')  # Get the email from the form data

        if not user_email:
            print("Email not provided in the request.")
            return redirect('/signin')

        # Check if a filename already exists for the user in the `users` table
        cursor.execute('''
            SELECT pdf_form FROM users WHERE email = ?
        ''', (user_email,))
        existing_filename = cursor.fetchone()

        # If a filename exists in the table but the file is missing from the folder, generate a new one
        if existing_filename and existing_filename[0]:
            existing_file_path = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], existing_filename[0])
            if not os.path.exists(existing_file_path):
                print(f"File {existing_filename[0]} is missing, generating a new filename.")

        # If the file exists or no existing filename, proceed with checking the folder and renaming logic
        base, extension = os.path.splitext(filename)
        counter = 1
        new_filename = filename  # Initialize new_filename

        while os.path.exists(file_path):
            new_filename = f"{base}({counter}){extension}"
            file_path = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], new_filename)
            counter += 1

        # Save the file using the unique filename
        file.save(file_path)
        print(f"PDF saved to {file_path}")

        # Update the `pdf_form` field in the `users` table with the new filename
        cursor.execute('''
            UPDATE users
            SET pdf_form = ?
            WHERE email = ?
        ''', (new_filename, user_email))

        conn.commit()
        conn.close()

        print(f"PDF filename '{new_filename}' updated in the users table for email {user_email}.")

    return redirect('/signin')



@app.route('/insert_resume', methods=['POST'])
def insert_resume():
    if 'resume' not in request.files:
        print("No resume file part")
        return {"error": "No resume file"}, 400

    resume_file = request.files['resume']

    if resume_file.filename == '':
        print("No selected resume file")
        return {"error": "No selected resume file"}, 400

    if resume_file:
        # Secure the filename
        resume_filename = secure_filename(resume_file.filename)
        resume_file_path = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], resume_filename)

        # Save the resume file
        resume_file.save(resume_file_path)
        print(f"Resume saved to {resume_file_path}")

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the last User_ID from the users table
        cursor.execute('SELECT User_ID FROM users ORDER BY User_ID DESC LIMIT 1')
        last_row = cursor.fetchone()

        if last_row:
            user_id = last_row[0]
            # Insert the resume filename into the resume_form field for the last user
            cursor.execute('UPDATE users SET resume_form = ? WHERE User_ID = ?', (resume_filename, user_id))
            conn.commit()
            print(f"Resume filename '{resume_filename}' updated in the users table for User_ID {user_id}.")
        else:
            print("No users found in the table.")

        conn.close()

        return {"success": "Resume uploaded successfully."}

    return {"error": "Error processing resume."}, 500












































@app.route('/retrieve_application_status', methods=['GET'])
def retrieve_application_status():
    try:
        # Check if user_id and user_type are in session
        if 'user_id' not in session or session['user_type'] != 'Jobseeker':
            return jsonify({'error': 'Unauthorized access'}), 403
        
        user_id = session['user_id']  # Get the jobseeker's user_id from the session

        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()

        print("Database connection established.")

        # Query to get application status and related information
        cursor.execute('''  
            SELECT a.status_id, a.applicant_id, a.job_id, a.jobseeker_id, a.employer_id, a.status_description, 
                   a.status_type, a.company, u.profile, u.fname, a.date_posted
            FROM application_status a
            JOIN users u ON a.employer_id = u.User_ID
            WHERE (a.jobseeker_popup IS NULL OR a.jobseeker_popup = '') AND a.jobseeker_id = ?
        ''', (user_id,))  # Filter by jobseeker_id

        status_list = cursor.fetchall()
        conn.close()

        # Check if no records were found
        if not status_list:
            print("No data was found.")  # Print message when no records are found
            return jsonify([])  # Return an empty list

        # Prepare the status data
        results = []
        for row in status_list:
            profile_picture = row[8]
            # Dynamically generate the profile picture URL
            if profile_picture:
                profile_url = url_for('static', filename=f'images/employer-images/{profile_picture}')
            else:
                profile_url = url_for('static', filename='images/employer-images/woman.png')

            results.append({
                'status_id': row[0],
                'applicant_id': row[1],
                'job_id': row[2],
                'jobseeker_id': row[3],
                'employer_id': row[4],
                'status_description': row[5],
                'status_type': row[6],
                'company': row[7],
                'profile_picture': profile_url,
                'employer_name': row[9],
                'date_posted': row[10]
            })

        return jsonify(results)

    except Exception as e:
        print(f"Error fetching application statuses: {e}")
        return jsonify({'error': 'An error occurred while retrieving application statuses'}), 500























@app.route('/update_popup_status', methods=['POST'])
def update_popup_status():
    try:
        # Extract and print the parameters
        applicant_id = request.form.get('id')
        popup_value = request.form.get('popup')

        print(f"Received parameters: applicant_id={applicant_id}, popup_value={popup_value}")

        # Check if parameters are missing
        if not applicant_id or not popup_value:
            raise ValueError("Missing required parameters")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Print connection and cursor status
        print("Database connection established.")

        # Update the popup field in the application_status table
        cursor.execute('''
            UPDATE application_status
            SET jobseeker_popup = ?
            WHERE applicant_id = ?
        ''', (popup_value, applicant_id))

        # Commit and close
        conn.commit()
        conn.close()
        
        print(f"Successfully updated popup status for applicant_id={applicant_id} to {popup_value}")
        retrieve_application_status()
        return jsonify({'status': 'success'})
    
    except Exception as e:
        print(f"Error updating pop-up status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500






import re




from nltk.stem import PorterStemmer

# Initialize the PorterStemmer
stemmer = PorterStemmer()

def clean_and_stem_skills(skills_string):
    # Split the skills string on commas to separate individual skills
    skills_list = skills_string.split(',')
    
    # Initialize a list to hold cleaned and stemmed skills
    cleaned_skills = []
    
    for skill in skills_list:
        # Remove special characters and whitespace, then convert to lowercase
        cleaned_skill = ''.join(e for e in skill.strip().lower() if e.isalnum())
        cleaned_skills.append(cleaned_skill)

    return cleaned_skills

@app.route('/advance_filter', methods=['GET'])
def advance_filter():
    skill_filter = request.args.get('skill_filter', 'Default')
    location_filter = request.args.get('location_filter', 'Default')
    company_filter = request.args.get('company_filter', 'Default')
    job_filter = request.args.get('job_filter', 'Default')
    position_filter = request.args.get('position_filter', 'Default')
    nature_of_work_filter = request.args.get('nature_of_work_filter', 'Default')

    if 'user_id' not in session:
        return jsonify({"error": "User is not logged in"}), 401

    conn = get_db_connection()

    jobseeker_id = session['user_id']
    all_form101_query = "SELECT * FROM form101 WHERE jobseeker_id = ?"
    all_form101_records = conn.execute(all_form101_query, (jobseeker_id,)).fetchall()

    form101_records = [dict(row) for row in all_form101_records]
    print(f"All records from form101 for Jobseeker_ID {jobseeker_id}: {form101_records}")

    all_jobs_query = "SELECT * FROM jobs"
    all_jobs_records = conn.execute(all_jobs_query).fetchall()

    jobs_records = [dict(row) for row in all_jobs_records]
    print(f"All records from jobs table: {jobs_records}")

    initial_query = "SELECT * FROM jobs WHERE LOWER(request) = 'approved' AND LOWER(jobStatus) = 'available'"
    initial_jobs = conn.execute(initial_query).fetchall()

    filtered_jobs = []

    skills_query = "SELECT skills FROM form101 WHERE jobseeker_id = ?"
    skills_result = conn.execute(skills_query, (jobseeker_id,)).fetchone()

    cleaned_jobseeker_skills = []
    if skills_result:
        cleaned_jobseeker_skills = clean_and_stem_skills(skills_result['skills'])
        print(f"This is the Jobseeker_ID: {jobseeker_id} and this is skills: {cleaned_jobseeker_skills}")

    # If all filters are 'Default', check for partial matches
    if all(f == 'Default' for f in [skill_filter, location_filter, company_filter, job_filter, position_filter, nature_of_work_filter]):
        for job in initial_jobs:
            cleaned_job_skills = clean_and_stem_skills(job['skills'])
            print(f"This is the Job ID: {job['Job_ID']} and the fetched skills on this job: {cleaned_job_skills}")

            matched_words = set()
            for job_skill in cleaned_job_skills:
                for js_skill in cleaned_jobseeker_skills:
                    # Check if job skill is a substring of jobseeker skill or vice versa
                    if job_skill in js_skill or js_skill in job_skill:
                        matched_words.add(job_skill)  # Add the job's skill instead

            if matched_words:
                print(f"Matched words found: {matched_words}")
                filtered_jobs.append(job)


    else:
        for job in initial_jobs:
            cleaned_job_skills = clean_and_stem_skills(job['skills'])

            if (skill_filter == 'Default' or skill_filter.lower() in cleaned_job_skills) and \
               (location_filter == 'Default' or location_filter.lower() in job['location'].lower()) and \
               (company_filter == 'Default' or company_filter.lower() in job['Company'].lower()) and \
               (job_filter == 'Default' or job_filter.lower() in job['title'].lower()) and \
               (position_filter == 'Default' or position_filter.lower() in job['position'].lower()) and \
               (nature_of_work_filter == 'Default' or nature_of_work_filter.lower() in job['natureOfWork'].lower()):
                filtered_jobs.append(job)

    # Remove duplicates by converting list to a dictionary (keyed by Job_ID)
    final_jobs = list({job['Job_ID']: job for job in filtered_jobs}.values())

    conn.close()

    job_list = [{
        "Job_ID": job['Job_ID'],
        "Company": job['Company'],
        "title": job['title'],
        "image": job['image'],
        "location": job['location'],
        "natureOfWork": job['natureOfWork'],
        "jobStatus": job['jobStatus'],
        "closingDate": job['closingDate'],
    } for job in final_jobs]

    print(f"Return fetched jobs: {job_list}")

    return jsonify(job_list)





















@app.route('/job_details', methods=['GET'])
def job_details():
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({"error": "Job ID not provided"}), 400

    conn = get_db_connection()
    job = conn.execute("SELECT * FROM jobs WHERE Job_ID = ?", (job_id,)).fetchone()
    conn.close()

    if job:
        # Convert Row to dictionary
        job_dict = {key: job[key] for key in job.keys()}
        print("Job Data:", job_dict)  # Debugging line
        return jsonify(job_dict)
    else:

        return jsonify({"error": "Job not found"}), 404
    





























@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.form.get('email')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the email is already registered
    cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
    email_exists = cursor.fetchone()[0] > 0

    conn.close()

    # Return a JSON response to the client
    return jsonify({'email_exists': email_exists})













def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



@app.route('/applicant', methods=['POST'])
def applicant():
    # Get user ID from session and validate if the user is logged in
    session_id = session.get('user_id')
    if not session_id:
        print("User not logged in.")
        return {"error": "User is not logged in."}, 401

    print("User is logged in. Session ID:", session_id)

    conn = get_db_connection()
    cursor = conn.cursor()

    print("Received POST request for applicant.")

    # Get data from the form
    job_id = request.form.get('job_id')
    employer_id = request.form.get('employer_id')
    file = request.files.get('file')  # Use .get to prevent KeyError if 'file' not in request

    print("Job ID:", job_id)
    print("Employer ID:", employer_id)

    # Ensure a file was uploaded
    if not file:
        print("No file uploaded.")
        return {"error": "No file uploaded."}, 400

    # Save the uploaded file
    filename = secure_filename(file.filename)
    base, ext = os.path.splitext(filename)
    timestamp = int(time.time())
    filename = f"{base}_{timestamp}{ext}"
    file_path = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], filename)
    file.save(file_path)
    print("File saved to:", file_path)

    # Get employer's email and company name before inserting
    cursor.execute('''
        SELECT jobs.company, users.email 
        FROM jobs 
        JOIN users ON jobs.employer_id = users.User_ID 
        WHERE jobs.Job_ID = ?
    ''', (job_id,))
    employer_info = cursor.fetchone()

    if not employer_info:
        print("Employer information not found.")
        conn.close()
        return {"error": "Employer information not found."}, 404

    company_name, employer_email = employer_info
    print("Employer information retrieved:")
    print(f"Company Name: {company_name}")
    print(f"Employer Email: {employer_email}")

    # Insert the application into the applicant table with 'Pending' status
    initial_status = 'Pending'
    cursor.execute('''
        INSERT INTO applicant (job_id, employer_id, jobseeker_id, jobseeker_name, email, contact_no, form, status, date_request)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_id, employer_id, session_id, 
        session.get('user_fname'), session.get('user_email'), 
        session.get('user_contact'), file_path, initial_status, 
        datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')
    ))
    print(f"Application inserted for jobseeker ID {session_id} with file path: {file_path}.")

    # Retrieve the last inserted applicant ID and its status from applicant table
    applicant_id = cursor.lastrowid
    cursor.execute('SELECT status FROM applicant WHERE applicant_id = ?', (applicant_id,))
    applicant_status = cursor.fetchone()[0]

    # Prepare and insert data into the application_status table using applicant's status
    status_description = f"Your application at {company_name} is now being processed. Status: {applicant_status}"
    date_posted = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        INSERT INTO application_status (
            applicant_id, job_id, jobseeker_id, employer_id, 
            status_description, status_type, company, date_posted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        applicant_id, job_id, session_id, employer_id, 
        status_description, applicant_status, company_name, date_posted
    ))
    print(f"Status record created for applicant ID {applicant_id} with status '{applicant_status}'.")

    # Send email to the employer
    send_employer_email_from_applicant(employer_email, session.get('user_fname'), company_name)
    print("Email sent to employer.")

    # Commit and close connection
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": "Application submitted successfully."}






def send_employer_email_from_applicant(email, fname, company):
    # Email account setup
    sender_email = "reignjosephc.delossantos@gmail.com"
    password = "vfwd oaaz ujog gikm"  # Use a secure app-specific password

    # Email content
    subject = "BustosPESO - Jobseeker Applicant"
    body = f"""
    Dear Employer,

    We wanted to inform you that an applicant, {fname}, has applied for a position at {company}.
    
    Best regards,
    BustosPESO Team
    """
    
    # Setting up the message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Sending the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, email, message.as_string())
        print(f"Email sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {e}")







@app.route('/jobseeker/status')
def jobseeker_status():
    if 'user_id' in session and session['user_type'] == 'Jobseeker':
        user_id = session['user_id']
        print(f"User ID from session: {user_id}")  # Print user ID to check if it's retrieved correctly
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user data
        cursor.execute('SELECT * FROM users WHERE User_ID = ?', (user_id,))
        user_data = cursor.fetchone()
        
        # Convert Row object to a dictionary for easier debugging
        if user_data:
            user_data_dict = {key: user_data[key] for key in user_data.keys()}
            print(f"Fetched user data: {user_data_dict}")  # Print fetched user data for debugging
        else:
            print("No user data found.")  # Notify if no user data is returned

        # Ensure profile image is set to default if missing
        if user_data and (user_data[6] is None or user_data[6] == ''):
            user_data = list(user_data)  # Convert tuple to list to modify
            user_data[6] = 'images/profile.png'  # Default profile image path
            print("Profile image was missing; set to default.")  # Notify that the default image was set
        
        # Close the cursor and connection
        cursor.close()
        conn.close()

        # Pass the user data to the template
        print(f"Rendering status page with user data: {user_data_dict}")  # Print user data before rendering
        return render_template('jobseeker/status.html', user_data=user_data_dict)
    
    print("User not logged in or not a jobseeker. Redirecting to signin.")  # Notify if the user is not logged in
    return redirect(url_for('signin'))






















@app.route('/jobseeker_fetch_all_notification')
def jobseeker_fetch_all_notification():
    if 'user_id' in session and session['user_type'] == 'Jobseeker':
        user_id = session['user_id']  # Get the jobseeker's ID from the session

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch notifications for the specific jobseeker where popup is NULL or empty,
        # and join with jobs table where jobStatus is 'Available' and request is 'Approved'
        cursor.execute('''
            SELECT jn.*, j.jobStatus, j.request, j.title, j.image, j.location, j.natureOfWork, j.Company, j.closingDate
            FROM jobseeker_notifications jn
            JOIN jobs j ON jn.Job_ID = j.Job_ID
            WHERE jn.jobseeker_id = ? 
            AND (jn.popup IS NULL OR jn.popup = "")
            AND j.jobStatus = "Available" 
            AND j.request = "Approved"
            ORDER BY jn.date_created DESC
        ''', (user_id,))  # Filter by jobseeker_id

        notifications = cursor.fetchall()

        # Generate notification texts
        notifications_with_text = []
        for notification in notifications:
            employer_id = notification['employer_id']
            cursor.execute('SELECT profile FROM users WHERE User_ID = ?', (employer_id,))
            employer_data = cursor.fetchone()
            
            profile_picture = employer_data['profile'] if employer_data and employer_data['profile'] else '/static/images/employer-images/avatar.png'
            
            notifications_with_text.append({
                'employer_fname': notification['employer_fname'],
                'text': notification['text'],
                'date_created': notification['date_created'],
                'profile_picture': profile_picture,
                'NotifID': notification['NotifID'],
                'Job_ID': notification['Job_ID'],
                'jobStatus': notification['jobStatus'],    # Added from jobs table
                'request': notification['request'],        # Added from jobs table
                'title': notification['title'],            # Job title
                'image': notification['image'],            # Job image
                'location': notification['location'],      # Job location
                'natureOfWork': notification['natureOfWork'],  # Job nature
                'Company': notification['Company'],        # Job Company
                'closingDate': notification['closingDate'] # Closing date
            })

        # Close the cursor and connection
        cursor.close()
        conn.close()

        # Return the notifications as JSON
        return jsonify({
            'count': len(notifications_with_text),
            'notifications': notifications_with_text
        })

    return jsonify({'error': 'User not authenticated'}), 401






@app.route('/jobseeker/notification/close/<int:notif_id>', methods=['POST'])
def close_jobseeker_notification(notif_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update the popup status in the database
    cursor.execute('UPDATE jobseeker_notifications SET popup = ? WHERE NotifID = ?', ('false', notif_id))
    conn.commit()

    # Check if the update was successful
    if cursor.rowcount == 0:
        return jsonify({'error': 'Notification not found'}), 404

    cursor.close()
    conn.close()
    return jsonify({'success': True}), 200











def update_job_statuses():
    conn = get_db_connection()

    # Get current time in Philippine Time (PHT)
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Print current time in PHT for debugging purposes
    print(f"Current Time (PHT): {current_time_pht}")

    try:
        # Perform the update and count how many rows were affected
        cursor = conn.execute("""
            UPDATE jobs 
            SET jobStatus = 'Unavailable'
            WHERE closingDate <= ?
        """, (current_time_pht,))

        conn.commit()

        # Print the number of rows affected
        rows_updated = cursor.rowcount
        print(f"Rows Updated: {rows_updated}")

        # Optional: Verify which jobs were updated
        cursor.execute("""
            SELECT job_id, title, closingDate 
            FROM jobs 
            WHERE closingDate <= ?
        """, (current_time_pht,))
        updated_jobs = cursor.fetchall()

        print("Jobs marked as 'Unavailable':")
        for job in updated_jobs:
            job_id, title, closing_date = job
            print(f"Job ID: {job_id}, Title: {title}, Closing Date: {closing_date}")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()




@app.route('/jobseeker')
def jobseeker():
    print("Entering jobseeker route")  # Debugging line
    # Check if user is authenticated and is a Jobseeker
    if 'user_id' not in session or session.get('user_type') != 'Jobseeker':
        return redirect(url_for('signin'))

    # Set session start time if it doesn't exist
    if 'session_start' not in session:
        session['session_start'] = datetime.now(timezone)

    # Check for session timeout (30 minutes)
    session_start = session['session_start']
    session_expiry = session_start + timedelta(minutes=1800)

    # Debugging session times
    print(f"Session start: {session_start}, Current time: {datetime.now(timezone)}")

    # If the session has expired, clear session data and redirect
    if datetime.now(timezone) > session_expiry:
        print(f"The session expired at {session_expiry.strftime('%Y-%m-%d %H:%M:%S')} {timezone.zone}")

        # Update currentState to Inactive
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET currentState = ? WHERE User_ID = ?', ('Inactive', session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()

        session.clear()  # Clear session data
        return redirect(url_for('signin'))

    # If session is valid, proceed to fetch job announcements and user data
    update_job_statuses()
    user_id = session['user_id']

    # Connect to the database and fetch job announcements
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM jobs')
    jobs = cursor.fetchall()

    cursor.execute('SELECT * FROM users WHERE User_ID = ?', (user_id,))
    user_data = cursor.fetchone()

    # Ensure the user has a profile image
    if user_data and (user_data[6] is None or user_data[6] == ''):
        user_data = list(user_data)  # Convert to list to modify
        user_data[6] = 'images/profile.png'

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Pass the jobs and user data to the template
    return render_template('/jobseeker/jobseeker.html', jobs=jobs, user_data=user_data)



@app.route('/update_inactive_status', methods=['POST'])
def update_inactive_status():
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET currentState = ? WHERE User_ID = ?', ('Inactive', session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()

        session.clear()  # Clear session data after marking as inactive
        return jsonify({'status': 'success'}), 200
    return jsonify({'error': 'Not authenticated'}), 403








@app.route('/jobseeker_update_profile', methods=['POST'])
def update_profile():
    # Check if the user is logged in
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')
    if 'user_id' not in session:
        flash('You need to log in first')
        return redirect(url_for('signin'))

    user_id = session['user_id']

    # Retrieve form data
    try:
        bio = request.form['bio']
    except KeyError as e:
        flash(f'Missing form field: {e}')
        return redirect(request.url)

    # Get current user data from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT profile, email FROM users WHERE User_ID = ?", (user_id,))
    user_data = cursor.fetchone()
    current_image_path = user_data[0]  # Get current profile image path
    email_address = user_data[1]        # Get email address

    # Handle the profile picture upload
    if 'profile_picture' not in request.files or request.files['profile_picture'].filename == '':
        # No file uploaded, keep the current image
        image_path = current_image_path
    else:
        file = request.files['profile_picture']
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], filename)  # Ensure you have this config set
            file.save(filepath)
            image_path = f'images/jobseeker-uploads/{filename}'  # Update this for the database path
        else:
            flash('Invalid file format')
            image_path = current_image_path  # Keep the current image path if the file is invalid

    # Update the database with the user's bio and profile image
    cursor.execute("""
        UPDATE users
        SET bio = ?, profile = ?
        WHERE User_ID = ?
    """, (bio, image_path, user_id))

    # Print the updated values for debugging
    print(f"Updated Profile: User_ID = {user_id}, Bio = {bio}, Profile Image Path = {image_path}, Email = {email_address}")

    # Now, get the address and phone number from the form101 table
    cursor.execute("""
        SELECT address, barangay, municipality, province, contact_no
        FROM form101
        WHERE jobseeker_id = ?
    """, (user_id,))
    form_data = cursor.fetchone()

    if form_data:
        # Concatenate address fields
        address = f"{form_data[0]}, {form_data[1]}, {form_data[2]}, {form_data[3]}"  # Concatenate address fields
        contact_no = form_data[4]  # Get contact number

        # Print email, address, and contact number for debugging
        print(f"Email Address: {email_address}, Address: {address}, Contact No: {contact_no}")

        # You can now use email_address, address, and contact_no as needed, for example, you might want to update them in the users table if necessary
        # Uncomment the next lines if you need to update the contact number and address in the users table
        # cursor.execute("""
        #     UPDATE users
        #     SET address = ?, contact_no = ?
        #     WHERE User_ID = ?
        # """, (address, contact_no, user_id))

    # Get jobseeker details from `users` table
    cursor.execute('SELECT profile, fname, userType FROM users WHERE User_ID = ?', (user_id,))
    user = cursor.fetchone()

    if user:
        picture = user[0]  # profile (picture)
        fname = user[1]    # fname
        userType = user[2] # userType

        notification_text = f"{fname} updated their profile."

        # Insert notification into `admin_notification` table
        cursor.execute('''
            INSERT INTO admin_notification (user_id, userType, picture, fname, notification_text, notification_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, userType, picture, fname, notification_text, current_time_pht))

        print(f"Admin Notification: {notification_text}")

    conn.commit()
    conn.close()

    # Return a JSON response for AJAX
    return jsonify(success=True)



@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    star = request.form['star']
    comments = request.form['comments']
    user_id = request.form['user_id']
    date_created = datetime.now().strftime('%d/%m/%Y')
    # philippine_tz = timezone(timedelta(hours=8))
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')


    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rating (star, comments, User_ID, date_created) VALUES (?, ?, ?, ?)",
                   (star, comments, user_id, current_time_pht))

    # Get jobseeker details from `users` table
    rating_id = cursor.lastrowid
    print(f"Newly inserted Rating ID: {rating_id}")
    cursor.execute('SELECT profile, fname, userType FROM users WHERE User_ID = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        picture = user[0]  # profile (picture)
        fname = user[1]    # fname
        userType = user[2] # userType
    
        
        cursor.execute('SELECT star, comments FROM rating WHERE RatingID = ?', (rating_id,))
        rating = cursor.fetchone()
        
        if rating:
            star = rating[0]
            comments = rating[1]

            # Create notification text
            notification_text = f"{fname} gives a rate of {star}. {comments}"
            
            # Insert notification into `admin_notification` table
            cursor.execute('''
                INSERT INTO admin_notification (user_id, userType, picture, fname, notification_text, notification_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, userType, picture, fname, notification_text, current_time_pht))

            print(f"Admin Notification: {notification_text}")


    conn.commit()
    conn.close()
    
    return redirect(url_for('jobseeker'))


@app.route('/use_default_resume', methods=['GET', 'POST'])
def use_default_resume():
    session_id = session.get('user_id')  # Get user ID from session
    if not session_id:
        return {"error": "User is not logged in."}, 401

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT resume_form FROM users WHERE User_ID = ?', (session_id,))
    result = cursor.fetchone()

    if result:
        resume_form = result[0]
        
        if request.method == 'POST':
            job_id = request.form['job_id']
            employer_id = request.form['employer_id']
            
            # Construct the file path for the default resume
            file_path = os.path.join('static/images/jobseeker-uploads', resume_form)

            # Insert into applicant table using the file path
            initial_status = 'Pending'
            cursor.execute(''' 
                INSERT INTO applicant (job_id, employer_id, jobseeker_id, jobseeker_name, email, contact_no, form, status, date_request) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id, employer_id, session_id, 
                session.get('user_fname'), session.get('user_email'), 
                session.get('user_contact'), file_path, initial_status, 
                datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')
            ))

            # Retrieve the last inserted applicant ID and its status
            applicant_id = cursor.lastrowid
            cursor.execute('SELECT status FROM applicant WHERE applicant_id = ?', (applicant_id,))
            applicant_status = cursor.fetchone()[0]

            # Get employer's email and company name
            cursor.execute('''
                SELECT jobs.company, users.email, jobs.employer_id 
                FROM jobs 
                JOIN users ON jobs.employer_id = users.User_ID 
                WHERE jobs.Job_ID = ?
            ''', (job_id,))
            employer_info = cursor.fetchone()            

            if employer_info:
                company_name, employer_email, employer_id = employer_info
                print(f"Company Name: {company_name}")
                print(f"Employer Email: {employer_email}")
                print(f"Employer ID: {employer_id}")
                
                # Insert into application_status
                status_description = f"Your application at {company_name} is now being processed. Status: {applicant_status}"
                date_posted = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

                cursor.execute('''
                    INSERT INTO application_status (
                        applicant_id, job_id, jobseeker_id, employer_id, 
                        status_description, status_type, company, date_posted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    applicant_id, job_id, session_id, employer_id, 
                    status_description, applicant_status, company_name, date_posted
                ))
                print(f"Status record created for applicant ID {applicant_id} with status '{applicant_status}'.")

                conn.commit()

                # Send email to the employer
                send_employer_email_from_applicant(employer_email, session.get('user_fname'), company_name)
                print("Email sent to employer.")

                return {"success": "Default resume used and application submitted."}
            else:
                print("Employer information not found.")
                return {"error": "Employer information not found."}, 404            
    
    return {"error": "No default resume found for this user."}, 404
