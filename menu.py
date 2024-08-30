from flask import Flask, request, redirect, url_for, render_template, flash, session
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
            SELECT User_ID, email, password, fname, userType, contactnum, bio, profile 
            FROM users WHERE email = ? AND password = ?
        ''', (email, password))
        user = cursor.fetchone()

        if user:
            # Clear existing session data
            session.clear()
            
            # Set new session data
            session['user_id'] = user[0]          # User ID
            session['user_email'] = user[1]       # User Email
            session['user_password'] = user[2]    # User Password (added this line)
            session['user_fname'] = user[3]       # User First Name (fname)
            session['user_contact'] = user[5]     # User Contact Number
            session['user_bio'] = user[6]         # User Bio
            session['user_profile'] = user[7]     # User Profile Image
            session['user_type'] = user[4]        # User Type
            
            # Debug prints
            print(f"Signed in user ID: {session['user_id']}")
            print(f"Signed in user type: {session['user_type']}")
            print(f"Signed in user first name: {session.get('user_fname')}")
            print(f"Signed in user contact: {session.get('user_contact')}")
            print(f"Signed in user bio: {session.get('user_bio')}")
            print(f"Signed in user password: {session.get('user_password')}")  # Debug print

            cursor.close()
            conn.close()
            
            if user[4] == 'Jobseeker':
                return redirect(url_for('jobseeker'))
            elif user[4] == 'Employer':
                return redirect(url_for('employer'))
            else:
                return "Invalid user type", 401
        else:
            cursor.close()
            conn.close()
            return "Invalid credentials", 401

    return render_template('/menu/signin.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from the session
    session.pop('user_type', None)  # Remove user_type from the session
    return redirect(url_for('signin'))
    
@app.route('/signup')
def signup():
    return render_template('/menu/signup.html')






@app.route('/')
def index():
    return render_template('/menu/index.html')

@app.route('/about')
def about_and_contact():
    return render_template('/menu/about.html')
