import sqlite3

# Path to your SQLite database
DATABASE = 'trabahanap.db'

def print_jobseeker_notifications():
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Execute a query to select all data from jobseeker_notifications
        # cursor.execute('SELECT * FROM application_status')
        cursor.execute('SELECT * FROM users')
        # Fetch all rows
        rows = cursor.fetchall()

        # Print each row
        for row in rows:
            print(row)

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the database connection
        if conn:
            conn.close()

if __name__ == '__main__':
    print_jobseeker_notifications()