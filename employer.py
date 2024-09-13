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
    # Check if user is authenticated
    if 'user_id' not in session or session.get('user_type') != 'Employer':
        return redirect(url_for('signin'))
    
    return render_template('employer/employer.html')




















@app.route('/get_notes', methods=['GET'])
def get_notes():
    date = request.args.get('date')
    conn = get_db_connection()
    cursor = conn.execute('SELECT note FROM calendar WHERE date = ?', (date,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({'note': row['note']})
    else:
        return jsonify({'note': ''})

# Insert or update a note for a specific date
@app.route('/save_note', methods=['POST'])
def save_note():
    data = request.get_json()
    date = data['date']
    note = data['note']
    
    conn = get_db_connection()
    # Insert or update the note
    conn.execute('INSERT OR REPLACE INTO calendar (date, note) VALUES (?, ?)', (date, note))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

















































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

    # Fetch the company associated with the applicant from application_status table
    cursor.execute("SELECT company FROM application_status WHERE applicant_id = ?", (applicant_id,))
    result = cursor.fetchone()

    if result:
        company = result[0]  # Extract the company name from the result

        # Update the schedule in the application_status table
        cursor.execute("""
            UPDATE application_status 
            SET scheduled = ?, status_type = 'Scheduled', status_description = ?, date_posted = ? 
            WHERE applicant_id = ?
        """, (
            new_schedule, 
            f"Your application at {company} is scheduled at {new_schedule}",
            current_time_pht,
            applicant_id
        ))

        # Now also update the schedule in the applicant table where Applicant_ID matches
        cursor.execute("""
            UPDATE applicant 
            SET schedule = ?
            WHERE Applicant_ID = ?
        """, (new_schedule, applicant_id))
    
    # Commit the changes to both tables and close the connection
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})


























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


@app.route('/update_interview_result', methods=['POST'])
def update_interview_result():
    applicant_id = request.form['id']
    result = request.form['result']

    # Get current time in Philippine Time (UTC+8)
    philippine_tz = pytz.timezone('Asia/Manila')
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Establish a connection to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch job details from the applicant and jobs tables
        cursor.execute('''
            SELECT a.job_id, j.company, j.position
            FROM applicant a
            JOIN jobs j ON a.job_id = j.Job_ID
            WHERE a.Applicant_ID = ?
        ''', (applicant_id,))
        job_details = cursor.fetchone()

        if job_details is None:
            print(f"Error: Job details not found for applicant ID {applicant_id}")
            return jsonify({'status': 'error', 'message': 'Job details not found'}), 404

        job_id, company, position = job_details
        print(f"Fetched job details: job_id={job_id}, company={company}, position={position}")

        # Determine the status_type based on the result
        if result == "Passed":
            status_type = "Passed"
            status_descriptions = [
                f"Congratulations! You are now hired!",
                f"You are now hired at {company} as a {position}."
            ]
        elif result == "Failed":
            status_type = "Failed"
            status_descriptions = [
                f"Your interview did not meet our expectations.",
                f"Unfortunately, you were not selected for the position at {company}. Please feel free to apply for other opportunities."
            ]
        else:
            status_type = result  # Use the result as status_type if it's neither Passed nor Failed
            status_descriptions = [
                f"Your interview status is {result}."
            ]

        # Choose a random status description
        status_description = random.choice(status_descriptions)
        print(f"Generated status description: {status_description}")

        # Update the result, status_type, status_description, and date_posted in the application_status table
        cursor.execute('''
            UPDATE application_status
            SET status_type = ?, date_posted = ?, result = ?, status_description = ?
            WHERE applicant_id = ?
        ''', (status_type, current_time_pht, result, status_description, applicant_id))

        # Commit the changes
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        # Close the connection
        conn.close()

    return jsonify({'status': 'success'})

