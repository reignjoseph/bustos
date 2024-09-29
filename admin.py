import re
from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify, send_from_directory,abort,make_response,send_file
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
from threading import Thread
import time
import pdfkit



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







@app.route('/peso_report_view', methods=['GET'])
def peso_report_view():
    return render_template('admin/admin_reports.html')







































@app.route('/statistics', methods=['GET', 'POST'])
def statistics():
    return render_template('admin/employment_statistic.html')





















@app.route('/retrieve_admin_notification', methods=['GET'])
def retrieve_admin_notification():
    fname = request.args.get('fname')
    notification_id = request.args.get('notification_id')
    date_range = request.args.get('dateRange')  # Get date range from the request
    user_id = request.args.get('user_id')  # Get user_id from the request

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT notification_id, userType, picture, fname, notification_text, notification_date
            FROM admin_notification
            WHERE (notification_popup IS NULL OR notification_popup = '')
        """
        params = []

        if fname:
            query += " AND fname LIKE ?"
            params.append(f"%{fname}%")
        if notification_id:
            query += " AND notification_id = ?"
            params.append(notification_id)
        if user_id:
            query += " AND user_id = ?"  # Add condition for user_id
            params.append(user_id)
        if date_range:
            # Split the date range into start and end dates
            date_range = date_range.split(' to ')
            if len(date_range) == 2:
                start_date = date_range[0]
                end_date = date_range[1]
                query += " AND notification_date BETWEEN ? AND ?"
                params.append(start_date)
                params.append(end_date)

        print("Executing query:", query)
        print("With parameters:", params)

        cur.execute(query, params)
        notifications = cur.fetchall()

        print("Fetched notifications:", notifications)

        data = [
            {
                "notification_id": notification[0],
                "userType": notification[1],
                "picture": (
                    f"static/{notification[2]}" if notification[1] == "Jobseeker" 
                    else f"/static/images/employer-images/{notification[2]}" if notification[1] == "Employer" 
                    else f"/static/{notification[2]}" if notification[1] == "Admin" 
                    else notification[2]  # Default case if not Jobseeker, Employer, or Admin
                ),
                "fname": notification[3],
                "notification_text": notification[4],
                "notification_date": notification[5]
            }
            for notification in notifications
        ]

        print("Processed notification data:", data)

        return jsonify(data)

    except Exception as e:
        print(f"Error retrieving notifications: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

    finally:
        cur.close()
        conn.close()





# def update_notification_pictures():
#     conn = get_db_connection()
#     cur = conn.cursor()

#     try:
#         # Update pictures in admin_notification from users table
#         cur.execute("""
#             UPDATE admin_notification
#             SET picture = (SELECT profile FROM users WHERE User_ID = admin_notification.user_id)
#             WHERE user_id IN (SELECT User_ID FROM users)
#         """)
#         conn.commit()
#         print("Updated notification pictures.")
#     except Exception as e:
#         print(f"Error updating notification pictures: {e}")
#     finally:
#         cur.close()
#         conn.close()
# # Start the background thread
# Thread(target=update_notification_pictures, daemon=True).start()






































