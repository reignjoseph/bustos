from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
#___________________________________
import logging
from logging import FileHandler
from main import app
import random

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
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


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
    old_password = request.form['oldpassword']
    new_password = request.form['newpassword']
    confirm_password = request.form['confirmpassword']

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
    return jsonify({'success': True, 'redirect': url_for('employer')})








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
            'INSERT INTO jobs (title, position, description, image, location, natureOfWork, salary, Company, closingDate, jobStatus, employer_ID,request,skills) VALUES (?,?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (title, position, description, image_path, location, natureOfWork, salary, company, closing_date, jobStatus, session['user_id'],"Pending",skills_str)
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