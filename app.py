from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
import requests
import sqlite3
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = 'BILINGGO'
conn = sqlite3.connect('database.db', check_same_thread= False)
DATABASE = 'database.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, check_same_thread=False)
    return g.db

@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()


cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS USERS")
conn.commit()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    name TEXT,
    phone TEXT,
    gender TEXT,
    role TEXT
    )''')
conn.commit()

cursor.execute("DROP TABLE IF EXISTS FLASHCARD")
conn.commit()


cursor.execute('''CREATE TABLE IF NOT EXISTS FLASHCARD(
               ID INTEGER PRIMARY KEY AUTOINCREMENT,
               EMAIL TEXT,
               THEME TEXT,
               WORD TEXT,
               PRONUNCIATION TEXT,
               FORM TEXT,
               MEANING TEXT)''')

def get_start_and_end_of_week():
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    start_of_week = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
    end_of_week = datetime(end_of_week.year, end_of_week.month, end_of_week.day, 23, 59, 59)
    print('START ')
    print(start_of_week)
    print('END ')
    print(end_of_week)
    return start_of_week, end_of_week

def count_logins_each_day_of_week(signed_in_email):
    start_of_week, end_of_week = get_start_and_end_of_week()
    cursor.execute('''
        SELECT TIMESTAMP FROM LOGIN_RECORD
        WHERE TIMESTAMP BETWEEN ? AND ? AND EMAIL = ?
    ''', (start_of_week.timestamp(), end_of_week.timestamp(),signed_in_email))

    conn.commit()

    login_records = cursor.fetchall()
    print('test date ')
    print(login_records)

    # Initialize a list to count logins for each day of the week
    login_count = [0] * 7  # 7 days in a week

    # Count logins for each day
    for (timestamp,) in login_records:
        login_date = datetime.fromtimestamp(timestamp)
        day_index = (login_date - start_of_week).days
        if 0 <= day_index < 7:
            login_count[day_index] += 1

    return login_count

cursor.execute('''CREATE TABLE IF NOT EXISTS LOGIN_RECORD(
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    EMAIL TEXT,
    TIMESTAMP INTEGER)''')
conn.commit()

cursor.execute("INSERT INTO USERS VALUES ('admin1@outlook.com','1','ADMIN','113','MALE','ADMIN')")
conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

count_login = []
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Here you would typically check the credentials against a database
        cursor.execute("SELECT * FROM USERS WHERE USERNAME = ? AND PASSWORD = ?",(email,password))
        row_num = len(cursor.fetchall())
        if row_num == 1:
            session['email'] = email
            signin_time = datetime.utcnow().timestamp()
            cursor.execute("INSERT INTO LOGIN_RECORD (EMAIL, TIMESTAMP) VALUES (?,?)",(email,signin_time))
            conn.commit()
            cursor.execute("SELECT * FROM LOGIN_RECORD")
            conn.commit()
            rows = cursor.fetchall()
            print(rows)
            global count_login
            count_login = count_logins_each_day_of_week(email)
            print(count_login)
            cursor.execute("SELECT ROLE FROM USERS WHERE USERNAME = ?",(email,))
            role = cursor.fetchone()
            
            if role[0] == 'ADMIN':
                return redirect(url_for('admin_dashboard'))
            if role[0] == 'STUDENT':
                return redirect(url_for('dashboard'))
        
        conn.commit()
        cursor.execute("SELECT * FROM USERS WHERE USERNAME = ?",(email,))
        conn.commit()
        row_num = len(cursor.fetchall())
        if row_num == 0:
            msg = 'This email has not been registered!'
        else:
            msg = 'Wrong password!'

    return render_template('signin.html',message = msg)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        gender = request.form['gender']
        # Here you would typically save the user details to a database
        # For this example, we'll just redirect to the home page
        cursor.execute("SELECT * FROM USERS WHERE USERNAME = ?", (email,))
        count = len(cursor.fetchall())
        if(count == 0):
            cursor.execute("INSERT INTO USERS VALUES (?,?,?,?,?,?)", (email,password,name,phone,gender,'STUDENT'))
            return redirect(url_for('signin'))
        else:
            msg = 'This email address has been used'
    return render_template('signup.html',message = msg)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', logincount = count_login)

@app.route('/flashcards')
@app.route('/flashcards', methods=['GET', 'POST'])
def flashcards():
    db = get_db()
    cursor = db.cursor()
    if 'email' in session:
        email = session['email']
        if request.method == 'POST':
            print(request.form)
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
            db.commit()
            
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
                db.commit()
                theme = [row[0] for row in cursor.fetchall()]
                cursor.execute('SELECT THEME, WORD, PRONUNCIATION, FORM, MEANING FROM FLASHCARD WHERE EMAIL = ?',(email,))
                flashcards = cursor.fetchall()
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

@app.route('/mocktests')
def mocktests():
    return render_template('mocktests.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', admin_name="Admin Name", logincount = count_login)

@app.route('/admin_create_notification', methods=['POST'])
def admin_create_notification():
    # Xử lý logic tạo thông báo ở đây
    pass
    if 'email' in session:
        email = session['email']
        if request.method == 'POST':
            vocabulary = request.form['vocabulary']
            print(vocabulary)
            pronunciation = request.form['pronunciation']
            form = request.form['form']
            meaning = request.form['meaning']
            cursor.execute("INSERT INTO FLASHCARDS (EMAIL, WORD, PRONUNCIATION, FORM, MEANING) VALUES (?,?,?,?,?)",(email, vocabulary,pronunciation,form,meaning))
            conn.commit
            cursor.execute("SELECT * FROM FLASHCARDS")
            print(cursor.fetchall())
        return render_template('flashcards.html', email = email)
    else:
        return redirect(url_for('signin'))
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/admin_view_account')
def admin_view_account():
    conn = get_db_connection()
    students = conn.execute('SELECT name FROM users WHERE role = "STUDENT"').fetchall()
    teachers = conn.execute('SELECT name FROM users WHERE role = "TEACHER"').fetchall()
    recent_accounts = conn.execute('SELECT name, role FROM users').fetchall()
    conn.close()
    return render_template('admin_view_account.html', students=students, teachers=teachers, recent_accounts=recent_accounts)

@app.route('/admin_report')
def admin_report():
    return render_template('admin_report.html')

# Kiểm tra và khởi tạo cơ sở dữ liệu nếu chưa tồn tại
def init_db():
    if not os.path.exists('database.db'):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT NOT NULL,  
                password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

@app.route('/admin_create_account', methods=['GET', 'POST'])
def admin_create_account():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = 'TEACHER'

        # Thêm thông tin người dùng vào cơ sở dữ liệu
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO users (name, email, role) VALUES (?, ?, ?)
        ''', (name, email, role))
        conn.commit()
        conn.close()

        return 'Tài khoản đã được tạo thành công!'  # Hoặc có thể redirect đến một trang thông báo khác

    return render_template('admin_create_account.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