@app.route('/close_admin_notification', methods=['POST'])
def close_admin_notification():
    notification_id = request.json.get('notification_id')  # Get notification_id from the request
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch the user_id from the admin_notification table using the notification_id
        cur.execute("""
            SELECT user_id FROM admin_notification 
            WHERE notification_id = ?""", (notification_id,))
        user_id_row = cur.fetchone()
        
        if user_id_row:
            user_id = user_id_row[0]  # Extract user_id
            
            # Fetch the profile (picture) from the users table
            cur.execute("""
                SELECT profile FROM users 
                WHERE User_ID = ?""", (user_id,))
            profile_row = cur.fetchone()
            
            if profile_row:
                new_picture = profile_row[0]  # Get the profile picture
                
                # Update the admin_notification table with the new picture
                cur.execute("""
                    UPDATE admin_notification
                    SET picture = ?, notification_popup = 'false'
                    WHERE notification_id = ?""", (new_picture, notification_id))
                conn.commit()  # Commit the changes to the database

                return jsonify({"message": "Notification closed and picture updated successfully"}), 200
            else:
                return jsonify({"error": "User not found"}), 404
        else:
            return jsonify({"error": "Notification not found"}), 404

    except Exception as e:
        print(f"Error closing notification: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

    finally:
        cur.close()
        conn.close()




























@app.route('/get_userType', methods=['GET'])
def get_user_type():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Group by month and year
    cursor.execute('''
        SELECT strftime('%Y-%m', dateRegister) as month,  -- Group by Year-Month
               SUM(CASE WHEN userType = "Jobseeker" AND status = "Approved" THEN 1 ELSE 0 END) as jobseeker_count,
               SUM(CASE WHEN userType = "Employer" AND status = "Approved" THEN 1 ELSE 0 END) as employer_count
        FROM users
        GROUP BY month
        ORDER BY month ASC
    ''')

    results = cursor.fetchall()

    # Prepare the response
    data = {
        'dates': [row[0] for row in results],  # This will contain the year-month (YYYY-MM)
        'jobseeker': [row[1] for row in results],
        'employer': [row[2] for row in results]
    }

    conn.close()

    # Return the data as JSON
    return jsonify(data)
















@app.route('/retrieve_types_of_users')
def retrieve_types_of_users():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Database connection established.")  # Debugging line

    # Query to count users
    cursor.execute("SELECT COUNT(*) as total, "
                   "(SELECT COUNT(*) FROM users WHERE currentState='Active') as active, "
                   "(SELECT COUNT(*) FROM users WHERE currentState='Inactive') as inactive, "
                   "(SELECT COUNT(*) FROM users WHERE status='Approved') as approved "
                   "FROM users")

    result = cursor.fetchone()

    print("Query executed. Result fetched: ", result)  # Debugging line

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Check if result is None
    if result is None:
        print("No result returned from the database.")  # Debugging line
        return jsonify({'count': {'total': 0, 'active': 0, 'inactive': 0, 'approved': 0}})

    return jsonify({
        'count': {
            'total': result['total'],
            'active': result['active'],
            'inactive': result['inactive'],
            'approved': result['approved']
        }
    })




@app.route('/get_all_ratings', methods=['GET'])
def get_all_ratings():
    conn = get_db_connection()
    cursor = conn.cursor()

    current_year = datetime.now().year
    previous_year = current_year - 1

    # Total ratings for the current year
    cursor.execute("""
        SELECT COUNT(*) AS total_ratings, SUM(star) AS total_stars
        FROM rating 
        WHERE strftime('%Y', date_created) = ?
    """, (str(current_year),))
    result_current_year = cursor.fetchone()
    total_ratings_current_year = result_current_year['total_ratings']
    total_stars_current_year = result_current_year['total_stars'] or 0  # Handle case where no ratings exist
    average_ratings_current_year = total_stars_current_year / total_ratings_current_year if total_ratings_current_year > 0 else 0

    # Total ratings for the previous year
    cursor.execute("""
        SELECT COUNT(*) AS total_ratings, SUM(star) AS total_stars
        FROM rating 
        WHERE strftime('%Y', date_created) = ?
    """, (str(previous_year),))
    result_previous_year = cursor.fetchone()
    total_ratings_previous_year = result_previous_year['total_ratings']
    total_stars_previous_year = result_previous_year['total_stars'] or 0
    average_ratings_previous_year = total_stars_previous_year / total_ratings_previous_year if total_ratings_previous_year > 0 else 0

    # Calculate the percentage change in total ratings and average ratings
    percentage_change_ratings = ((total_ratings_current_year - total_ratings_previous_year) / total_ratings_previous_year) * 100 if total_ratings_previous_year > 0 else 0
    percentage_change_average = ((average_ratings_current_year - average_ratings_previous_year) / average_ratings_previous_year) * 100 if average_ratings_previous_year > 0 else 0

    # Count ratings by star for the current year
    cursor.execute("""
        SELECT star, COUNT(*) AS count 
        FROM rating 
        WHERE strftime('%Y', date_created) = ?
        GROUP BY star 
        ORDER BY star
    """, (str(current_year),))
    ratings_by_star = cursor.fetchall()

    conn.close()

    ratings_dict = {row['star']: row['count'] for row in ratings_by_star}

    return jsonify({
        'total_ratings': total_ratings_current_year,
        'average_ratings': round(average_ratings_current_year, 2),  # Rounded average rating
        'percentage_change_ratings': percentage_change_ratings,
        'percentage_change_average': percentage_change_average,
        'ratings_by_star': ratings_dict
    })












@app.route('/get_job_count', methods=['POST'])
def get_job_count():
    data = request.get_json()
    job_status = data.get('jobStatus')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) as count FROM jobs WHERE jobStatus = ?"
    cursor.execute(query, (job_status,))
    row = cursor.fetchone()
    
    conn.close()
    return jsonify({'count': row[0]})






