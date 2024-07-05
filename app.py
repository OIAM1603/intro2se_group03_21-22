from flask import Flask, jsonify, make_response, render_template, request, redirect, url_for,session, flash
import sqlite3
import os
from datetime import datetime, timedelta
from fpdf import FPDF
app = Flask(__name__)
app.config['SECRET_KEY'] = 'BILINGGO'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# # Hàm để lấy dữ liệu đăng nhập từ cơ sở dữ liệu SQLite
def get_login_data(conn, filter_type='month'):
    cur = conn.cursor()
    
    if filter_type == 'month':
        today = datetime.now()
        first_day_of_this_month = today.replace(day=1)
        last_day_of_prev_month = first_day_of_this_month - timedelta(days=1)
        first_day_of_prev_month = last_day_of_prev_month.replace(day=1)
        
        cur.execute('''
            SELECT email, login_time, logout_time FROM login_activity 
            WHERE login_time >= ? AND login_time <= ?
        ''', (first_day_of_prev_month.strftime('%Y-%m-%d 00:00:00'), last_day_of_prev_month.strftime('%Y-%m-%d 23:59:59')))
    else:
        cur.execute('SELECT email, login_time, logout_time FROM login_activity')
    
    login_activities = cur.fetchall()
    
    daily_login_counts = {}
    total_duration = 0
    count = 0
    
    for activity in login_activities:
        login_time = datetime.strptime(activity[1], '%Y-%m-%d %H:%M:%S')
        logout_time = datetime.strptime(activity[2], '%Y-%m-%d %H:%M:%S')
        duration = (logout_time - login_time).total_seconds()
        
        date_str = login_time.strftime('%Y-%m-%d')
        if date_str not in daily_login_counts:
            daily_login_counts[date_str] = 0
        daily_login_counts[date_str] += 1
        
        total_duration += duration
        count += 1
    
    avg_login_duration = total_duration / count if count > 0 else 0
    return {
        'daily_login_counts': daily_login_counts,
        'avg_login_duration': avg_login_duration
    }

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            phone TEXT,
            gender TEXT,
            role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # Tạo bảng notifications
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        notification_text TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_notifications (
    email TEXT,
    notification_id INTEGER,
    is_read INTEGER DEFAULT 0,
    FOREIGN KEY (email) REFERENCES users(username),
    FOREIGN KEY (notification_id) REFERENCES notifications(notification_id)
    )''')
    # Tạo bảng login_activity nếu chưa tồn tại
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            login_time TEXT,
            logout_time TEXT
        )
    ''')
    # cursor.execute('''
    # INSERT INTO login_activity (email, login_time, logout_time)
    # VALUES
    #     ('user1@example.com', '2024-07-04 08:30:00', '2024-07-04 09:00:00'),
    #     ('user2@example.com', '2024-07-04 09:00:00', '2024-07-04 10:00:00'),
    #     ('user1@example.com', '2024-07-03 15:00:00', '2024-07-03 15:30:00'),
    #     ('user3@example.com', '2024-07-03 10:00:00', '2024-07-03 11:00:00');
    # ''')

    conn.commit()
    conn.close()
init_db()
# Route để hiển thị trang chủ dashboard của admin
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', admin_name="Admin Name")
@app.route('/admin_create_notification', methods=['GET', 'POST'])
def admin_create_notification():
    init_db()
    if request.method == 'POST':
        title = request.form.get('title')
        notification_text = request.form.get('notification_text')
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert notification into notifications table
        cur.execute('INSERT INTO notifications (title, notification_text, created_at) VALUES (?, ?, ?)',
                    (title, notification_text, datetime.now()))
        notification_id = cur.lastrowid
        
        # Insert notification into user_notifications table for each user
        cur.execute('SELECT username FROM users')
        users = cur.fetchall()
        for user in users:
            cur.execute('INSERT INTO user_notifications (email, notification_id) VALUES (?, ?)',
                        (user['username'], notification_id))
        
        conn.commit()
        conn.close()

        flash('Đã tạo thông báo đến người dùng thành công', 'success')
        return redirect(url_for('admin_create_notification'))
    return render_template('admin_create_notification.html')

