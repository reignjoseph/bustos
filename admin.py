import re
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
app.permanent_session_lifetime = timedelta(minutes=3)


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

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or session.get('user_type') != 'Admin':
        return redirect(url_for('signin'))

    # Set session start time if it doesn't exist
    if 'session_start' not in session:
        session['session_start'] = datetime.now(timezone)  # Make this aware

    # Check for session timeout (e.g., 3 minutes)
    session_start = session['session_start']
    if datetime.now(timezone) - session_start > timedelta(minutes=3):
        # Update currentState to Inactive
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE users SET currentState = 'Inactive' WHERE User_ID = ?''', (session['user_id'],))
        conn.commit()
        cursor.close()
        conn.close()

        # Clear session data
        session.clear()
        return redirect(url_for('signin'))

    return render_template('admin/admin.html')



@app.route('/insert_announcement', methods=['POST'])
def insert_announcement():
    try:
        # Get the form data
        image = request.files['image']
        what = request.form['what']
        when = request.form['when']
        where = request.form['location']
        requirement = request.form['requirement']
        description = request.form['description']

        # Save image to the static folder
        image_path = ''
        if image:
            image_path = f'static/images/admin-uploads/{image.filename}'
            image.save(image_path)

        # Insert data into the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Escape the SQL keywords with double quotes
        cursor.execute('''
            INSERT INTO announcement ("image", "What", "When", "Where", "Requirement", "Description")
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (image_path, what, when, where, requirement, description))

        conn.commit()
        conn.close()

        return jsonify(success=True)

    except Exception as e:
        print(f"Error inserting announcement: {e}")
        return jsonify(success=False), 500






















































@app.route('/admin_fetched_jobs', methods=['GET'])
def admin_fetched_jobs():
    job_id = request.args.get('job_id', '')
    title = request.args.get('title', '')
    position = request.args.get('position', '')
    location = request.args.get('location', '')
    skills = request.args.get('skills', '')
    request_filter = request.args.get('request', '')
    date_range = request.args.get('date_range', '').split(' to ')
    page = int(request.args.get('page', 1))  # Get the current page, default is 1
    items_per_page = 4  # We limit the jobs to 4 per page

    conn = get_db_connection()

    # Base query
    query = "SELECT * FROM jobs WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM jobs WHERE 1=1"
    params = []

    # Add filters to the query
    if job_id:
        query += " AND Job_ID LIKE ?"
        count_query += " AND Job_ID LIKE ?"
        params.append(f'%{job_id}%')
    if title:
        query += " AND title LIKE ?"
        count_query += " AND title LIKE ?"
        params.append(f'%{title}%')
    if position:
        query += " AND position LIKE ?"
        count_query += " AND position LIKE ?"
        params.append(f'%{position}%')
    if location:
        query += " AND location LIKE ?"
        count_query += " AND location LIKE ?"
        params.append(f'%{location}%')
    if skills:
        query += " AND skills LIKE ?"
        count_query += " AND skills LIKE ?"
        params.append(f'%{skills}%')
    if request_filter and request_filter != 'All':
        query += " AND request = ?"
        count_query += " AND request = ?"
        params.append(request_filter)
    if len(date_range) == 2:
        query += " AND date_posted BETWEEN ? AND ?"
        count_query += " AND date_posted BETWEEN ? AND ?"
        params.append(date_range[0])
        params.append(date_range[1])

    # Pagination Logic: Add LIMIT and OFFSET to the query
    offset = (page - 1) * items_per_page
    query += " LIMIT ? OFFSET ?"
    params.append(items_per_page)
    params.append(offset)

    # Fetch jobs and total job count
    jobs = conn.execute(query, params).fetchall()
    total_jobs = conn.execute(count_query, params[:-2]).fetchone()[0]  # Get total job count

    conn.close()

    # Calculate total pages
    total_pages = (total_jobs + items_per_page - 1) // items_per_page

    # Convert jobs to a list of dictionaries
    jobs_list = [{
        'Job_ID': job['Job_ID'],
        'title': job['title'],
        'position': job['position'],
        'description': job['description'],
        'location': job['location'],
        'request': job['request'],
        'skills': job['skills'],
        'date_posted': job['date_posted']
    } for job in jobs]

    return jsonify({
        'jobs': jobs_list,
        'total_pages': total_pages,
        'current_page': page
    })





