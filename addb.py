import sqlite3
from datetime import datetime, timedelta


conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS user_notifications (
    email TEXT,
    notification_id INTEGER,
    is_read INTEGER DEFAULT 0,
    FOREIGN KEY (email) REFERENCES users(username),
    FOREIGN KEY (notification_id) REFERENCES notifications(id)
)''')
conn.commit()
conn.close()