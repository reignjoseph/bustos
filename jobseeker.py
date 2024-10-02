# import re
from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify
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
app.permanent_session_lifetime = timedelta(minutes=3)

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
        # Secure the filename and prepare for saving
        filename = secure_filename('form-content-jobseeker.pdf')
        file_path = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], filename)
        
        # Check if file already exists and rename if necessary
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

        conn = get_db_connection()
        cursor = conn.cursor()

        
        current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

        # Insert into the `pdf` table with the unique filename
        cursor.execute('''
            INSERT INTO pdf (pdf_form)
            VALUES (?)
        ''', (new_filename,))

        conn.commit()
        conn.close()

        print(f"PDF filename '{new_filename}' inserted into the database.")

    return redirect('/signin')



















































@app.route('/retrieve_application_status', methods=['GET'])
def retrieve_application_status():
    try:
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()

        print("Database connection established.")

        # Query to get application status and related information where 'popup' is empty or null
        cursor.execute('''
            SELECT a.status_id, a.applicant_id, a.job_id, a.jobseeker_id, a.employer_id, a.status_description, 
                   a.status_type, a.company, u.profile, u.fname, a.date_posted
            FROM application_status a
            JOIN users u ON a.employer_id = u.User_ID
            WHERE a.popup IS NULL OR a.popup = ''
        ''')

        status_list = cursor.fetchall()

        # Print the retrieved data
        print(f"Fetched {len(status_list)} records from application_status.")

        for row in status_list:
            print("Record details:")
            print(f"status_id: {row[0]}")
            print(f"applicant_id: {row[1]}")
            print(f"job_id: {row[2]}")
            print(f"jobseeker_id: {row[3]}")
            print(f"employer_id: {row[4]}")
            print(f"status_description: {row[5]}")
            print(f"status_type: {row[6]}")
            print(f"company: {row[7]}")
            print(f"profile_picture: {row[8]}")
            print(f"employer_name: {row[9]}")
            print(f"date_posted: {row[10]}")

        conn.close()

        # Prepare the status data with the profile picture URL and date_posted
        results = []
        for row in status_list:
            profile_picture = row[8]
            # Dynamically generate the profile picture URL
            if profile_picture:
                profile_url = url_for('static', filename=f'images/employer-images/{profile_picture}')
            else:
                profile_url = url_for('static', filename='images/employer-images/default.jpg')

            # Add the date_posted field to the result
            results.append({
                'status_id': row[0],
                'applicant_id': row[1],
                'job_id': row[2],
                'jobseeker_id': row[3],
                'employer_id': row[4],
                'status_description': row[5],
                'status_type': row[6],
                'company': row[7],
                'profile_picture': profile_url,  # Use the dynamic profile URL
                'employer_name': row[9],
                'date_posted': row[10]  # Include the date_posted field
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
            SET popup = ?
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









@app.route('/advance_filter', methods=['GET'])
def advance_filter():
    skill_filter = request.args.get('skill_filter', 'Default')
    location_filter = request.args.get('location_filter', 'Default')
    company_filter = request.args.get('company_filter', 'Default')
    position_filter = request.args.get('position_filter', 'Default')  # Add position filter
    natureOfWork_filter = request.args.get('natureOfWork_filter', 'Default')  # Add natureOfWork filter
    job_filter = request.args.get('job_filter', 'Default')  # Add job filter

    if 'user_id' not in session:
        return jsonify({"error": "User is not logged in"}), 401  # Unauthorized response

    conn = get_db_connection()

    # First, retrieve jobs where Request is "Approved" and jobStatus is "Available"
    initial_query = "SELECT * FROM jobs WHERE LOWER(request) = 'approved' AND LOWER(jobStatus) = 'available'"
    initial_jobs = conn.execute(initial_query).fetchall()

    print("Initial Filtered Jobs (Approved & Available):", [job['Job_ID'] for job in initial_jobs])  # Debugging line

    # Skill filter logic
    if skill_filter == 'Default':
        jobseeker_id = session['user_id']
        skills_query = "SELECT skills FROM form101 WHERE jobseeker_id = ?"
        skills_result = conn.execute(skills_query, (jobseeker_id,)).fetchone()

        if skills_result:
            # Remove unwanted prefixes and standardize skills
            skills = skills_result['skills'].replace("[", "").replace("]", "").split(",")
            skills = [skill.strip().replace("Skill: ", "").lower() for skill in skills]
            print("Extracted Skills:", skills)  # Debugging line

            # Prepare the query to match jobs with any of these skills
            skill_jobs = [job for job in initial_jobs if any(skill in job['skills'].lower() for skill in skills)]
        else:
            skill_jobs = []  # No skills found, return empty result
    else:
        skill_jobs = [job for job in initial_jobs if skill_filter.lower() in job['skills'].lower()]

    print("Skill Jobs:", [job['Job_ID'] for job in skill_jobs])  # Print Job_IDs

    # Location filter logic
    if location_filter != 'Default':
        location_jobs = [job for job in skill_jobs if location_filter.lower() in job['location'].lower()]
    else:
        location_jobs = skill_jobs

    print("Location Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Company filter logic
    if company_filter != 'Default':
        company_jobs = [job for job in location_jobs if company_filter.lower() in job['company'].lower()]
        location_jobs = [job for job in location_jobs if job in company_jobs]

    print("Company Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Position filter logic
    if position_filter != 'Default':
        position_jobs = [job for job in location_jobs if position_filter.lower() in job['position'].lower()]
        location_jobs = [job for job in location_jobs if job in position_jobs]

    print("Position Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Nature of Work filter logic
    if natureOfWork_filter != 'Default':
        natureOfWork_jobs = [job for job in location_jobs if natureOfWork_filter.lower() in job['natureOfWork'].lower()]
        location_jobs = [job for job in location_jobs if job in natureOfWork_jobs]

    print("Nature of Work Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Job filter logic
    if job_filter != 'Default':
        job_jobs = [job for job in location_jobs if job_filter.lower() in job['title'].lower()]
        location_jobs = [job for job in location_jobs if job in job_jobs]

    print("Job Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    conn.close()

    # Convert jobs to a list of dictionaries including Job_ID
    job_list = [{
        "Job_ID": job['Job_ID'],  # Include Job_ID
        "employer_ID": job['employer_ID'],  # Add employer_ID to the output
        "Company": job['Company'],
        "title": job['title'],
        "position": job['position'],  # Add position to the output
        "image": job['image'],
        "location": job['location'],
        "natureOfWork": job['natureOfWork'],
        "jobStatus": job['jobStatus'],
        "closingDate": job['closingDate'],
        "skills": job['skills']
    } for job in location_jobs]

    print("Jobs Returned:", job_list)  # Debugging line

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
    if request.method == 'POST':
        # Get data from the form
        job_id = request.form['job_id']
        employer_id = request.form['employer_id']
        file = request.files['file']
        
        # Check if the file is provided
        if not file or file.filename == '':
            return "No file selected", 400
        
        # Check if the file type is allowed
        if not allowed_file(file.filename):
            return "File type not allowed", 400
        
        # Ensure a safe filename and avoid filename conflicts
        filename = secure_filename(file.filename)
        base, ext = os.path.splitext(filename)
        timestamp = int(time.time())
        filename = f"{base}_{timestamp}{ext}"
        file_path = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get user details from session
        jobseeker_id = session.get('user_id')  # Get jobseeker_id from the session
        jobseeker_name = session.get('user_fname')
        email = session.get('user_email')
        contact_no = session.get('user_contact')
        # philippine_tz = timezone(timedelta(hours=8))
        current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')        

        # Connect to the database
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()
        
        # Insert the application into the database
        cursor.execute('''
            INSERT INTO applicant (job_id, employer_id, jobseeker_id, jobseeker_name, email, contact_no, form, status,date_request)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)
        ''', (job_id, employer_id, jobseeker_id, jobseeker_name, email, contact_no, file_path, 'Pending',current_time_pht))
        


        print(f"Received data - Date Request: {current_time_pht}")
        # Commit and close the connection
        # Get jobseeker details from `users` table
        cursor.execute('SELECT profile, fname, userType FROM users WHERE User_ID = ?', (jobseeker_id,))
        user = cursor.fetchone()
        
        if user:
            picture = user[0]  # profile (picture)
            fname = user[1]    # fname
            userType = user[2] # userType
        
            # Get job details from `jobs` table to retrieve company and location
            cursor.execute('SELECT Company, location FROM jobs WHERE Job_ID = ?', (job_id,))
            job = cursor.fetchone()
            
            if job:
                company = job[0]
                location = job[1]

                # Create notification text
                notification_text = f"{fname} applied for a job at {company} located in {location}"
                
                # Insert notification into `admin_notification` table
                cursor.execute('''
                    INSERT INTO admin_notification (user_id, userType, picture, fname, notification_text, notification_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (jobseeker_id, userType, picture, fname, notification_text, current_time_pht))

                print(f"Admin Notification: {notification_text}")


        conn.commit()
        cursor.close()
        conn.close()

        return "Application submitted successfully!", 200





@app.route('/jobseeker/status')
def jobseeker_status():
    if 'user_id' in session and session['user_type'] == 'Jobseeker':
        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user data
        cursor.execute('SELECT * FROM users WHERE User_ID = ?', (user_id,))
        user_data = cursor.fetchone()

        
        # Close the cursor and connection
        cursor.close()
        conn.close()

        # Pass the notifications to the template
        return render_template('jobseeker/status.html', user_data=user_data)
    
    return redirect(url_for('signin'))




















@app.route('/jobseeker/notification')
def jobseeker_notification():
    if 'user_id' in session and session['user_type'] == 'Jobseeker':
        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user data
        cursor.execute('SELECT * FROM users WHERE User_ID = ?', (user_id,))
        user_data = cursor.fetchone()

        # Fetch notifications for the jobseeker
        cursor.execute('SELECT * FROM jobseeker_notifications WHERE employer_id IS NOT NULL')
        notifications = cursor.fetchall()

        # Generate notification texts
        notifications_with_text = []
        for notification in notifications:
            employer_id = notification['employer_id']
            
            # Fetch the employer's profile picture
            cursor.execute('SELECT profile FROM users WHERE User_ID = ?', (employer_id,))
            employer_data = cursor.fetchone()
            if employer_data and employer_data['profile']:
                profile_picture = f'/static/images/employer-images/{employer_data["profile"]}'
            else:
                profile_picture = '/static/images/employer-images/avatar.png'
            
            company = notification['company']
            job_title = notification['job_title']
            text = notification['text']
            date_created = notification['date_created']
            notifications_with_text.append({
                'employer_fname': notification['employer_fname'],
                'text': text,
                'company': company,
                'job_title': job_title,
                'date_created': date_created,
                'profile_picture': profile_picture
            })

        # Close the cursor and connection
        cursor.close()
        conn.close()

        # Pass the notifications to the template
        return render_template('jobseeker/notification.html', user_data=user_data, notifications=notifications_with_text)
    
    return redirect(url_for('signin'))



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
    update_job_statuses()
    if 'user_id' in session and session['user_type'] == 'Jobseeker':
        user_id = session['user_id']
        # Connect to the database and fetch job announcements
        conn = get_db_connection()
        cursor = conn.cursor()
        
        
        
        # Query to fetch jobs (you may need to adjust the query based on your table structure)
        cursor.execute('SELECT * FROM jobs')
        jobs = cursor.fetchall()
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE User_ID = ?', (user_id,))
        user_data = cursor.fetchone()

        

        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        # Pass the jobs to the template
        return render_template('/jobseeker/jobseeker.html', jobs=jobs, user_data=user_data)
    
    return redirect(url_for('signin'))













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
        address = request.form['address']
        phone = request.form['phone']
    except KeyError as e:
        flash(f'Missing form field: {e}')
        return redirect(request.url)

    # Get current user data from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT profile FROM users WHERE User_ID = ?", (user_id,))
    current_image_path = cursor.fetchone()[0]
    conn.close()

    # Handle the profile picture upload
    if 'profile_picture' not in request.files or request.files['profile_picture'].filename == '':
        # No file uploaded, keep the current image
        image_path = current_image_path
    else:
        file = request.files['profile_picture']
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['JOBSEEKER_UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_path = f'images/jobseeker-uploads/{filename}'
        else:
            flash('Invalid file format')
            image_path = current_image_path  # Keep the current image path if the file is invalid

    # Update the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET bio = ?, address = ?, contactnum = ?, profile = ?
        WHERE User_ID = ?
    """, (bio, address, phone, image_path, user_id))
    


    # Get jobseeker details from `users` table
    cursor.execute('SELECT profile, fname, userType FROM users WHERE User_ID = ?', (user_id,))
    user = cursor.fetchone()

    if user:
        picture = user[0]  # profile (picture)
        fname = user[1]    # fname
        userType = user[2] # userType

        # Now fetch the rating using the last inserted `rating_id`
        notification_text = f"{fname} update his profile status"

        # Insert notification into `admin_notification` table
        cursor.execute('''
            INSERT INTO admin_notification (user_id, userType, picture, fname, notification_text, notification_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, userType, picture, fname, notification_text, current_time_pht))

        print(f"Admin Notification: {notification_text}")


    conn.commit()
    conn.close()
    
    # Redirect to the jobseeker page after updating the profile
    return redirect(url_for('jobseeker'))





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


