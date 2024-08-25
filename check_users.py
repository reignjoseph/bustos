import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('trabahanap.db')

# Create a cursor object
cursor = conn.cursor()

# Execute the query to select all records from the users table
cursor.execute('SELECT * FROM users')

# Fetch all rows from the executed query
rows = cursor.fetchall()

# Print each row
for row in rows:
    print(row)

# Close the cursor and connection
cursor.close()
conn.close()