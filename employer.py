from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify, send_from_directory,abort
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
#___________________________________
import logging
from logging import FileHandler
from main import app
import random
import pytz
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
timezone = pytz.timezone('Asia/Manila')
philippine_tz = pytz.timezone('Asia/Manila')


timezone = pytz.timezone('Asia/Manila')

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
app.permanent_session_lifetime = timedelta(minutes=1800)  # Set session timeout to 30 minutes


app.config['EMPLOYER_UPLOAD_FOLDER'] = 'static/images/employer-uploads'
app.config['JOBSEEKER_UPLOAD_FOLDER'] = 'static/images/jobseeker-uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif','pdf'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# This is the connection
def get_db_connection():
    conn = sqlite3.connect('trabahanap.db')
    conn.row_factory = sqlite3.Row
    return conn




# This is Employer
@app.route('/employer', methods=['GET', 'POST'])
def employer():
    # Check if user is authenticated and is an Employer
    if 'user_id' not in session or session.get('user_type') != 'Employer':
        print('Redirecting to sign-in due to missing user session or invalid user type')  # Debugging print statement
        return redirect(url_for('signin'))

    # Set session start time if it doesn't exist
    if 'session_start' not in session:
        session['session_start'] = datetime.now(timezone)  # Make this aware with timezone

    # Retrieve session start time and check for timeout (e.g., 60 minutes)
    session_start = session['session_start']
    if datetime.now(timezone) - session_start > timedelta(minutes=1800):
        print('Session has timed out, updating user state and redirecting')  # Debugging print statement
        
        # Update currentState to Inactive in the database
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE users SET currentState = 'Inactive' WHERE User_ID = ?''', (session['user_id'],))
        conn.commit()
        cursor.close()
        conn.close()

        # Clear session data
        session.clear()
        print('Session cleared, redirecting to sign-in')  # Debugging print statement
        
        # Return JSON response to indicate session timeout
        return jsonify({'session_timeout': True})

    # Fetch user profile picture
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT profile FROM users WHERE User_ID = ?", (user_id,))
    profile_picture = cursor.fetchone()[0]
    conn.close()

    # Check if profile picture is NULL or empty
    if profile_picture is None or profile_picture == '':
        profile_picture = 'images/employer-images/user_1.png'  # Set default image path

    # If session is still active, render the employer page
    return render_template('employer/employer.html')






































@app.route('/fetch_myListPosted', methods=['GET'])
def fetch_myListPosted():
    employer_id = session.get('user_id')  # Get employer ID from session

    # Print for debugging
    print(f"Fetching jobs for employer ID: {employer_id}")

    # Establish a database connection
    conn = get_db_connection()

    # Build the query to fetch all jobs for the employer
    query = "SELECT * FROM jobs WHERE employer_ID = ?"
    params = [employer_id]

    # Fetch all jobs for the specific employer
    jobs = conn.execute(query, params).fetchall()

    # Debugging: Print all jobs in the table
    all_jobs_query = "SELECT * FROM jobs"
    all_jobs = conn.execute(all_jobs_query).fetchall()
    # print("All jobs in the table:")
    # for job in all_jobs:
        # print(dict(job))  # Print each job as a dictionary

    conn.close()

    # Prepare data for JSON response
    jobs_list = [dict(job) for job in jobs]  # Convert to list of dicts

    # Print the fetched jobs for debugging
    print(f"Fetched {len(jobs_list)} jobs for employer ID {employer_id}.")  # Debugging print

    return jsonify({"jobs": jobs_list})

@app.route('/filter_myListPosted', methods=['GET'])
def filter_myListPosted():
    employer_id = session.get('user_id')  # Get employer ID from session
    
    # Get filter parameters from the request
    title = request.args.get('title', '')  # Default to an empty string if not provided
    position = request.args.get('position', '')
    company = request.args.get('company', '')
    skills = request.args.get('skills', '')

    # Establish a database connection
    conn = get_db_connection()

    # Build the query to fetch all jobs for the employer
    query = """
    SELECT * FROM jobs 
    WHERE employer_ID = ? 
    AND (title LIKE ? OR ? = '') 
    AND (position LIKE ? OR ? = '')
    AND (Company LIKE ? OR ? = '')
    AND (skills LIKE ? OR ? = '')
    """

    # Parameters for the query
    params = [
        employer_id,
        f'%{title}%', title,
        f'%{position}%', position,
        f'%{company}%', company,
        f'%{skills}%', skills
    ]

    # Execute the query and fetch jobs
    jobs = conn.execute(query, params).fetchall()
    conn.close()

    # Prepare data for JSON response
    jobs_list = [dict(job) for job in jobs]  # Convert to list of dicts

    # Print for debugging
    print(f"Fetched {len(jobs_list)} jobs with filters: title={title}, position={position}, company={company}, skills={skills}.")

    return jsonify({"jobs": jobs_list})






































@app.route('/fetch_applicant_stats', methods=['GET'])
def fetch_applicant_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch total number of applicants
    cursor.execute("SELECT COUNT(Applicant_ID) FROM applicant")
    total_applicants = cursor.fetchone()[0]

    # Fetch total number of approved applicants
    cursor.execute("SELECT COUNT(Applicant_ID) FROM applicant WHERE status = 'Approved'")
    approved_applicants = cursor.fetchone()[0]

    # Fetch total number of denied applicants
    cursor.execute("SELECT COUNT(Applicant_ID) FROM applicant WHERE status = 'Denied'")
    denied_applicants = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        'total_applicants': total_applicants,
        'approved_applicants': approved_applicants,
        'denied_applicants': denied_applicants
    })


@app.route('/fetch_educational_attainment', methods=['GET'])
def fetch_educational_attainment():
    # Establish a connection to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all data from form101
    cursor.execute("""
        SELECT form101_id, elementary, senior_high, tertiary, graduate_studies, vocational_training
        FROM form101
    """)
    rows = cursor.fetchall()

    # Prepare the data for the frontend
    data = {
        'elementary': 0,
        'senior_high': 0,
        'tertiary': 0,
        'graduate_studies': 0,
        'vocational_training': 0
    }
    
    # Iterate through each row to find the highest attainment and count the valid entries
    for row in rows:
        form101_id = row[0]
        elementary = row[1]
        senior_high = row[2]
        tertiary = row[3]
        graduate_studies = row[4]
        vocational_training = row[5]

        # Determine the highest attainment
        attainment_levels = [
            ('elementary', elementary),
            ('senior_high', senior_high),
            ('tertiary', tertiary),
            ('graduate_studies', graduate_studies),
            ('vocational_training', vocational_training),
        ]
        
        highest_attainment = None
        
        for level, value in attainment_levels:
            if value and value.strip():  # Ignore NULL or empty string
                if highest_attainment is None or attainment_levels.index((level, value)) > attainment_levels.index(highest_attainment):
                    highest_attainment = (level, value)

        # Print the highest attainment per form101_id
        if highest_attainment:
            print(f"form101_id: {form101_id}, Highest attainment: {highest_attainment[0]}")

            # Increment the count for the corresponding educational attainment
            data[highest_attainment[0]] += 1

    # Close the database connection
    conn.close()

    # Count totals for each educational attainment level
    data_counts = {
        'elementary': data['elementary'],
        'senior_high': data['senior_high'],
        'tertiary': data['tertiary'],
        'graduate_studies': data['graduate_studies'],
        'vocational_training': data['vocational_training']
    }

    # Return the counts in the desired format
    return jsonify(data_counts)





@app.route('/check_interview_status/<int:applicant_id>', methods=['GET'])
def check_interview_status(applicant_id):
    # Establish a connection to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the "interviewed" status from the application_status table
    cursor.execute("SELECT interviewed FROM application_status WHERE applicant_id = ?", (applicant_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        interviewed_status = result[0]
        # Return whether the field should be disabled based on the "interviewed" status
        return jsonify({'disabled': interviewed_status == 'YES'})
    else:
        return jsonify({'disabled': False})


        






@app.route('/count_applicant_and_jobs', methods=['GET'])
def count_applicant_and_jobs():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query counts from respective tables
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE jobStatus='Available' AND request='Approved'")
    job_posted_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM application_status WHERE status_type='Hire'")
    got_hired_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE jobStatus='Unavailable'")
    job_closed_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applicant")
    applicant_count = cursor.fetchone()[0]

    # Close connection
    cursor.close()
    connection.close()

    return jsonify({
        "job_posted": job_posted_count,
        "got_hired": got_hired_count,
        "job_closed": job_closed_count,
        "applicants": applicant_count
    })



























@app.route('/get_notes', methods=['GET'])
def get_notes():
    date = request.args.get('date')
    print(f"Fetching notes for date: {date}")  # Debugging print statement

    conn = get_db_connection()
    cursor = conn.execute('SELECT calendar_id, note FROM calendar WHERE date = ?', (date,))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        # Concatenate all notes into a single string
        combined_notes = "\n".join([row['note'] for row in rows])
        # Return all calendar IDs for the date
        calendar_ids = [row['calendar_id'] for row in rows]

        print(f"Found notes: {combined_notes}")  # Debugging print statement
        return jsonify({'calendar_ids': calendar_ids, 'notes': combined_notes})
    else:
        print("No note found for the given date")  # Debugging print statement
        return jsonify({'calendar_ids': [], 'notes': ''})












@app.route('/save_note', methods=['POST'])
def save_note():
    data = request.get_json()
    calendar_id = data.get('calendar_id')
    date = data['date']
    note = data['note']
    
    print(f"Saving note: calendar_id={calendar_id}, date={date}, note={note}")  # Debugging print statement
    
    conn = get_db_connection()
    
    if calendar_id is None:  # Insert new note
        print("Inserting new note")  # Debugging print statement
        conn.execute('INSERT INTO calendar (date, note) VALUES (?, ?)', (date, note))
    else:  # Update existing note
        print("Updating existing note")  # Debugging print statement
        conn.execute('UPDATE calendar SET date = ?, note = ? WHERE calendar_id = ?', (date, note, calendar_id))
    
    conn.commit()
    conn.close()
    
    print("Note saved successfully")  # Debugging print statement
    return jsonify({'status': 'success'})

@app.route('/get_calendar_notes', methods=['GET'])
def get_calendar_notes():
    date = request.args.get('date')
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM calendar WHERE date = ?', (date,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({'scheduled': True})
    else:
        return jsonify({'scheduled': False})




@app.route('/remove_note', methods=['POST'])
def remove_note():
    data = request.get_json()
    calendar_id = data.get('calendar_id')

    if calendar_id:
        # Establish a connection to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete the note entry from the calendar table
        cursor.execute("DELETE FROM calendar WHERE calendar_id = ?", (calendar_id,))

        # Commit the changes to the database and close the connection
        conn.commit()
        conn.close()

        return jsonify({'status': 'success'})

    return jsonify({'status': 'error', 'message': 'Invalid calendar_id'})


@app.route('/update_applicant_schedule', methods=['POST'])
def update_applicant_schedule():
    applicant_id = request.form['id']
    new_schedule = request.form['schedule']
    
    # Check if the provided schedule has seconds
    if len(new_schedule) == 16:  # Format 'YYYY-MM-DD HH:MM'
        new_schedule += ':00'  # Append seconds if missing

    # Establish a connection to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the current time in Philippine Time (UTC+8)
    philippine_tz = pytz.timezone('Asia/Manila')
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Fetch the company, jobseeker_id, employer_id, and email associated with the applicant
    cursor.execute("""
        SELECT application_status.company, application_status.jobseeker_id, application_status.employer_id, users.email 
        FROM application_status 
        JOIN users ON application_status.jobseeker_id = users.User_ID 
        WHERE application_status.applicant_id = ?
    """, (applicant_id,))
    result = cursor.fetchone()

    if result:
        company, jobseeker_id, employer_id, email = result  # Now includes email
        
        # Fetch the fname of the jobseeker
        cursor.execute("SELECT fname FROM users WHERE User_ID = ? AND userType = 'Jobseeker'", (jobseeker_id,))
        user_result = cursor.fetchone()
        fname = user_result[0] if user_result else 'Unknown'

        # Fetch the fname of the employer
        cursor.execute("SELECT fname FROM users WHERE User_ID = ? AND userType = 'Employer'", (employer_id,))
        employer_result = cursor.fetchone()
        employer_name = employer_result[0] if employer_result else 'Unknown'

        # Check current scheduled value
        cursor.execute("SELECT scheduled FROM application_status WHERE applicant_id = ?", (applicant_id,))
        scheduled_result = cursor.fetchone()
        is_rescheduled = scheduled_result[0] is not None if scheduled_result else False

        # Extract date from the new_schedule
        scheduled_datetime = datetime.strptime(new_schedule, '%Y-%m-%d %H:%M:%S')  # Convert to datetime object
        scheduled_date = new_schedule.split(' ')[0]  # Get 'YYYY-MM-DD'

        # Check if an entry for the applicant_id already exists in the calendar table
        cursor.execute("SELECT calendar_id FROM calendar WHERE applicant_id = ?", (applicant_id,))
        calendar_result = cursor.fetchone()

        if calendar_result:
            calendar_id = calendar_result[0]
            # Update the existing calendar entry
            cursor.execute(""" 
                UPDATE calendar 
                SET date = ?, note = ? 
                WHERE calendar_id = ?
            """, (scheduled_date, f"{employer_name} set a schedule for his/her applicant {fname} for {company}", calendar_id))
            
        else:
            # Insert a new calendar entry
            cursor.execute(""" 
                INSERT INTO calendar (applicant_id, date, note) 
                VALUES (?, ?, ?)
            """, (applicant_id, scheduled_date, f"{employer_name} set a schedule for his/her applicant {fname} for {company}"))
        
        # Update the schedule in the application_status table
        cursor.execute(""" 
            UPDATE application_status 
            SET scheduled = ?, status_type = 'Scheduled', status_description = ?, date_posted = ? 
            WHERE applicant_id = ? 
        """, (
            new_schedule, 
            f"Your application at {company} was scheduled at {scheduled_datetime}",
            current_time_pht,
            applicant_id
        ))

        # Now also update the schedule in the applicant table where Applicant_ID matches
        cursor.execute(""" 
            UPDATE applicant 
            SET schedule = ? 
            WHERE Applicant_ID = ?
        """, (new_schedule, applicant_id))

        # Send the scheduling email
        send_schedule_message(email, company, scheduled_datetime, is_rescheduled)  # Send email to jobseeker

    # Commit the changes to both tables and close the connection
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

def send_schedule_message(email, company, scheduled_date, is_rescheduled=False):
    sender_email = "reignjosephc.delossantos@gmail.com"
    password = "vfwd oaaz ujog gikm"  # Use app password or OAuth2 for better security

    # Create the email
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = email
    message['Subject'] = "BustosPESO - Job Application Status Update"

    # Format the scheduled date into a more readable format
    formatted_date = scheduled_date.strftime("%B %d, %Y %I:%M %p")  # e.g., "October 10, 2024 12:00 PM"

    # Determine email body based on whether it is a reschedule
    if is_rescheduled:
        body = f"Dear User,\n\nWe wanted to inform you that your application at {company} has been rescheduled for {formatted_date}.\n\nBest regards,\nBustosPESO Support Team"
    else:
        body = f"Dear User,\n\nWe wanted to inform you that your application at {company} has been scheduled for {formatted_date}.\n\nBest regards,\nBustosPESO Support Team"

    message.attach(MIMEText(body, 'plain'))

    try:
        # Establish a secure session with SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, password)  # Login to your email account
            server.send_message(message)  # Send the email
        print("Schedule email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")







@app.route('/update_interview_status', methods=['POST'])
def update_interview_status():
    applicant_id = request.form['id']
    interviewed = request.form['interviewed']

    # Get current time in Philippine Time (UTC+8)
    philippine_tz = pytz.timezone('Asia/Manila')
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Define status description
    status_description = "Your interview is now being processed, please wait for the result within a week."
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Print the current time for debugging
        print(f"Updating interview status for applicant_id={applicant_id}")
        print(f"Current Philippine time (date_posted) to be updated: {current_time_pht}")

        # Update the interviewed field, status_type, date_posted, and status_description in the application_status table
        cursor.execute('''
            UPDATE application_status
            SET interviewed = ?,
                status_type = 'Interviewed',
                date_posted = ?,
                status_description = ?
            WHERE applicant_id = ?
        ''', (interviewed, current_time_pht, status_description, applicant_id))

        conn.commit()
        conn.close()

        return jsonify({'status': 'success'})

    except Exception as e:
        print(f"Error updating interview status: {e}")
        return jsonify({'error': 'An error occurred while updating interview status'}), 500


def send_interview_email(email, company):
    sender_email = "reignjosephc.delossantos@gmail.com"
    password = "vfwd oaaz ujog gikm"  # Use app password or OAuth2 for better security

    # Create the email
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = email
    message['Subject'] = "BustosPESO - Job Application Status Update"

    body = f"Dear User,\n\nWe wanted to inform you that your interview for applying at {company} is now being processed. Please wait for the result within a week. If there's still no update, please contact us.\n\nBest regards,\nBustosPESO Support Team"
    message.attach(MIMEText(body, 'plain'))

    try:
        # Establish a secure session with SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, password)  # Login to your email account
            server.send_message(message)  # Send the email
        print("Interview email sent successfully.")
    except Exception as e:
        print(f"Error sending interview email: {e}")





@app.route('/update_interview_result', methods=['POST'])
def update_interview_result():
    applicant_id = request.form['id']
    result = request.form['result']
    reason = request.form.get('reason')  # Fetch the rejection reason if provided

    # Get current time in Philippine Time (UTC+8)
    philippine_tz = pytz.timezone('Asia/Manila')
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the jobseeker_id from the application_status table
        cursor.execute('SELECT jobseeker_id FROM application_status WHERE applicant_id = ?', (applicant_id,))
        jobseeker = cursor.fetchone()

        if jobseeker is None:
            return jsonify({'status': 'error', 'message': 'Jobseeker ID not found'}), 404

        jobseeker_id = jobseeker[0]

        # Fetch job details and email from the applicant and users tables
        cursor.execute(''' 
            SELECT j.company, j.position, u.email  -- Select the company, position, and email fields
            FROM jobs j
            JOIN applicant a ON a.job_id = j.Job_ID
            JOIN users u ON u.User_ID = ?
            WHERE a.Applicant_ID = ?
        ''', (jobseeker_id, applicant_id))
        
        job_details = cursor.fetchone()

        if job_details is None:
            return jsonify({'status': 'error', 'message': 'Job details not found'}), 404

        company, position, email = job_details  # Unpack the results

        if result == "Hire":
            status_type = "Hire"
            status_description = f"Congratulations! You are now hired at {company} as a {position}."

            # Create the email body for hiring
            body = f"Dear User,\n\nWe wanted to inform you that you have been hired at {company} as a {position}. If there's still no update, please contact us.\n\nBest regards,\nBustosPESO Support Team"

        elif result == "Reject":
            status_type = "Reject"
            if reason:
                status_description = f"Your application was rejected for the following reason: {reason}"
                body = f"Dear User,\n\nWe wanted to inform you that your interview for applying at {company} is rejected. Reason: {reason}. If there's still no update, please contact us.\n\nBest regards,\nBustosPESO Support Team"
            else:
                status_description = f"Unfortunately, you were not selected for the position at {company}."
                body = f"Dear User,\n\nWe wanted to inform you that your interview for applying at {company} is rejected. If there's still no update, please contact us.\n\nBest regards,\nBustosPESO Support Team"

        else:
            status_type = result
            status_description = f"Your interview status is {result}."
            body = f"Dear User,\n\nYour interview status is {result}. If there's still no update, please contact us.\n\nBest regards,\nBustosPESO Support Team"

        # Update the status in the application_status table
        cursor.execute('''
            UPDATE application_status
            SET status_type = ?, date_posted = ?, result = ?, status_description = ?
            WHERE applicant_id = ?
        ''', (status_type, current_time_pht, result, status_description, applicant_id))

        conn.commit()

        # Send email notification
        send_result_email(email, body)

    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

    finally:
        conn.close()

    return jsonify({'status': 'success'})

def send_result_email(to_email, body):
    sender_email = "reignjosephc.delossantos@gmail.com"
    password = "vfwd oaaz ujog gikm"  # Use app password or OAuth2 for better security

    # Create the email
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = to_email
    message['Subject'] = "BustosPESO - Job Application Status Update"

    message.attach(MIMEText(body, 'plain'))

    try:
        # Establish a secure session with the SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Upgrade to a secure connection
            server.login(sender_email, password)  # Log in to your email account
            server.send_message(message)  # Send the email
    except Exception as e:
        print(f"Error sending email: {e}")



@app.route('/fetch_interview_result', methods=['POST'])
def fetch_interview_result():
    applicant_id = request.form['id']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the interview result from the application_status table
        cursor.execute("""
            SELECT result
            FROM application_status
            WHERE applicant_id = ?
        """, (applicant_id,))
        
        result = cursor.fetchone()

        # Return the result if found, else return None
        if result:
            return jsonify({'result': result[0]})
        else:
            return jsonify({'result': None})  # Return None if no result found

    except Exception as e:
        print(f"Error fetching interview result: {e}")
        return jsonify({'error': 'An error occurred while fetching interview result'}), 500
    finally:
        conn.close()


@app.route('/check_interview_availability', methods=['POST'])
def check_interview_availability():
    applicant_id = request.form['id']
    
    # Establish a connection to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the current time in Philippine Time (UTC+8)
    philippine_tz = pytz.timezone('Asia/Manila')
    current_time_pht = datetime.now(philippine_tz)
    
    # Fetch the scheduled time for the applicant
    cursor.execute('''SELECT scheduled FROM application_status WHERE applicant_id = ?''', (applicant_id,))
    result = cursor.fetchone()

    conn.close()

    if result and result[0] is not None:
        scheduled_time_str = result[0]
        try:
            # Parse the scheduled time
            if len(scheduled_time_str) == 16:  # Format 'YYYY-MM-DD HH:MM'
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M')
                scheduled_time = philippine_tz.localize(scheduled_time)  # Localize to Philippine Time
            elif len(scheduled_time_str) == 19:  # Format 'YYYY-MM-DD HH:MM:SS'
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
                scheduled_time = philippine_tz.localize(scheduled_time)  # Localize to Philippine Time
            else:
                raise ValueError("Unexpected date format")

            # Compare scheduled time with current time
            if scheduled_time < current_time_pht:
                return jsonify({'status': 'show'})
            else:
                return jsonify({'status': 'hide'})
        except ValueError as e:
            # Handle any parsing errors
            print(f"Date parsing error: {e}")
            return jsonify({'status': 'hide'})
    else:
        # Handle the case where no scheduled time was found or it was None
        print(f"No scheduled time found for applicant ID {applicant_id}")
        return jsonify({'status': 'hide'})


@app.route('/fetch_approved_applicants', methods=['GET'])
def fetch_approved_applicants():
    try:
        # Ensure the user is logged in and is an employer
        if 'user_id' in session and session['user_type'] == 'Employer':
            employer_id = session['user_id']  # Get the employer's user_id from the session

            conn = sqlite3.connect('trabahanap.db')
            cursor = conn.cursor()

            # Fetch applicants with "Approved" status and their corresponding company where employer_id matches
            # Add condition for emloyer_popup to be NULL or an empty string
            cursor.execute('''
                SELECT 
                    applicant.Applicant_ID, 
                    applicant.job_id, 
                    applicant.employer_id, 
                    applicant.jobseeker_id, 
                    applicant.jobseeker_name, 
                    applicant.email, 
                    applicant.contact_no, 
                    applicant.form, 
                    applicant.schedule, 
                    applicant.status, 
                    applicant.date_request, 
                    jobs.Company,  -- Assuming "Company" is a field in the jobs table
                    users.profile,
                    application_status.interviewed  -- Fetch the interviewed status
                FROM 
                    applicant
                JOIN 
                    jobs 
                ON 
                    applicant.job_id = jobs.Job_ID
                JOIN
                    users
                ON
                    applicant.jobseeker_id = users.User_ID
                LEFT JOIN
                    application_status
                ON
                    applicant.Applicant_ID = application_status.applicant_id
                WHERE 
                    applicant.status = ? AND
                    applicant.employer_id = ? AND
                    (application_status.employer_popup IS NULL OR application_status.employer_popup = '')  -- Restrict employer_popup to be NULL or empty
            ''', ('Approved', employer_id))

            applicants = cursor.fetchall()

            conn.close()

            approved_applicant_list = []
            for row in applicants:
                approved_applicant_list.append({
                    'Applicant_ID': row[0],
                    'job_id': row[1],
                    'employer_id': row[2],
                    'jobseeker_id': row[3],
                    'jobseeker_name': row[4],
                    'email': row[5],
                    'contact_no': row[6],
                    'form': row[7],
                    'schedule': row[8],
                    'status': row[9],
                    'date_request': row[10],
                    'Company': row[11],
                    'profile': row[12],
                    'interviewed': row[13]  # Add the interviewed information
                })

            return jsonify(approved_applicant_list)

        else:
            return jsonify({'error': 'Unauthorized access or invalid session'}), 401

    except Exception as e:
        print(f"Error fetching applicants: {e}")
        return jsonify({'error': 'An error occurred while fetching applicants'}), 500


@app.route('/close_applicant_history/<int:applicant_id>', methods=['POST'])
def close_applicant_history(applicant_id):
    try:
        # Connect to the database
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()

        # Update the 'popup' field in the application_status table to 'false' for the given applicant_id
        cursor.execute('''
            UPDATE application_status 
            SET employer_popup = 'false'
            WHERE applicant_id = ?
        ''', (applicant_id,))
        conn.commit()

        # Check if any row was updated
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'No such applicant or popup already closed'}), 404

        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error closing applicant popup: {e}")
        return jsonify({'error': 'An error occurred while closing the popup'}), 500















@app.route('/fetch_applicants', methods=['GET'])
def fetch_applicants():
    try:
        # Ensure the user is logged in and is an employer
        if 'user_id' in session and session['user_type'] == 'Employer':
            employer_id = session['user_id']  # Get the employer's user_id from the session

            conn = sqlite3.connect('trabahanap.db')
            cursor = conn.cursor()

            # Fetch applicants with "Pending" status and their corresponding company where employer_id matches
            cursor.execute('''
                SELECT 
                    applicant.Applicant_ID, 
                    applicant.job_id, 
                    applicant.employer_id, 
                    applicant.jobseeker_id, 
                    applicant.jobseeker_name, 
                    applicant.email, 
                    applicant.contact_no, 
                    applicant.form, 
                    applicant.schedule, 
                    applicant.status, 
                    applicant.date_request, 
                    jobs.Company,  -- Assuming "Company" is a field in the jobs table
                    users.profile
                FROM 
                    applicant
                JOIN 
                    jobs 
                ON 
                    applicant.job_id = jobs.Job_ID
                JOIN
                    users
                ON
                    applicant.jobseeker_id = users.User_ID
                WHERE 
                    applicant.status = ? AND
                    applicant.employer_id = ?  -- Add the employer_id match condition
            ''', ('Pending', employer_id))

            applicants = cursor.fetchall()
            # print("Fetched applicants with Pending status and Company from DB:", applicants)  # Debug the SQL response

            conn.close()

            applicant_list = []
            for row in applicants:
                # print(f"Processing row: {row}")  # Debug each row as it's processed
                applicant_list.append({
                    'Applicant_ID': row[0],
                    'job_id': row[1],
                    'employer_id': row[2],
                    'jobseeker_id': row[3],
                    'jobseeker_name': row[4],
                    'email': row[5],
                    'contact_no': row[6],
                    'form': row[7],
                    'schedule': row[8],
                    'status': row[9],
                    'date_request': row[10],
                    'Company': row[11],  # Add the company information
                    'profile': row[12],
                })

            return jsonify(applicant_list)

        else:
            return jsonify({'error': 'Unauthorized access or invalid session'}), 401

    except Exception as e:
        print(f"Error fetching applicants: {e}")
        return jsonify({'error': 'An error occurred while fetching applicants'}), 500




@app.route('/update_applicant_status', methods=['POST'])
def update_applicant_status():
    try:
        philippine_tz = pytz.timezone('Asia/Manila')
        current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')
        data = request.get_json()
        applicant_id = data.get('applicant_id')
        status = data.get('status')
        denied_reason = data.get('denied_reason')  # Get denied reason if applicable from textarea

        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()

        # Fetch details from the applicant table based on applicant_id
        cursor.execute('''
            SELECT job_id, employer_id, jobseeker_id
            FROM applicant
            WHERE Applicant_ID = ?
        ''', (applicant_id,))
        applicant = cursor.fetchone()

        if applicant is None:
            print(f"Error: Applicant not found for ID: {applicant_id}")
            return jsonify({'error': 'Applicant not found'}), 404

        job_id, employer_id, jobseeker_id = applicant
        print(f"Fetched applicant details: job_id={job_id}, employer_id={employer_id}, jobseeker_id={jobseeker_id}")

        # Fetch company name from the jobs table using job_id
        cursor.execute('''
            SELECT company
            FROM jobs
            WHERE Job_ID = ?
        ''', (job_id,))
        job = cursor.fetchone()

        if job is None:
            print(f"Error: Job not found for Job_ID: {job_id}")
            return jsonify({'error': 'Job not found'}), 404

        company = job[0]
        print(f"Fetched company: {company}")

        # Fetch employer fname based on employer_id from users table
        cursor.execute('SELECT fname FROM users WHERE User_ID = ?', (employer_id,))
        employer = cursor.fetchone()

        if employer:
            employer_fname = employer[0]  # Employer's fname
        else:
            employer_fname = f"Employer ID {employer_id}"

        # Fetch applicant's email address
        cursor.execute('SELECT email FROM users WHERE User_ID = ?', (jobseeker_id,))
        applicant_email = cursor.fetchone()
        if applicant_email:
            email = applicant_email[0]  # Get the email
        else:
            print(f"Error: Email not found for jobseeker ID: {jobseeker_id}")
            return jsonify({'error': 'Email not found for the jobseeker'}), 404

        # Define status descriptions based on the status
        if status == "Approved":
            status_descriptions = [
                f"Your application at {company} is {status}.",
                f"Update: Your application status at {company} is {status}.",
                f"Notification: Your application for the position at {company} is {status}.",
                f"Alert: The status of your application at {company} is {status}.",
                f"Info: Your application status at {company} has changed to {status}."
            ]
        elif status == "Denied":
            status_descriptions = [
                f"Your application at {company} is {status} due to a mismatch of your resume.",
                f"We're sad to inform you that your application is {status}.",
                f"Alert: The status of your application at {company} is {status}."
            ]
        else:
            status_descriptions = [
                f"Your application at {company} is {status}.",
                f"Alert: The status of your application at {company} has changed to {status}."
            ]

        # Choose a random status description
        status_description = random.choice(status_descriptions)
        print(f"Generated status description: {status_description}")

        # Update the applicant's status in the applicant table
        cursor.execute('''
            UPDATE applicant
            SET status = ?
            WHERE Applicant_ID = ?
        ''', (status, applicant_id))

        print(f"Updated applicant ID {applicant_id} status to {status}")

        # Update the application_status table based on existing records
        cursor.execute('''
            UPDATE application_status
            SET status_description = ?, status_type = ?, date_posted = ?
            WHERE applicant_id = ?
        ''', (status_description, status, current_time_pht, applicant_id))

        print(f"Updated application_status for applicant_id {applicant_id}")

        # Send email notification
        if status == "Denied":
            send_applicant_status_update_email(email, company, status, denied_reason)
        else:
            send_applicant_status_update_email(email, company, status)

        # Commit the transaction and close the connection
        conn.commit()
        conn.close()

        return jsonify({'message': 'Status updated successfully!'})

    except Exception as e:
        print(f"Error updating applicant status: {e}")
        return jsonify({'error': 'An error occurred while updating applicant status'}), 500


def send_applicant_status_update_email(email, company, status_type, denied_reason=None):
    try:
        sender_email = "reignjosephc.delossantos@gmail.com"
        password = "vfwd oaaz ujog gikm"  # Use app password or OAuth2 for better security

        # Create the email
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = email
        message['Subject'] = "BustosPESO - Job Application Status Update"

        if status_type == "Denied":
            body = f"Dear User,\n\nWe wanted to inform you that your application at {company} has been {status_type}."
            if denied_reason:
                body += f"\n\nReason: {denied_reason}"
            body += "\n\nIf you have any questions, feel free to reach out to our support team.\n\nBest regards,\nBustosPESO Support Team"

        else:  # Assuming status_type is "Approved"
            body = f"Dear User,\n\nWe wanted to inform you that your application at {company} has been {status_type}. Please wait to be schedule your interview."
            body += "\n\nIf you have any questions, feel free to reach out to our support team.\n\nBest regards,\nBustosPESO Support Team"

        # Attach the body with the msg instance
        message.attach(MIMEText(body, 'plain'))

        # Send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.send_message(message)

        print(f"Email sent successfully to {email}")

    except Exception as e:
        print(f"Error sending email: {e}")







@app.route('/employer_profile_update', methods=['POST'])
def employer_profile_update():
    if 'profile_picture' not in request.files:
        return jsonify(success=False, error="No file part"), 400
    
    file = request.files['profile_picture']
    
    if file.filename == '':
        return jsonify(success=False, error="No selected file"), 400
    
    # Save the file
    filename = secure_filename(file.filename)  # Use secure_filename to prevent issues
    file_path = os.path.join('static/images/employer-images/', filename)
    file.save(file_path)

    # Get the current user's ID from the session
    user_id = session.get('user_id')  # Assumes you store the User_ID in session['user_id']
    
    if not user_id:
        return jsonify(success=False, error="User not logged in"), 400

    # Connect to the database and update the profile picture
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update the profile picture path in the database
        cursor.execute('UPDATE users SET profile = ? WHERE User_ID = ?', (filename, user_id))
        conn.commit()  # Commit after updating users table

        # Get user details for notification
        cursor.execute('SELECT fname, userType FROM users WHERE User_ID = ?', (user_id,))
        user = cursor.fetchone()

        if user:
            fname = user[0]    # First name
            userType = user[1] # User type
            notification_text = f"{fname} has updated their profile picture."

            # Insert notification into admin_notification table
            cursor.execute('''
                INSERT INTO admin_notification (user_id, userType, picture, fname, notification_text, notification_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, userType, filename, fname, notification_text, datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()  # Commit after inserting notification
            print(f"Admin Notification: {notification_text}")

    except Exception as e:
        conn.rollback()  # Rollback in case of error
        print(f"Error during update or notification insertion: {e}")
        return jsonify(success=False, error="Internal Server Error"), 500
    finally:
        # Close the connection
        conn.close()

    # Update the session to reflect the new profile picture
    session['user_profile'] = filename
    
    return jsonify(success=True, image_url=url_for('static', filename='images/employer-images/' + filename))





@app.route('/profile_employer', methods=['GET', 'POST'])
def profile_employer():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Update user information
        contact = request.form['contact']
        bio = request.form['bio']
        address = request.form['address']  # New address field

        # Update the user's profile in the `users` table
        cursor.execute('''
            UPDATE users
            SET contactnum = ?, bio = ?, address = ?
            WHERE User_ID = ?
        ''', (contact, bio, address, user_id))
        conn.commit()

        # Get updated user details for the notification
        cursor.execute('SELECT profile, fname, userType FROM users WHERE User_ID = ?', (user_id,))
        user = cursor.fetchone()

        if user:
            picture = user[0]  # Profile picture (or placeholder)
            fname = user[1]    # First name
            userType = user[2] # User type (e.g., employer)
            
            # Create the notification text
            notification_text = f"{fname} has updated their profile."

            # Insert notification into `admin_notification` table
            current_time_pht = datetime.now(pytz.timezone('Asia/Manila')).strftime('%Y-%m-%d %H:%M:%S')  # Assuming you're using timezone aware timestamps
            cursor.execute('''
                INSERT INTO admin_notification (user_id, userType, picture, fname, notification_text, notification_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, userType, picture, fname, notification_text, current_time_pht))

            conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for('profile_employer'))

    else:
        # Display user information
        cursor.execute('SELECT * FROM users WHERE User_ID = ?', (user_id,))
        user = cursor.fetchone()

        if user:
            session['user_email'] = user['email']
            session['user_contact'] = user['contactnum']
            session['user_bio'] = user['bio']
            session['user_address'] = user['address']  # Retrieve address
            return render_template('/employer/employer.html', user=user)
        else:
            cursor.close()
            conn.close()
            return "User not found", 404





@app.route('/change_password', methods=['POST'])
def change_password():
    # Access the data as JSON
    data = request.json
    old_password = data['oldpassword']           # Change to match AJAX keys
    new_password = data['newpassword']           # Change to match AJAX keys
    confirm_password = data['confirmpassword']   # Change to match AJAX keys

    print(f"Old Password: {old_password}")
    print(f"New Password: {new_password}")
    print(f"Confirm Password: {confirm_password}")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the current password from the session
    current_password = session.get('user_password')  # Ensure this is set when the user logs in

    if old_password != current_password:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'error_message': 'Old password is incorrect'})

    if new_password != confirm_password:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'error_message': 'New password and confirm password do not match'})

    # Update the password in the database
    cursor.execute('''
        UPDATE users
        SET password = ?
        WHERE User_ID = ?
    ''', (new_password, session['user_id']))

    conn.commit()
    cursor.close()
    conn.close()

    # Update the session password here if needed
    session['user_password'] = new_password

    # Redirect to the profile page or another page as needed
    return jsonify({'success': True})







@app.route('/post_job', methods=['POST'])
def post_job():
    try:
        # Get form data
        company = request.form['company']
        title = request.form['title']
        description = request.form['description']
        position = request.form['position']
        location = request.form['location']
        natureOfWork = request.form['natureOfWork']
        salary = request.form['salary']
        closingDate = request.form['closingDate']
        jobStatus = request.form['jobStatus']
        skills = request.form.getlist('skills[]')
        
        # Current time in Philippine timezone
        philippine_tz = pytz.timezone('Asia/Manila')
        current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

        # Join skills into a string
        skills_str = ','.join(skills)
    except KeyError as e:
        flash(f'Missing form field: {e}')
        return redirect(request.url)

    # Validate closing date
    try:
        closing_date = datetime.strptime(closingDate, '%Y-%m-%d %H:%M')
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD HH:MM.')
        return redirect(request.url)

    # Validate job status
    if jobStatus not in ['Available', 'Unavailable']:
        flash('Invalid job status. Please select either "Available" or "Unavailable".')
        return redirect(request.url)

    # Validate image upload
    if 'image' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['image']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['EMPLOYER_UPLOAD_FOLDER'], filename))
        image_path = f'images/employer-uploads/{filename}'

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch employer's data using the session ID
        cursor.execute('SELECT fname, profile FROM users WHERE User_ID = ?', (session['user_id'],))
        employer_data = cursor.fetchone()
        if employer_data:
            employer_fname = employer_data[0]
            employer_profile = employer_data[1] if employer_data[1] and employer_data[1].strip() else 'static/images/employer-images/avatar.png'
        else:
            employer_fname = 'Unknown'
            employer_profile = 'static/images/employer-images/avatar.png'

        # Insert job details into the jobs table, including the employer's session ID
        conn.execute(
            '''INSERT INTO jobs (title, position, description, image, location, natureOfWork, salary, Company, closingDate, jobStatus, employer_ID, request, skills, date_posted) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, position, description, image_path, location, natureOfWork, salary, company, closing_date, jobStatus, session['user_id'], "Pending", skills_str, current_time_pht)
        )

        # Fetch jobseekers' details (if needed)
        cursor.execute('SELECT User_ID FROM users WHERE userType = "Jobseeker"')
        jobseekers = cursor.fetchall()

        # Create notification text
        cursor.execute('SELECT profile, fname, userType FROM users WHERE User_ID = ?', (session['user_id'],))
        user = cursor.fetchone()

        if user:
            picture = user[0]  # profile (picture)
            fname = user[1]    # fname
            userType = user[2] # userType

            notification_text = f"{fname} is requesting permission to post about the company {company} as they are currently hiring."

            # Insert notification into `admin_notification` table with session user ID
            cursor.execute('''
                INSERT INTO admin_notification (user_id, userType, picture, fname, notification_text, notification_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], userType, picture, fname, notification_text, current_time_pht))

            print(f"Admin Notification: {notification_text}")

        conn.commit()
        conn.close()

        # Redirect based on user type
        if session.get('user_type') == 'Employer':
            return redirect(url_for('employer'))
        else:
            return redirect(url_for('jobseeker_notifications'))

    flash('Invalid file format')
    return redirect(request.url)





























@app.route('/insert_html2pdf_employer', methods=['POST'])
def insert_html2pdf_employer():
    if 'pdf' not in request.files:
        print("No file part")
        return redirect('/signin')

    file = request.files['pdf']

    if file.filename == '':
        print("No selected file")
        return redirect('/signin')

    email_input = request.form.get('email')  # Get email from the form data

    if file:
        # Secure the filename and prepare for saving
        filename = secure_filename('form-content-employer.pdf')
        file_path = os.path.join(app.config['EMPLOYER_UPLOAD_FOLDER'], filename)

        # Check if file already exists and rename if necessary
        base, extension = os.path.splitext(filename)
        counter = 1
        new_filename = filename  # Initialize new_filename

        while os.path.exists(file_path):
            new_filename = f"{base}({counter}){extension}"
            file_path = os.path.join(app.config['EMPLOYER_UPLOAD_FOLDER'], new_filename)
            counter += 1
        
        # Save the file using the unique filename
        file.save(file_path)
        print(f"PDF saved to {file_path}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the existing email from the database for comparison
        cursor.execute(''' 
            SELECT email 
            FROM users 
            WHERE email = ? 
        ''', (email_input,))
        
        existing_email = cursor.fetchone()  # Get the existing email from the database

        if existing_email:
            # Compare emails
            print(f"Input email: {email_input}")
            print(f"Email from database: {existing_email[0]}")

            if email_input == existing_email[0]:  # Check if both emails match
                # Update the `pdf_form` field in the `users` table
                cursor.execute(''' 
                    UPDATE users 
                    SET pdf_form = ? 
                    WHERE email = ?  -- Use email instead of User_ID
                ''', (new_filename, email_input))  # Insert the filename as text

                conn.commit()
                print(f"PDF filename '{new_filename}' updated in the users table for email {email_input}.")
            else:
                print("Emails do not match. PDF not updated.")
        else:
            print("Email not found in the database.")

        conn.close()

    return redirect('/signin')