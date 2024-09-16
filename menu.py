from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
#___________________________________
import logging
from logging import FileHandler
from main import app
# This is the menu
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
        
        cursor.execute('''
            SELECT * 
            FROM users WHERE email = ?
        ''', (email,))
        user = cursor.fetchone()

        if user:
            if user[2] != password:  # Check password
                cursor.close()
                conn.close()
                return render_template('/menu/signin.html', error_message='Invalid password.')

            if user[7] == 'Pending':
                cursor.close()
                conn.close()
                return render_template('/menu/signin.html', error_message='Your account is pending approval.')
            
            # Clear existing session data
            session.clear()
            
            # Set new session data
            session['user_id'] = user[0]          # User ID
            session['user_email'] = user[1]       # User Email
            session['user_password'] = user[2]    # User Password
            session['user_fname'] = user[3]       # User First Name (fname)
            session['user_type'] = user[4]        # User Type
            session['user_contact'] = user[5]     # User Contact Number
            session['user_profile'] = user[6]     # User Profile Image
            session['user_status'] = user[7]      # User Status
            session['user_dateRegister'] = user[8]# User Registration Date
            session['user_bio'] = user[9]         # User Bio
            session['user_address'] = user[10]    # User Address

            print(user[0])  # User ID
            print(user[1])  # User Email
            print(user[2])  # User Password
            print(user[3])  # User First Name (fname)
            print(user[4])  # User Type
            print(user[5])  # User Contact Number
            print(user[6])  # User Profile Image
            print(user[7])  # User Status
            print(user[8])  # User Registration Date
            print(user[9]) # User Bio
            print(user[10]) # User Address

            cursor.close()
            conn.close()
            
            if user[4] == 'Jobseeker':
                return redirect(url_for('jobseeker'))
            elif user[4] == 'Employer':
                return redirect(url_for('employer'))
            elif user[4] == 'Admin':
                return redirect(url_for('admin'))
            else:
                return render_template('/menu/signin.html', error_message='Invalid user type.')
        else:
            cursor.close()
            conn.close()
            return render_template('/menu/signin.html', error_message='Not registered email.')
    
    return render_template('/menu/signin.html')



@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from the session
    session.pop('user_type', None)  # Remove user_type from the session
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
