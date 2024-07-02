from flask import Flask, make_response, render_template, request, redirect, url_for,session, flash
import sqlite3
import os
from datetime import datetime, timedelta
from fpdf import FPDF
app = Flask(__name__)
app.config['SECRET_KEY'] = 'BILINGGO'
def get_login_data(conn):
    cur = conn.cursor()
    last_week = datetime.now() - timedelta(days=7)
    cur.execute('SELECT * FROM login_activity WHERE login_time >= ?', (last_week,))
    login_activities = cur.fetchall()

    daily_login_counts = {}
    total_login_duration = 0

    for activity in login_activities:
        login_time = datetime.strptime(activity['login_time'], '%Y-%m-%d %H:%M:%S')
        logout_time = datetime.strptime(activity['logout_time'], '%Y-%m-%d %H:%M:%S') if activity['logout_time'] else None
        day = login_time.strftime('%A')
        daily_login_counts[day] = daily_login_counts.get(day, 0) + 1
        
        if logout_time:
            duration = (logout_time - login_time).total_seconds()
            total_login_duration += duration

    avg_login_duration = total_login_duration / len(login_activities) if login_activities else 0

    return {
        'daily_login_counts': daily_login_counts,
        'avg_login_duration': avg_login_duration
    }    
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn
# Khởi tạo cơ sở dữ liệu
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
    conn.commit()
    conn.close()


# Route để hiển thị trang chủ dashboard của admin
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', admin_name="Admin Name")
@app.route('/admin_create_notification', methods=['POST'])
def admin_create_notification():
    if request.method == 'POST':
        notification_text = request.form.get('notification_text')
        attachment = request.files.get('attachment')
        attachment_filename = attachment.filename if attachment else None

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert notification into notifications table
        cur.execute('INSERT INTO notifications (notification_text, attachment_filename, created_at) VALUES (?, ?, ?)',
                    (notification_text, attachment_filename, datetime.now()))
        notification_id = cur.lastrowid
        
        # Insert notification into user_notifications table for each user
        cur.execute('SELECT username FROM users')
        users = cur.fetchall()
        for user in users:
            cur.execute('INSERT INTO user_notifications (email, notification_id) VALUES (?, ?)',
                        (user['username'], notification_id))
        
        conn.commit()
        conn.close()

        flash('Notification sent successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_dashboard'))

# Route để hiển thị báo cáo
@app.route('/admin_report')
def admin_report():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Truy cập cơ sở dữ liệu để lấy thông tin tài khoản
    cur.execute('SELECT COUNT(*) FROM users')
    total_accounts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='STUDENT'")
    student_accounts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='TEACHER'")
    teacher_accounts = cur.fetchone()[0]

    # Truy cập cơ sở dữ liệu đăng nhập
    login_data = get_login_data(conn)
    
    conn.close()
    return render_template('admin_report.html', total_accounts=total_accounts,
                           student_accounts=student_accounts, teacher_accounts=teacher_accounts,
                           login_data=login_data)
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
@app.route('/admin_create_account', methods=['GET', 'POST'])
def admin_create_account():
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
            return render_template('admin_create_account.html', message='Tạo tài khoản giáo viên thành công')

        else:
            msg = 'Địa chỉ email này đã được sử dụng.'

    return render_template('admin_create_account.html', message=msg)
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'User Report', 0, 1, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

@app.route('/admin_report/export_report')
def export_report():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM users')
    total_accounts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='STUDENT'")
    student_accounts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='TEACHER'")
    teacher_accounts = cur.fetchone()[0]

    login_data = get_login_data(conn)
    conn.close()

    pdf = PDFReport()
    pdf.add_page()
    pdf.chapter_title('Account Statistics')
    pdf.chapter_body(f'Total Accounts: {total_accounts}\nStudents: {student_accounts}\nTeachers: {teacher_accounts}')
    
    pdf.chapter_title('Login Activity')
    daily_login_counts = login_data['daily_login_counts']
    avg_login_duration = login_data['avg_login_duration']
    
    for day, count in daily_login_counts.items():
        pdf.chapter_body(f'{day}: {count} logins')

    pdf.chapter_body(f'Average login duration: {avg_login_duration:.2f} seconds')

    response = make_response(pdf.output(dest='S').encode('latin1'))
    response.headers.set('Content-Disposition', 'attachment', filename='report.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response

# Route để hiển thị trang admin chung
@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
