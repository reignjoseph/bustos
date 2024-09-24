from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
#___________________________________
import logging
from logging import FileHandler
from main import app
import pytz
# This is the 
# Set a secret key for the session
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=3)

def get_db_connection():
    conn = sqlite3.connect('trabahanap.db')
    conn.row_factory = sqlite3.Row
    return conn











@app.route('/announcement')
def announcement():
    return render_template('/menu/announcement.html')


@app.route('/update_announcement_status', methods=['POST'])
def update_announcement_status():
    try:
        # Get current date in the Philippines timezone
        timezone = pytz.timezone('Asia/Manila')
        current_date_ph = datetime.now(timezone)

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all announcements
        cursor.execute('SELECT announcementID, "When" FROM announcement')
        announcements = cursor.fetchall()

        for row in announcements:
            announcement_id = row[0]
            when_range = row[1]

            # Ensure the when_range is valid
            if ' to ' in when_range:
                # Parse the date range
                start_date_str, end_date_str = when_range.split(' to ')
                start_date = timezone.localize(datetime.strptime(start_date_str, '%Y-%m-%d'))
                end_date = timezone.localize(datetime.strptime(end_date_str, '%Y-%m-%d')) + timedelta(days=1)  # Extend to the end of the day
            else:
                # Handle the case of a single date
                start_date = timezone.localize(datetime.strptime(when_range, '%Y-%m-%d'))
                end_date = start_date + timedelta(days=1)  # End of the same day

            # Debugging: Print current date and the start/end dates
            print(f"Current date: {current_date_ph}, Start date: {start_date}, End date: {end_date}")

            # Determine the new status
            new_status = "Available" if start_date <= current_date_ph < end_date else "Unavailable"

            # Fetch current status and print it
            cursor.execute('SELECT status FROM announcement WHERE announcementID = ?', (announcement_id,))
            current_status = cursor.fetchone()[0]
            print(f"Announcement ID: {announcement_id}, Current Status: {current_status}")

            # Check if status has changed and print
            if current_status != new_status:
                print(f"Announcement ID: {announcement_id}, Status changed from {current_status} to {new_status}")
                # Update the announcement status
                cursor.execute('UPDATE announcement SET status = ? WHERE announcementID = ?', (new_status, announcement_id))

        conn.commit()
        conn.close()

        return jsonify(success=True)

    except Exception as e:
        print(f"Error updating announcement status: {e}")
        return jsonify(success=False), 500



@app.route('/fetch_announcements', methods=['GET'])
def fetch_announcements():
    try:
        # Connect to the database
        update_announcement_status() 
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
        role = request.form['role']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Connect to the database
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()
        
        # Insert the user into the database
        cursor.execute('''
            INSERT INTO users (email, password, fname, userType, contactnum, dateRegister, AccountStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (email, password, name, role, None, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Active'))
        
        # Commit and close the connection
        conn.commit()
        cursor.close()
        conn.close()
        
        return render_template('/menu/signup.html', show_modal=True)

    return render_template('/menu/signup.html', show_modal=False)





@app.route('/')
def index():
    return render_template('/menu/index.html')

@app.route('/about')
def about_and_contact():
    return render_template('/menu/about.html')
