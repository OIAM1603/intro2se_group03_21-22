import sqlite3

def add_sample_data():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (name, email, role) VALUES
        ('Phạm Xuân Hòa', 'toan@example.com', 'student'),
        ('Nguyễn Thị Thanh Ngọc', 'nhi@example.com', 'teacher')
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_sample_data()
    print("Sample data added successfully.")
