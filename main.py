from flask import Flask, request, redirect, url_for, render_template, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Add a secret key for flashing messages

app.config['UPLOAD_FOLDER'] = 'static/images/employer-uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_db_connection():
    conn = sqlite3.connect('trabahanap.db')
    conn.row_factory = sqlite3.Row
    return conn

def update_job_statuses():
    conn = get_db_connection()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("""
        UPDATE jobs 
        SET jobStatus = 'Unavailable'
        WHERE closingDate <= ?
    """, (current_time,))
    conn.commit()
    conn.close()













# This is Employer
@app.route('/employer', methods=['GET', 'POST'])
def employer():
    if request.method == 'POST':
        # Handle form submission
        return post_job()  # Redirect to post_job route
    
    return render_template('employer/employer.html')

@app.route('/post_job', methods=['POST'])
def post_job():
    # Retrieve form data
    print("POST request received at /post_job")  # Debug print
    try:
        title = request.form['title']
        position = request.form['position']
        description = request.form['description']
        location = request.form['location']
        natureOfWork = request.form['natureOfWork']
        salary = request.form['salary']
        company = request.form['company']
        closingDate = request.form['closingDate']
        jobStatus = request.form['jobStatus']
    except KeyError as e:
        flash(f'Missing form field: {e}')
        return redirect(request.url)

    # Convert closingDate string to datetime object
    try:
        closing_date = datetime.strptime(closingDate, '%Y-%m-%d %H:%M')
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD HH:MM.')
        return redirect(request.url)

    # Validate jobStatus
    if jobStatus not in ['Available', 'Unavailable']:
        flash('Invalid job status. Please select either "Available" or "Unavailable".')
        return redirect(request.url)
    
    # Check if the post request has the file part
    if 'image' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['image']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        image_path = f'images/employer-uploads/{filename}'  # Relative path for the URL
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO jobs (title, position, description, image, location, natureOfWork, salary, Company, closingDate, jobStatus) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (title, position, description, image_path, location, natureOfWork, salary, company, closing_date, jobStatus)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('employer'))

    flash('Invalid file format')
    return redirect(request.url)


# This is the jobseeker
@app.route('/notification')
def notification():
    return render_template('/jobseeker/notification.html')

@app.route('/jobseeker')
def jobseeker():
    update_job_statuses()
    if 'user_id' in session and session['user_type'] == 'Jobseeker':
        # Connect to the database and fetch job announcements
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query to fetch jobs (you may need to adjust the query based on your table structure)
        cursor.execute('SELECT * FROM jobs')
        jobs = cursor.fetchall()
        
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        # Pass the jobs to the template
        return render_template('/jobseeker/jobseeker.html', jobs=jobs)
    
    return redirect(url_for('signin'))













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
        
        # Connect to the SQLite database
        conn = sqlite3.connect('trabahanap.db')
        cursor = conn.cursor()
        
        # Execute the query to select the user with the provided email and password
        cursor.execute('''
            SELECT * FROM users WHERE email = ? AND password = ? AND userType = 'Jobseeker'
        ''', (email, password))
        user = cursor.fetchone()
        
        # Close the cursor and connection
        cursor.close()
        conn.close()

        # Check if user is found
        if user:
            session['user_id'] = user[0]
            session['user_type'] = user[4]
            
            # Redirect to the jobseeker page
            return redirect(url_for('jobseeker'))
        else:
            return "The user is not defined", 401

    # Render the sign-in form
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
