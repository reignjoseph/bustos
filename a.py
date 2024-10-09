import sqlite3

# Path to your SQLite database
DATABASE = 'trabahanap.db'

def count_available_jobs():
    """Count and print the number of available jobs from the jobs table."""
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()  # Create a cursor
    try:
        # Query to count available jobs
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE jobStatus='Available'")
        count = cursor.fetchone()[0]  # Fetch the first element from the result
        
        # Print the count
        print(f"Number of available jobs: {count}")

    except sqlite3.DatabaseError as e:
        print(f"Database error: {e}")

    finally:
        cursor.close()  # Close the cursor
        connection.close()  # Close the connection

if __name__ == '__main__':
    count_available_jobs()  # Call the function