@app.route('/admin_fetched_jobs/approve/<int:job_id>', methods=['POST'])
def approve_job(job_id):
    conn = get_db_connection()
    conn.execute("UPDATE jobs SET request = 'Approved' WHERE Job_ID = ?", (job_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job approved successfully'})

@app.route('/admin_fetched_jobs/deny/<int:job_id>', methods=['POST'])
def deny_job(job_id):
    conn = get_db_connection()
    conn.execute("UPDATE jobs SET request = 'Denied' WHERE Job_ID = ?", (job_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job denied successfully'})





































































@app.route('/fetch_all_users', methods=['GET'])
def fetch_all_users():
    user_id = request.args.get('user_id', '')
    fname = request.args.get('fname', '')
    email = request.args.get('email', '')
    userType = request.args.get('userType', '')
    status = request.args.get('status', '')
    date = request.args.get('date', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT u.User_ID, u.email, u.fname, u.userType, u.status, u.dateRegister, p.pdf_form
        FROM users u
        LEFT JOIN pdf p ON u.User_ID = p.User_ID
        WHERE 1=1
    """
    
    filters = []
    if user_id:
        query += " AND u.User_ID = ?"
        filters.append(user_id)
    if fname:
        query += " AND u.fname LIKE ?"
        filters.append(f"%{fname}%")
    if email:
        query += " AND u.email LIKE ?"
        filters.append(f"%{email}%")
    if userType:
        query += " AND u.userType = ?"
        filters.append(userType)
    if status:
        query += " AND u.status = ?"
        filters.append(status)
    if date:
        start_date, end_date = date.split(' to ')
        query += " AND date(u.dateRegister) BETWEEN ? AND ?"
        filters.extend([start_date, end_date])

    users = cursor.execute(query, filters).fetchall()
    conn.close()

    users_list = [
        {
            "User_ID": row["User_ID"],
            "email": row["email"],
            "fname": row["fname"],
            "userType": row["userType"],
            "status": row["status"],
            "dateRegister": row["dateRegister"],
            "pdf_form": row["pdf_form"]  # Add PDF information to the response
        }
        for row in users
    ]

    return jsonify({"users": users_list})


@app.route('/update_user_status', methods=['POST'])
def update_user_status():
    data = request.json
    user_id = data['userId']
    status = data['status']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE User_ID = ?", (status, user_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})



@app.route('/fetch_all_jobseekers', methods=['GET'])
def fetch_all_jobseekers():
    # Get query parameters for pagination and filtering
    page = int(request.args.get('page', 1))
    items_per_page = 7
    offset = (page - 1) * items_per_page

    user_id = request.args.get('user_id', '')
    fname = request.args.get('fname', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Base SQL query to fetch jobseekers
    query = """
        SELECT User_ID, email, fname, contactnum, address,currentState, dateRegister
        FROM users
        WHERE userType = 'Jobseeker'
    """
    
    # Filtering by User_ID, fname, and date range if provided
    filters = []
    if user_id:
        query += " AND User_ID = ?"
        filters.append(user_id)
    if fname:
        query += " AND fname LIKE ?"
        filters.append(f"%{fname}%")
    if date_from and date_to:
        query += " AND date(dateRegister) BETWEEN ? AND ?"
        filters.extend([date_from, date_to])
    elif date_from:
        query += " AND date(dateRegister) >= ?"
        filters.append(date_from)
    elif date_to:
        query += " AND date(dateRegister) <= ?"
        filters.append(date_to)

    # Add pagination
    query += " LIMIT ? OFFSET ?"
    filters.extend([items_per_page, offset])

    # Execute query
    cursor.execute(query, filters)
    jobseekers = cursor.fetchall()
    conn.close()

    # Format data as a list of dictionaries to return as JSON
    jobseekers_list = [
        {
            "User_ID": row["User_ID"],
            "email": row["email"],
            "fname": row["fname"],
            "contactnum": row["contactnum"] if row["contactnum"] is not None else "",
            "address": row["address"] if row["address"] is not None else "",
            "currentState": row["currentState"],
            "dateRegister": row["dateRegister"]
        }
        for row in jobseekers
    ]

    # Return the jobseekers data as JSON
    return jsonify({"jobseekers": jobseekers_list})





@app.route('/fetch_all_employers', methods=['GET'])
def fetch_all_employers():
    # Get query parameters for pagination and filtering
    page = int(request.args.get('page', 1))
    items_per_page = 7
    offset = (page - 1) * items_per_page

    user_id = request.args.get('user_id', '')
    fname = request.args.get('fname', '')
    startDate = request.args.get('startDate', '')
    endDate = request.args.get('endDate', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Base SQL query to fetch employers
    query = """
        SELECT User_ID, email, fname, contactnum, address, currentState, dateRegister
        FROM users
        WHERE userType = 'Employer'
    """
    
    # Filtering by User_ID, fname, and date range if provided
    filters = []
    if user_id:
        query += " AND User_ID = ?"
        filters.append(user_id)
    if fname:
        query += " AND fname LIKE ?"
        filters.append(f"%{fname}%")
    if startDate and endDate:
        query += " AND dateRegister BETWEEN ? AND ?"
        filters.extend([startDate, endDate])

    # Add pagination
    query += " LIMIT ? OFFSET ?"
    filters.extend([items_per_page, offset])

    # Execute query
    cursor.execute(query, filters)
    employers = cursor.fetchall()
    conn.close()

    # Format data as a list of dictionaries to return as JSON
    employers_list = [
        {
            "User_ID": row["User_ID"],
            "email": row["email"],
            "fname": row["fname"],
            "contactnum": row["contactnum"] if row["contactnum"] is not None else "",
            "address": row["address"] if row["address"] is not None else "",
            "currentState": row["currentState"] if row["currentState"] is not None else "",
            "dateRegister": row["dateRegister"]
        }
        for row in employers
    ]

    # Return the employers data as JSON
    return jsonify({"employers": employers_list})



@app.route('/fetch_all_ratings', methods=['GET'])
def fetch_all_ratings():
    try:
        page = int(request.args.get('page', 1))
        user_id_filter = request.args.get('user_id', None)
        star_filter = request.args.get('star', None)
        start_date_filter = request.args.get('startDate', None)
        end_date_filter = request.args.get('endDate', None)

        query = "SELECT RatingID, star, comments, User_ID, date_created FROM rating WHERE 1=1"
        params = []

        if user_id_filter:
            query += " AND User_ID = ?"
            params.append(user_id_filter)
        if star_filter:
            query += " AND star = ?"
            params.append(star_filter)
        if start_date_filter:
            query += " AND DATE(date_created) >= ?"
            params.append(start_date_filter)
        if end_date_filter:
            if end_date_filter:  # Ensure end_date_filter is not empty
                query += " AND DATE(date_created) <= ?"
                params.append(end_date_filter)

        offset = (page - 1) * 7
        query += " LIMIT 7 OFFSET ?"
        params.append(offset)

        print("Executing query:", query, "with params:", params)  # Debug

        con = get_db_connection()
        cur = con.cursor()
        cur.execute(query, params)
        ratings = cur.fetchall()

        cur.close()
        con.close()

        ratings_data = [
            {"RatingID": r[0], "star": r[1], "comments": r[2], "User_ID": r[3], "date_created": r[4]}
            for r in ratings
        ]

        print("Fetched ratings data:", ratings_data)  # Debug
        return jsonify({"ratings": ratings_data})
    
    except Exception as e:
        print(f"Error fetching ratings: {e}")  # Debug
        return jsonify({"error": "Internal Server Error"}), 500
