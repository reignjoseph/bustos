from flask import Flask, request, redirect, url_for, render_template, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import random
#___________________________________
import logging
from logging import FileHandler
from main import app


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

app.config['UPLOAD_FOLDER'] = 'static/images/jobseeker-uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# This is the jobseeker
def get_db_connection():
    conn = sqlite3.connect('trabahanap.db')
    conn.row_factory = sqlite3.Row
    return conn





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
            company = notification['company']
            job_title = notification['job_title']
            text = notification['text']
            date_created= notification['date_created']
            notifications_with_text.append({
                'employer_fname': notification['employer_fname'],
                'text': text,
                'company': company,
                'job_title': job_title,
                'date_created': date_created
                
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


@app.route('/update_profile', methods=['POST'])
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
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
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
        SET bio = ?, address = ?, contactnum = ?, profile = ?, AccountStatus = 'Active'
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
    created = datetime.now().strftime('%d/%m/%Y')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rating (star, comments, User_ID, created) VALUES (?, ?, ?, ?)",
                   (star, comments, user_id, created))
    conn.commit()
    conn.close()
    
    return redirect(url_for('jobseeker'))


