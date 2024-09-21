from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
#___________________________________
import logging
from logging import FileHandler
from main import app
# This is the 
# Set a secret key for the session
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=3)













@app.route('/announcement')
def announcement():
    # conn = get_db_connection()
    # jobs = conn.execute('SELECT * FROM jobs').fetchall()
    # conn.close()
    # return render_template('/menu/announcement.html', jobs=jobs)
    return render_template('/menu/announcement.html')

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
