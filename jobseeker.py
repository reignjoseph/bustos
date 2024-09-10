import re
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
import pdfkit   # Import the pdfkit library


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




@app.route('/retrieve_application_status', methods=['GET'])
def retrieve_application_status():
    try:
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()

        # Query to get application status and related information including date_posted
        cursor.execute('''
            SELECT a.status_id, a.applicant_id, a.job_id, a.jobseeker_id, a.employer_id, a.status_description, 
                   a.status_type, a.company, u.profile, u.fname, a.date_posted
            FROM application_status a
            JOIN users u ON a.employer_id = u.User_ID
        ''')

        status_list = cursor.fetchall()
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
            skill_query = "SELECT * FROM jobs WHERE " + " OR ".join(["LOWER(skills) LIKE ?"] * len(skills))
            skill_params = [f"%{skill}%" for skill in skills]

            print("Skill Query Parameters:", skill_params)  # Debugging line

            skill_jobs = conn.execute(skill_query, skill_params).fetchall()
        else:
            skill_jobs = []  # No skills found, return empty result
    else:
        skill_query = "SELECT * FROM jobs WHERE LOWER(skills) LIKE ?"
        skill_jobs = conn.execute(skill_query, (f'%{skill_filter.lower()}%',)).fetchall()

    print("Skill Jobs:", [job['Job_ID'] for job in skill_jobs])  # Print Job_IDs

    # Location filter logic
    if location_filter == 'Default':
        location_jobs = skill_jobs
    else:
        location_query = "SELECT * FROM jobs WHERE LOWER(location) LIKE ?"
        location_jobs = conn.execute(location_query, (f'%{location_filter.lower()}%',)).fetchall()

        # Intersection of location filtered jobs with skill filtered jobs
        location_jobs = [job for job in skill_jobs if job in location_jobs]

    print("Location Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Company filter logic
    if company_filter != 'Default':
        company_query = "SELECT * FROM jobs WHERE LOWER(company) LIKE ?"
        company_jobs = conn.execute(company_query, (f'%{company_filter.lower()}%',)).fetchall()

        # Intersection of company filtered jobs with location and skill filtered jobs
        location_jobs = [job for job in location_jobs if job in company_jobs]

    print("Company Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Position filter logic
    if position_filter != 'Default':
        position_query = "SELECT * FROM jobs WHERE LOWER(position) LIKE ?"
        position_jobs = conn.execute(position_query, (f'%{position_filter.lower()}%',)).fetchall()

        # Intersection of position filtered jobs with company, location, and skill filtered jobs
        location_jobs = [job for job in location_jobs if job in position_jobs]

    print("Position Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Nature of Work filter logic
    if natureOfWork_filter != 'Default':
        natureOfWork_query = "SELECT * FROM jobs WHERE LOWER(natureOfWork) LIKE ?"
        natureOfWork_jobs = conn.execute(natureOfWork_query, (f'%{natureOfWork_filter.lower()}%',)).fetchall()

        # Intersection of natureOfWork filtered jobs with company, location, skill, and position filtered jobs
        location_jobs = [job for job in location_jobs if job in natureOfWork_jobs]

    print("Nature of Work Jobs:", [job['Job_ID'] for job in location_jobs])  # Print Job_IDs

    # Job filter logic
    if job_filter != 'Default':
        job_query = "SELECT * FROM jobs WHERE LOWER(title) LIKE ?"
        job_jobs = conn.execute(job_query, (f'%{job_filter.lower()}%',)).fetchall()

        # Intersection of job filtered jobs with company, location, skill, position, and natureOfWork filtered jobs
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
    philippine_tz = timezone(timedelta(hours=8))
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')
    
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
    conn.commit()
    conn.close()

    print(f"Received data - Role: {role}, Name: {name}, Email: {email}, Password: {password}, User_ID: {user_id}")
    print(f"Received data - Strand: {senior_strand}")
    print(f"Received data - COURSE: {course}")
    print(f"Received data - Skills: {formatted_skills}")

    # print(f"Received data - User_ID: {user_id}, Surname: {surname}, Firstname: {firstname}, Middlename: {middlename}, Suffix: {suffix}, Birthdate: {birthdate}, Sex: {sex}, Address: {address}, Barangay: {barangay}, Municipality: {municipality}, Province: {province}, Religion: {religion}, Civil Status: {civilstatus}, TIN: {tin}, Height: {height}, Disability: {', '.join(disability)}, Contact No: {contact_no}, Email Address: {emailaddress}, Employment Status: {employment_status}, OFW: {ofw}, Specify Country: {specify_country}, Former OFW: {former_ofw}, Latest Country: {latest_country}, Return Date: {return_date}, 4Ps: {four_ps}, Household ID: {household_id}")

    return redirect('/signin')


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
        philippine_tz = timezone(timedelta(hours=8))
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
    philippine_tz = timezone(timedelta(hours=8))
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Print current time in PHT for debugging purposes
    print(f"Current Time (PHP): {current_time_pht}")

    try:
        conn.execute("""
            UPDATE jobs 
            SET jobStatus = 'Unavailable'
            WHERE closingDate <= ?
        """, (current_time_pht,))
        conn.commit()
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
    philippine_tz = timezone(timedelta(hours=8))
    current_time_pht = datetime.now(philippine_tz).strftime('%Y-%m-%d %H:%M:%S')


    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rating (star, comments, User_ID, date_created) VALUES (?, ?, ?, ?)",
                   (star, comments, user_id, current_time_pht))
    conn.commit()
    conn.close()
    
    return redirect(url_for('jobseeker'))