@app.route('/fetch_admin_announcements', methods=['GET'])
def fetch_admin_announcements():
    announcementID = request.args.get('announcementID', default=None, type=int)
    status = request.args.get('status', default=None, type=str)
    page = request.args.get('page', default=1, type=int)
    itemsPerPage = request.args.get('itemsPerPage', default=5, type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Specify the columns to select, excluding "image"
    query = """SELECT announcementID, "What", "When", "Where", "Requirement", "Description", "date_posted", "status" 
               FROM announcement WHERE 1=1"""
    params = []

    if announcementID is not None:
        query += " AND announcementID = ?"
        params.append(announcementID)
    
    if status and status != "Both":
        query += " AND status = ?"
        params.append(status)

    query += " LIMIT ? OFFSET ?"
    params.append(itemsPerPage)
    params.append((page - 1) * itemsPerPage)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Convert to JSON format
    announcements = [{'announcementID': row[0], 'What': row[1], 'When': row[2], 'Where': row[3],
                     'Requirement': row[4], 'Description': row[5], 'date_posted': row[6], 'status': row[7]} 
                     for row in rows]

    return jsonify(announcements)















































@app.route('/insert_announcement', methods=['POST'])
def insert_announcement():
    try:
        # Get the form data and print them for debugging
        image = request.files['image']
        what = request.form['what']
        when = request.form['when']  # e.g., '2024-09-21 to 2024-09-27'
        where = request.form['location']
        requirement = request.form['requirement']
        description = request.form['description']

        print(f"Received form data: what={what}, when={when}, where={where}, requirement={requirement}, description={description}")

        # Save image to the static folder
        image_path = ''
        if image:
            image_path = f'static/images/admin-uploads/{image.filename}'
            image.save(image_path)
            print(f"Image saved to: {image_path}")
        else:
            print("No image uploaded")

        # Get current date in the Philippines timezone
        timezone = pytz.timezone('Asia/Manila')
        current_date_ph = datetime.now(timezone)
        print(f"Current date in PH timezone: {current_date_ph}")

        # Calculate status based on 'when' field
        # Split the 'when' field to get the start and end dates
        date_range = when.split(' to ')
        start_date = datetime.strptime(date_range[0], '%Y-%m-%d')
        end_date = datetime.strptime(date_range[1], '%Y-%m-%d') if len(date_range) > 1 else start_date

        # Make start_date and end_date timezone-aware
        start_date = timezone.localize(start_date)
        end_date = timezone.localize(end_date)
        print(f"Parsed and localized date range: start_date={start_date}, end_date={end_date}")

        # Determine status: "Available" if today is in the range, otherwise "Unavailable"
        if start_date <= current_date_ph <= end_date:
            status = "Available"
        else:
            status = "Unavailable"
        print(f"Calculated status: {status}")

        # Insert data into the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into the "announcement" table, including date_posted and status
        cursor.execute('''
            INSERT INTO announcement ("image", "What", "When", "Where", "Requirement", "Description", "date_posted", "status")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (image_path, what, when, where, requirement, description, current_date_ph.strftime('%Y-%m-%d %H:%M:%S'), status))

        conn.commit()
        conn.close()

        print("Announcement successfully inserted into the database")

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
    page = int(request.args.get('page', 1))  # Default to 1

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
        try:
            start_date, end_date = date.split(' to ')
            query += " AND date(u.dateRegister) BETWEEN ? AND ?"
            filters.extend([start_date, end_date])
        except ValueError:
            return jsonify({"error": "Invalid date range format"}), 400

    # Pagination logic
    itemsPerPage = 5  # Set max items per page
    offset = (page - 1) * itemsPerPage  # Calculate offset
    query += " LIMIT ? OFFSET ?"
    filters.extend([itemsPerPage, offset])  # Add limit and offset to filters

    # Debug output
    print("Final Query:", query)
    print("Filters for users:", filters)

    try:
        users = cursor.execute(query, filters).fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Count total users without pagination limits
    total_users_query = """
        SELECT COUNT(*) FROM users u
        LEFT JOIN pdf p ON u.User_ID = p.User_ID
        WHERE 1=1
    """
    
    count_filters = []
    if user_id:
        total_users_query += " AND u.User_ID = ?"
        count_filters.append(user_id)
    if fname:
        total_users_query += " AND u.fname LIKE ?"
        count_filters.append(f"%{fname}%")
    if email:
        total_users_query += " AND u.email LIKE ?"
        count_filters.append(f"%{email}%")
    if userType:
        total_users_query += " AND u.userType = ?"
        count_filters.append(userType)
    if status:
        total_users_query += " AND u.status = ?"
        count_filters.append(status)
    if date:
        try:
            start_date, end_date = date.split(' to ')
            total_users_query += " AND date(u.dateRegister) BETWEEN ? AND ?"
            count_filters.extend([start_date, end_date])
        except ValueError:
            return jsonify({"error": "Invalid date range format"}), 400

    total_users = cursor.execute(total_users_query, count_filters).fetchone()[0]

    conn.close()

    users_list = [
        {
            "User_ID": row["User_ID"],
            "email": row["email"],
            "fname": row["fname"],
            "userType": row["userType"],
            "status": row["status"],
            "dateRegister": row["dateRegister"],
            "pdf_form": row["pdf_form"]
        }
        for row in users
    ]

    return jsonify({"users": users_list, "total": total_users})












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
        WHERE userType = 'Jobseeker' AND status = 'Approved'
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
        WHERE userType = 'Employer' AND status = 'Approved'
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