@app.route('/fetch_interview_result', methods=['POST'])
def fetch_interview_result():
    applicant_id = request.form['id']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT result
            FROM application_status
            WHERE applicant_id = ?
        """, (applicant_id,))
        
        result = cursor.fetchone()

        return jsonify({'result': result[0] if result else None})
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
    cursor.execute('''
        SELECT scheduled FROM application_status WHERE applicant_id = ?
    ''', (applicant_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        scheduled_time_str = result[0]
        try:
            # Print the scheduled time string and current time
            # print(f"Scheduled Time String: {scheduled_time_str}")
            # print(f"Current Time PHT: {current_time_pht}")

            # Parse the scheduled time
            if len(scheduled_time_str) == 16:  # Format 'YYYY-MM-DD HH:MM'
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M')
                scheduled_time = philippine_tz.localize(scheduled_time)  # Localize to Philippine Time
            elif len(scheduled_time_str) == 19:  # Format 'YYYY-MM-DD HH:MM:SS'
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
                scheduled_time = philippine_tz.localize(scheduled_time)  # Localize to Philippine Time
            else:
                raise ValueError("Unexpected date format")

            # Print the parsed scheduled time
            # print(f"Parsed Scheduled Time: {scheduled_time}")

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
        return jsonify({'status': 'hide'})
    applicant_id = request.form['id']
    
    # Establish a connection to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the current time in Philippine Time (UTC+8)
    philippine_tz = pytz.timezone('Asia/Manila')
    current_time_pht = datetime.now(philippine_tz)
    
    # Fetch the scheduled time for the applicant
    cursor.execute('''
        SELECT scheduled FROM application_status WHERE applicant_id = ?
    ''', (applicant_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        scheduled_time_str = result[0]
        try:
            # Print the scheduled time string and current time
            print(f"Scheduled Time String: {scheduled_time_str}")
            print(f"Current Time PHT: {current_time_pht}")

            # Parse the scheduled time
            if len(scheduled_time_str) == 16:  # Format 'YYYY-MM-DD HH:MM'
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M')
                scheduled_time = philippine_tz.localize(scheduled_time)  # Localize to Philippine Time
            elif len(scheduled_time_str) == 19:  # Format 'YYYY-MM-DD HH:MM:SS'
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
                scheduled_time = philippine_tz.localize(scheduled_time)  # Localize to Philippine Time
            else:
                raise ValueError("Unexpected date format")

            # Print the parsed scheduled time
            print(f"Parsed Scheduled Time: {scheduled_time}")

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
        return jsonify({'status': 'hide'})































@app.route('/fetch_approved_applicants', methods=['GET'])
def fetch_approved_applicants():
    try:
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()

        # Fetch applicants with "Pending" status and their corresponding company from the jobs table
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
                jobs.Company, -- Assuming "Company" is a field in the jobs table
                users.profile,
                application_status.interviewed -- Add this line to fetch the interviewed status
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
                applicant.status = ?
        ''', ('Approved',))

        applicants = cursor.fetchall()
        # print("Fetched applicants with Approve status and Company from DB:", applicants)  # Debug the SQL response

        conn.close()

        approved_applicant_list = []
        for row in applicants:
            # print(f"Processing row: {row}")  # Debug each row as it's processed
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
                'Company': row[11],  # Add the company information
                'profile': row[12],
                'interviewed': row[13]  # Add the interviewed information
            })

        return jsonify(approved_applicant_list)

    except Exception as e:
        print(f"Error fetching applicants: {e}")
        return jsonify({'error': 'An error occurred while fetching applicants'}), 500






















@app.route('/fetch_applicants', methods=['GET'])
def fetch_applicants():
    try:
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()

        # Fetch applicants with "Pending" status and their corresponding company from the jobs table
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
                jobs.Company, -- Assuming "Company" is a field in the jobs table
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
                applicant.status = ?
        ''', ('Pending',))

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

    except Exception as e:
        print(f"Error fetching applicants: {e}")
        return jsonify({'error': 'An error occurred while fetching applicants'}), 500


@app.route('/update_applicant_status', methods=['POST'])
def update_applicant_status():
    try:
        data = request.get_json()
        applicant_id = data.get('applicant_id')
        status = data.get('status')

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

        # Get current time in Philippine time (UTC+8)
        philippine_tz = timezone(timedelta(hours=8))
        current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Current Philippine time: {current_time_pht}")

        # Update the applicant's status in the applicant table
        cursor.execute('''
            UPDATE applicant
            SET status = ?
            WHERE Applicant_ID = ?
        ''', (status, applicant_id))

        print(f"Updated applicant ID {applicant_id} status to {status}")

        # Insert into the application_status table
        cursor.execute('''
            INSERT INTO application_status (applicant_id, job_id, jobseeker_id, employer_id, status_description, status_type, company, date_posted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (applicant_id, job_id, jobseeker_id, employer_id, status_description, status, company, current_time_pht))

        print(f"Inserted into application_status: applicant_id={applicant_id}, job_id={job_id}, jobseeker_id={jobseeker_id}, employer_id={employer_id}, status_type={status}, company={company}, date_posted={current_time_pht}")

        # Commit the transaction and close the connection
        conn.commit()
        conn.close()

        return jsonify({'message': 'Status updated successfully and inserted into application_status!'})

    except Exception as e:
        print(f"Error updating applicant status: {e}")
        return jsonify({'error': 'An error occurred while updating applicant status'}), 500




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

    # Update the profile picture path in the database
    cursor.execute('UPDATE users SET profile = ? WHERE User_ID = ?', (filename, user_id))
    conn.commit()
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
        email = request.form['email']
        contact = request.form['contact']
        bio = request.form['bio']

        cursor.execute('''
            UPDATE users
            SET contactnum = ?, bio = ?
            WHERE User_ID = ?
        ''', (contact, bio, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('profile_employer'))

    else:
        # Display user information
        cursor.execute('''
            SELECT * FROM users WHERE User_ID = ?
        ''', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_email'] = user['email']
            session['user_contact'] = user['contactnum']
            session['user_bio'] = user['bio']
            return render_template('/employer/employer.html', user=user)
        else:
            return "User not found", 404

@app.route('/change_password', methods=['POST'])
def change_password():
    print("Received data:", request.form)
    old_password = request.form['oldpassword']
    new_password = request.form['newpassword']
    confirm_password = request.form['confirmpassword']
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
        philippine_tz = timezone(timedelta(hours=8))
        current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')


        skills_str = ','.join(skills)
    except KeyError as e:
        flash(f'Missing form field: {e}')
        return redirect(request.url)

    try:
        closing_date = datetime.strptime(closingDate, '%Y-%m-%d %H:%M')
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD HH:MM.')
        return redirect(request.url)

    if jobStatus not in ['Available', 'Unavailable']:
        flash('Invalid job status. Please select either "Available" or "Unavailable".')
        return redirect(request.url)

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

        # Fetch the employer's name and profile picture
        cursor.execute('SELECT fname, profile FROM users WHERE User_ID = ?', (session['user_id'],))
        employer_data = cursor.fetchone()
        if employer_data:
            employer_fname = employer_data[0]
            # Use default profile image if profile field is empty
            employer_profile = employer_data[1] if employer_data[1] else 'static/images/employer-images/avatar.png'
        else:
            employer_fname = 'Unknown'
            employer_profile = 'static/images/employer-images/avatar.png'

        # Insert job details into jobs table including employer_ID
        conn.execute(
            'INSERT INTO jobs (title, position, description, image, location, natureOfWork, salary, Company, closingDate, jobStatus, employer_ID,request,skills,date_posted) VALUES (?,?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)',
            (title, position, description, image_path, location, natureOfWork, salary, company, closing_date, jobStatus, session['user_id'],"Pending",skills_str,current_time_pht)
        )

        # Fetch jobseekers' details
        cursor.execute('SELECT User_ID FROM users WHERE userType = "Jobseeker"')
        jobseekers = cursor.fetchall()

        # Get current time in Philippine Time (PHT)
        philippine_tz = timezone(timedelta(hours=8))
        current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

        # Generate notification text
        notification_text = generate_notification_text(company, title)
        
        # Create notifications for each jobseeker
        for jobseeker in jobseekers:
            user_id = jobseeker[0]
            conn.execute(
                'INSERT INTO jobseeker_notifications (employer_id, text, company, job_title, employer_fname, employer_profile, date_created) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (session['user_id'], notification_text, company, title, employer_fname, employer_profile, current_time_pht)
            )

        conn.commit()
        conn.close()

        # Redirect to a different page depending on the user type
        if session.get('user_type') == 'Employer':
            return redirect(url_for('employer'))
        else:
            return redirect(url_for('jobseeker_notifications'))

    flash('Invalid file format')
    return redirect(request.url)



def generate_notification_text(company, job_title):
    # Define consistent and varied structures
    structures = [
        f"Amazing Opportunity for {company} at {job_title}",
        f"{company} is offering an exciting opportunity for a {job_title}",
        f"{company} offers exciting opportunities at {job_title}",
        f"Exciting opportunity for {job_title} at {company}",
        f"New {job_title} position available at {company}",
        f"Don't miss out on the {job_title} role at {company}",
        f"Join {company} as a {job_title} and be part of something big",
        f"{company} is looking for a talented {job_title}",
        f"Great opening for a {job_title} at {company}",
        f"Explore the {job_title} position at {company} today"
    ]

    # Ensure adjectives and opportunities are correctly used
    adjectives = ["amazing", "exciting", "great", "unique"]
    opportunities = ["opportunity", "vacancy", "position", "opening"]

    # Templates with corrected adjective usage
    template1 = f"{random.choice(adjectives).capitalize()} {random.choice(opportunities)} at {company} as a {job_title}"
    template2 = f"{company} has a {random.choice(adjectives)} {random.choice(opportunities)} for a {job_title}"
    template3 = f"Apply now for a {job_title} role at {company} – an {random.choice(adjectives)} {random.choice(opportunities)}"
    template4 = f"{company} is offering a {random.choice(adjectives)} {random.choice(opportunities)} for the role of {job_title}"
    template5 = f"Looking for a {job_title}? Check out the {random.choice(adjectives)} {random.choice(opportunities)} at {company}"
    template6 = f"Exciting {job_title} role available at {company} – {random.choice(adjectives).capitalize()} {random.choice(opportunities)}"
    template7 = f"{company} has a fantastic {random.choice(adjectives)} {random.choice(opportunities)} for {job_title}"
    template8 = f"Apply for the {job_title} position at {company} – an {random.choice(adjectives)} {random.choice(opportunities)} awaits"
    template9 = f"{company} is looking for a {job_title} – discover the {random.choice(adjectives)} {random.choice(opportunities)} available"
    template10 = f"Join {company} as a {job_title} and seize this {random.choice(adjectives)} {random.choice(opportunities)}"

    templates = structures + [template1, template2, template3, template4, template5, template6, template7, template8, template9, template10]

    # Randomly select a template but keep it consistent for this combination
    notification_text = random.choice(templates)

    return notification_text