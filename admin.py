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

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or session.get ('user_type') != 'Admin':
        return redirect(url_for('signin'))

    return render_template('admin/admin.html')



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
        SELECT User_ID, email, fname, contactnum, address, dateRegister
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
        SELECT User_ID, email, fname, contactnum, address, dateRegister
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