# Route để hiển thị danh sách tài khoản theo từng vai trò
@app.route('/admin_view_account')
def admin_view_account():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    # Lấy danh sách sinh viên và giáo viên từ cơ sở dữ liệu
    students = conn.execute('SELECT name FROM users WHERE role = "STUDENT"').fetchall()
    teachers = conn.execute('SELECT name FROM users WHERE role = "TEACHER"').fetchall()

    # Lấy danh sách tài khoản mới được tạo gần đây
    recent_accounts = conn.execute('SELECT name, role FROM users ORDER BY created_at DESC LIMIT 4').fetchall()

    conn.close()
    return render_template('admin_view_account.html', students=students, teachers=teachers, recent_accounts=recent_accounts)

# Route để xử lý tạo tài khoản
@app.route('/admin_authorize_teacher_account', methods=['GET', 'POST'])
def admin_authorize_teacher_account():
    init_db()  # Đảm bảo cơ sở dữ liệu đã được khởi tạo

    msg = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        gender = request.form['gender']

        # Kết nối đến cơ sở dữ liệu
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Kiểm tra xem email đã tồn tại trong cơ sở dữ liệu chưa
        cursor.execute("SELECT * FROM users WHERE username=?", (email,))
        existing_user = cursor.fetchone()

        if existing_user is None:
            # Thêm thông tin người dùng vào cơ sở dữ liệu
            cursor.execute("INSERT INTO users (username, password, name, phone, gender, role) VALUES (?, ?, ?, ?, ?, ?)",
                           (email, password, name, phone, gender, 'TEACHER'))
            conn.commit()
            conn.close()

            # Chuyển hướng đến trang đăng nhập (signin) và thông báo thành công
            return render_template('admin_create_account.html', message='Successfully created teacher account')

        else:
            msg = 'This email address is already in use.'

    return render_template('admin_authorize_teacher_account.html', message=msg)

@app.route('/admin_report')
def admin_report():
    conn = sqlite3.connect('database.db')
    
    # Lấy dữ liệu đăng nhập từ cơ sở dữ liệu cho tháng gần nhất
    login_data = get_login_data(conn, filter_type='month')

    # Thống kê tài khoản
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    total_accounts = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM users WHERE role='STUDENT'")
    student_accounts = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM users WHERE role='TEACHER'")
    teacher_accounts = cur.fetchone()[0] or 0

    conn.close()

    return render_template('admin_report.html', total_accounts=total_accounts,
                           student_accounts=student_accounts, teacher_accounts=teacher_accounts,
                           login_data=login_data)

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Login Activity Report', 0, 1, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

@app.route('/admin_report/export_report')
def export_report():
    conn = sqlite3.connect('database.db')
    
    # Lấy dữ liệu đăng nhập từ cơ sở dữ liệu cho tháng gần nhất
    login_data = get_login_data(conn, filter_type='month')

    # Thống kê tài khoản
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    total_accounts = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM users WHERE role='STUDENT'")
    student_accounts = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM users WHERE role='TEACHER'")
    teacher_accounts = cur.fetchone()[0] or 0

    conn.close()

    pdf = PDFReport()
    pdf.add_page()
    pdf.chapter_title('Account Statistics')
    pdf.chapter_body(f'Total Accounts: {total_accounts}\nStudents: {student_accounts}\nTeachers: {teacher_accounts}')
    
    pdf.chapter_title('Login Activity (Last Month)')
    daily_login_counts = login_data['daily_login_counts']
    avg_login_duration = login_data['avg_login_duration']
    
    for day, count in daily_login_counts.items():
        pdf.chapter_body(f'{day}: {count} logins')

    pdf.chapter_body(f'Average login duration: {avg_login_duration:.2f} seconds')

    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers.set('Content-Disposition', 'attachment', filename='login_activity_report.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response
# Route để hiển thị trang admin chung
@app.route('/')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
        # // </script>
        # // <form action="{{ url_for('export_report') }}" method="get">
        # //     <button type="submit">Export to PDF</button>
        # // </form>