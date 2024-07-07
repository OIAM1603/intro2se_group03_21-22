from flask import Flask, flash, jsonify, make_response, render_template, request, redirect, url_for, session
from fpdf import FPDF
import pytz
import requests
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'BILINGUO'
### Tài khoản admin
email_admin ='admin@gmail.com'
password_admin = 'bilinguo'

# Hàm để lấy dữ liệu đăng nhập từ cơ sở dữ liệu SQLite
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

def get_db_connection():
    conn = sqlite3.connect('database.db', timeout=10)
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
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS FLASHCARD(
               ID INTEGER PRIMARY KEY AUTOINCREMENT,
               EMAIL TEXT,
               THEME TEXT,
               WORD TEXT,
               PRONUNCIATION TEXT,
               FORM TEXT,
               MEANING TEXT)''')
    conn.commit()
    # Tạo bảng login_activity nếu chưa tồn tại
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            login_time TEXT,
            logout_time TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            notification_id INTEGER,
            FOREIGN KEY (email) REFERENCES users(username),
            FOREIGN KEY (notification_id) REFERENCES notifications(id)
        )
    ''')
        # Tạo bảng recent_activities
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recent_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_description TEXT,
            activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        notification_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER,
            question TEXT NOT NULL,
            option_A TEXT NOT NULL,
            option_B TEXT NOT NULL,
            option_C TEXT NOT NULL,
            option_D TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teacher_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            activity_description TEXT,
            activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(username)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assigned_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER,
            student_username TEXT,
            assigned_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed BOOLEAN DEFAULT 0,
            deadline TIMESTAMP,
            score REAL,
            FOREIGN KEY (test_id) REFERENCES tests(id),
            FOREIGN KEY (student_username) REFERENCES users(username)
        )
    ''')
    conn.commit()
    conn.close()
init_db()
conn = sqlite3.connect('database.db', check_same_thread= False)
cursor = conn.cursor()

###############################################
###############--  ROLE ADMIN  --##############
###############################################

# Route để hiển thị trang chủ dashboard của admin
@app.route('/admin_dashboard()')
def admin_dashboard():
    conn = get_db_connection()

    # Lấy số lượt truy cập trong tuần hiện tại
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) AS visit_count, strftime('%w', login_time) AS day_of_week
        FROM login_activity
        WHERE login_time BETWEEN ? AND ?
        GROUP BY strftime('%w', login_time)
    ''', (start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')))
    
    weekly_visits = cursor.fetchall()
    visit_counts = {str(i): 0 for i in range(7)}
    for visit in weekly_visits:
        visit_counts[visit['day_of_week']] = visit['visit_count']
    
    # Lấy các hoạt động gần đây
    cursor.execute('SELECT activity_description FROM recent_activities ORDER BY activity_time DESC LIMIT 5')
    recent_activities = cursor.fetchall()

    conn.close()
    return render_template('admin_dashboard.html', 
                           admin_name="Admin Name",
                           visit_counts=visit_counts,
                           recent_activities=recent_activities)

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
        cur.execute('''
            INSERT INTO recent_activities (activity_description) 
            VALUES (?)
        ''', (f'Created notification: {title}.',))
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
            cursor.execute('''
                INSERT INTO recent_activities (activity_description) 
                VALUES (?)
            ''', (f'Admin created a new teacher account for {email}.',))
            conn.commit()

            conn.close()

            # Thông báo thành công
            return render_template('admin_authorize_teacher_account.html', message='Successfully created teacher account')

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
    cur.execute('''
        INSERT INTO recent_activities (activity_description) 
        VALUES (?)
    ''', (f'Export report.',))
    conn.commit()
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

###############################################
###############--  ROLE STUDENT  --############
###############################################

# @app.route('/')
# def home():
#     return render_template('index.html')

# @app.route('/signin', methods=['GET', 'POST'])
# def signin():
#     msg = ''
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         # Here you would typically check the credentials against a database
#         cursor.execute("SELECT * FROM USERS WHERE USERNAME = ? AND PASSWORD = ?",(email,password))
#         row_num = len(cursor.fetchall())
#         if row_num == 1:
#               # Lấy thời gian hiện tại theo múi giờ Việt Nam
#             tz = pytz.timezone('Asia/Ho_Chi_Minh')
#             signin_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
#             cursor.execute("INSERT INTO login_activity (EMAIL, LOGIN_TIME) VALUES (?,?)",(email,signin_time))
#             conn.commit()
#             cursor.execute("SELECT * FROM login_activity")
#             session['user_email'] = email
#             return redirect(url_for('dashboard'))
#         cursor.execute("SELECT * FROM USERS WHERE USERNAME = ?",(email,))
#         row_num = len(cursor.fetchall())
#         if row_num == 0:
#             msg = 'This email has not been registered!'
#         else:
#             msg = 'Wrong password!'
#     return render_template('signin.html', message = msg)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        gender = request.form['gender']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE username=?", (email,))
        if cursor.fetchone() is None:
            # Insert new user into the database
            cursor.execute("INSERT INTO users (username, password, name, phone, gender, role) VALUES (?,?,?,?,?,?)",
                           (email, password, name, phone, gender, 'STUDENT'))
            conn.commit()
            conn.close()
            return redirect(url_for('signin'))
        else:
            msg = 'This email address has already been used.'

        conn.close()

    return render_template('signup.html', message=msg)


# @app.route('/logout')
# def logout():
#     session.pop('user_id', None)
#     return redirect(url_for('index'))

@app.route('/profile')
def profile():
    # Thay đổi nội dung bên dưới với thông tin profile thực tế của sinh viên
    user_info = {
        'name': 'Name Student',
        'email': 'student@example.com',
        'enrolled_courses': ['Course 1', 'Course 2', 'Course 3']
    }
    return render_template('profile.html', user=user_info)

@app.route('/dashboard')
def dashboard():
    user_email = session.get('user_email')  # Replace with actual user email from session or login
    if not user_email:
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get notifications for the user
    cur.execute('''
    SELECT n.*, un.is_read 
    FROM notifications n 
    JOIN user_notifications un ON n.notification_id = un.notification_id 
    WHERE un.email = ? AND un.is_read = 0
    ORDER BY n.created_at DESC
    ''', (user_email,))
    notifications = cur.fetchall()
    
    # Count unread notifications
    cur.execute('SELECT COUNT(*) FROM user_notifications WHERE email = ? AND is_read = 0', (user_email,))
    unread_count = cur.fetchone()[0]
    
    conn.close()
    conn.close()
    return render_template('dashboard.html', notifications=notifications, unread_count=unread_count)

@app.route('/notifications/read/<int:notification_id>')
def mark_notification_read(notification_id):
    user_email = session.get('user_email')
    
    if user_email is None:
        return redirect(url_for('signin'))
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('UPDATE user_notifications SET is_read = 1 WHERE email = ? AND notification_id = ?', (user_email, notification_id))
        conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/notifications/unread_count')
def unread_count():
    user_email = session.get('user_email')
    
    if user_email is None:
        return {'count': 0}
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM user_notifications WHERE email = ? AND is_read = 0', (user_email,))
        count = cur.fetchone()[0]
    return {'count': count}

@app.route('/get_notifications')
def get_notifications():
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('signin'))

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT n.notification_id, n.title, n.notification_text, n.created_at 
            FROM notifications n 
            JOIN user_notifications un ON n.notification_id = un.notification_id 
            WHERE un.email = ? AND un.is_read = 0
            ORDER BY n.created_at DESC
        ''', (user_email,))
        notifications = cur.fetchall()

    notifications_list = [
        {"id": n['notification_id'], "title":n['title'], "text": n['notification_text'],  "created_at": n['created_at']}
        for n in notifications
    ]
    
    return jsonify(notifications_list)


@app.route('/mark_as_read/<int:notification_id>', methods=['POST'])
def mark_as_read(notification_id):
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('signin'))

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('UPDATE user_notifications SET is_read = 1 WHERE notification_id = ? AND email = ?', (notification_id, user_email))
        conn.commit()
    
    return jsonify({"status": "success"})

@app.route('/notification/<int:notification_id>')
def notification(notification_id):
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('signin'))

    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Lấy danh sách thông báo
        cur.execute('''
        SELECT n.notification_id, n.title, n.created_at, un.is_read 
        FROM notifications n
        JOIN user_notifications un ON n.notification_id = un.notification_id
        WHERE un.email = ?
        ORDER BY n.created_at DESC
        ''', (user_email,))
        notifications = cur.fetchall()
        
        # Lấy chi tiết thông báo được chọn
        cur.execute('''
        SELECT n.*, un.is_read FROM notifications n
        JOIN user_notifications un ON n.notification_id = un.notification_id
        WHERE n.notification_id = ? AND un.email = ?
        ''', (notification_id, user_email))
        notification = cur.fetchone()
        
        if not notification:
            return redirect(url_for('dashboard'))
    return render_template('notification.html', notifications=notifications, notification=notification)


count = 0;
@app.route('/flashcards')
@app.route('/flashcards', methods=['GET', 'POST'])
def flashcards():
    if 'user_email' in session:
        email = session['user_email']
        if request.method == 'POST':
            vocabulary = request.form['Vocabulary']
            pronunciation = request.form['Pronunciation']
            form = request.form['Definition']
            meaning = request.form['Meaning']
            if 'newCategory' in request.form:
                theme = request.form['newCategory']
            else:
                theme = request.form['currentCategory']
            # Insert the new flashcard into the database
            cursor.execute("INSERT INTO FLASHCARD (EMAIL, THEME, WORD, PRONUNCIATION, FORM, MEANING) VALUES (?, ?, ?, ?, ?, ?)",
                           (email, theme, vocabulary, pronunciation, form, meaning))
            conn.commit()
            
            # Redirect to the flashcards page or perform any other action as needed
            return redirect(url_for('flashcards'))
        
        if request.method == "GET":
            selected_theme = request.args.get('theme')
            print('checkpoint')
            print(selected_theme)
            if selected_theme:
                cursor.execute('SELECT THEME, WORD, PRONUNCIATION, FORM, MEANING FROM FLASHCARD WHERE EMAIL = (?) AND THEME = ?',(email, selected_theme))
                flashcards = cursor.fetchall()
                return render_template('flashcards.html', flashcards=flashcards, s_theme = selected_theme)
            else:
                cursor.execute("SELECT DISTINCT THEME FROM FLASHCARD")
                theme = [row[0] for row in cursor.fetchall()]
                print(theme)
                print('testcard')
                cursor.execute('SELECT THEME, WORD, PRONUNCIATION, FORM, MEANING FROM FLASHCARD WHERE EMAIL = ?',(email,))
                flashcards = cursor.fetchall()
                print('check 1')
                return render_template('flashcards.html', flashcards = flashcards, email=email, themes = theme)
        # Handle GET request to display the flashcards page
    else:
        return redirect(url_for('signin'))
    
@app.route('/dictionary', methods=['GET', 'POST'])
def dictionary():
    definition = None
    if request.method == 'POST':
        word = request.form['word']
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                definition = format_definition(data[0])
        else:
            definition = "Word not found."

    return render_template('dictionary.html', definition=definition)

def format_definition(data):
    result = f"Word: {data['word']}\nPhonetic: {data.get('phonetic', 'N/A')}\nOrigin: {data.get('origin', 'N/A')}\n"
    for meaning in data['meanings']:
        result += f"\nPart of Speech: {meaning['partOfSpeech']}\n"
        for definition in meaning['definitions']:
            result += f"{definition['definition']}\n"
            if 'example' in definition:
                result += f"Example: {definition['example']}\n"
    return result

# Route for /mocktest
@app.route('/mocktest', methods=['GET', 'POST'])
def mocktest():
    if 'user_email' not in session:
        return redirect(url_for('signin'))

    username = session['user_email']
    conn = get_db_connection()
    now = datetime.utcnow()

    tests = conn.execute('''
        SELECT at.id, at.test_id, at.assigned_time, at.completed, at.deadline, at.score, 
               t.title as test_name, 
               CASE 
                   WHEN at.completed = 1 THEN "Completed"
                   WHEN at.deadline < ? THEN "Test overdue"
                   ELSE "Pending"
               END as status
        FROM assigned_tests at
        JOIN tests t ON at.test_id = t.id
        WHERE at.student_username = ?
    ''', (now, username)).fetchall()

    conn.close()
    return render_template('mocktest.html', tests=tests)

# Route for viewing test questions and submitting answers
@app.route('/take_test/<int:test_id>', methods=['GET', 'POST'])
def take_test(test_id):
    if 'user_email' not in session:
        return redirect(url_for('signin'))

    username = session['user_email']
    conn = get_db_connection()

    if request.method == 'POST':
        answers = request.form.getlist('answers')
        questions = conn.execute('SELECT id, correct_option FROM questions WHERE test_id = ?', (test_id,)).fetchall()

        # Ensure number of answers matches number of questions
        if len(answers) != len(questions):
            flash('An error occurred while processing your answers. Please try again.')
            return redirect(url_for('mocktest'))

        correct_answers_count = sum(1 for question, answer in zip(questions, answers) if question['correct_option'] == answer)
        score = correct_answers_count

        # Update completed status and score in assigned_tests table
        conn.execute('UPDATE assigned_tests SET completed = 1, score = ? WHERE test_id = ? AND student_username = ?', 
                     (score, test_id, username))
        conn.commit()

        flash(f'You have completed the test. Your score is {score}.')
        return redirect(url_for('mocktest'))

    # Fetch questions for the test
    questions = conn.execute('SELECT * FROM questions WHERE test_id = ?', (test_id,)).fetchall()
    conn.close()
    return render_template('take_test.html', questions=questions, test_id=test_id)

@app.route('/admin_profile')
def admin_profile():
    # Thay đổi nội dung bên dưới với thông tin profile thực tế của sinh viên
    user_info = {
        'name': 'Name Admin',
        'email': 'admin@example.com',
        'enrolled_courses': ['Course 1', 'Course 2', 'Course 3']
    }
    return render_template('admin_profile.html', user=user_info)

###############################################
#############--  ROLE TEACHER  --##############
###############################################



@app.route('/teacher_profile')
def teacher_profile():
    # Thay đổi nội dung bên dưới với thông tin profile thực tế của sinh viên
    user_info = {
        'name': 'Name Teacher',
        'email': 'teacher@example.com',
        'enrolled_courses': ['Course 1', 'Course 2', 'Course 3']
    }
    return render_template('teacher_profile.html', user=user_info)

@app.route('/create_test', methods=['GET', 'POST'])
def create_test():
    if request.method == 'POST':
        title = request.form['title']
        num_questions = int(request.form['num_questions'])

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO tests (title) VALUES (?)', (title,))
        test_id = c.lastrowid

        for i in range(1, num_questions + 1):
            question = request.form[f'questions[{i}][question]']
            option_A = request.form[f'questions[{i}][option_A]']
            option_B = request.form[f'questions[{i}][option_B]']
            option_C = request.form[f'questions[{i}][option_C]']
            option_D = request.form[f'questions[{i}][option_D]']
            correct_option = request.form[f'questions[{i}][correct_option]']

            c.execute('''
                INSERT INTO questions (test_id, question, option_A, option_B, option_C, option_D, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (test_id, question, option_A, option_B, option_C, option_D, correct_option))
        # Log activity for teacher
        teacher_email = session['user_email']
        c.execute('''
            INSERT INTO teacher_activities ( teacher_id, activity_description)
            VALUES (?, ?)
        ''', (teacher_email, f'Created test: {title}'))

        conn.commit()
        conn.close()
        flash('Đã tạo test thành công', 'success')
        return redirect(url_for('create_test'))  # Redirect to home page after creating test
    
    return render_template('create_test.html')

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user_email' not in session:
        return redirect(url_for('teacher_signin'))
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) AS visit_count, strftime('%w', login_time) AS day_of_week
        FROM login_activity
        WHERE login_time BETWEEN ? AND ?
        GROUP BY strftime('%w', login_time)
    ''', (start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')))
    teacher_email = session['user_email']
    weekly_visits = cursor.fetchall()
    visit_counts = {str(i): 0 for i in range(7)}
    for visit in weekly_visits:
        visit_counts[visit['day_of_week']] = visit['visit_count']

    cursor.execute('''
        SELECT activity_description, activity_time 
        FROM teacher_activities 
        WHERE teacher_id = ? 
        ORDER BY activity_time DESC 
        LIMIT 5
    ''', (teacher_email,))
    activities = cursor.fetchall()
    conn.close()

    return render_template('teacher_dashboard.html', teacher_name=teacher_email,
                           visit_counts=visit_counts, activities=activities)

# @app.route('/teacher_signin', methods=['GET', 'POST'])
# def teacher_signin():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         # Here you would typically check the credentials against a database
#         cursor.execute("SELECT * FROM USERS WHERE USERNAME = ? AND PASSWORD = ?",(email,password))
#         row_num = len(cursor.fetchall())
#         if row_num == 1:
#             # Lấy thời gian hiện tại theo múi giờ Việt Nam
#             tz = pytz.timezone('Asia/Ho_Chi_Minh')
#             signin_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
#             cursor.execute("INSERT INTO login_activity (EMAIL, LOGIN_TIME) VALUES (?,?)",(email,signin_time))
#             conn.commit()
#             cursor.execute("SELECT * FROM login_activity")
#             rows = cursor.fetchall()
#             print(rows)
#             session['user_email'] = email
#             return redirect(url_for('teacher_dashboard'))
#         else:
#             print('Sign In Denied')
#     return render_template('teacher_signin.html')

@app.route('/assign_test', methods=['GET', 'POST'])
def assign_test():
    if request.method == 'POST':
        test_id = request.form['test_id']
        student_username = request.form['student_username']
        deadline = request.form['deadline']

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if student_username == 'all':
            c.execute('SELECT username FROM users WHERE role = "STUDENT"')
            students = c.fetchall()
            for student in students:
                c.execute('''
                    INSERT INTO assigned_tests (test_id, student_username, deadline)
                    VALUES (?, ?, ?)
                ''', (test_id, student['username'], deadline))
        else:
            c.execute('''
                INSERT INTO assigned_tests (test_id, student_username, deadline)
                VALUES (?, ?, ?)
            ''', (test_id, student_username, deadline))

        # Log activity for teacher
        teacher_email = session['user_email']
        c.execute('''
            INSERT INTO teacher_activities (teacher_id, activity_description)
            VALUES (?, ?)
        ''', (teacher_email, f'Assigned test ID {test_id} to {student_username} with deadline {deadline}'))

        conn.commit()
        conn.close()
        flash('Đã phân công bài kiểm tra thành công', 'success')
        return redirect(url_for('assign_test'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, title FROM tests')
    tests = c.fetchall()
    c.execute('SELECT username, name FROM users WHERE role = "STUDENT"')
    students = c.fetchall()
    conn.close()

    return render_template('assign_test.html', tests=tests, students=students)

###### Trang chung
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check credentials against the database
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (email, password))
        user = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn
        
        if user:
            role = user[5]  # Assume 'role' is at index 5 in the tuple (adjust index based on your schema)
            
            # Logging in activity
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
            signin_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO login_activity (EMAIL, LOGIN_TIME) VALUES (?, ?)", (email, signin_time))
            conn.commit()
            
            session['user_email'] = email
            
            # Redirect based on role
            if role == 'STUDENT':
                return redirect(url_for('dashboard'))
            elif role == 'TEACHER':
                return redirect(url_for('teacher_dashboard'))
            elif role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                msg = 'Unknown role!'
        else:
            msg = 'Incorrect username or password'
    
    return render_template('signin.html', message=msg)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

