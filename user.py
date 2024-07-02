from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'BILINGGO'
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
conn = sqlite3.connect('database.db', check_same_thread= False)

cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    name TEXT,
    phone TEXT,
    gender TEXT
    )''')
conn.commit()

cursor.execute('''CREATE TABLE IF NOT EXISTS LOGIN_RECORD(
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    EMAIL TEXT,
    TIMESTAMP INTEGER)''')
conn.commit()
cursor.execute("DELETE FROM USERS")
conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

# def home():
#     return render_template('index.html')
@app.route('/notifications/read/<int:notification_id>')
def mark_notification_read(notification_id):
    user_id = session.get('user_id')
    
    if user_id is None:
        return redirect(url_for('signin'))
    
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('UPDATE user_notifications SET is_read = 1 WHERE user_id = ? AND notification_id = ?', (user_id, notification_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/notifications/unread_count')
def unread_count():
    user_id = session.get('user_id')
    
    if user_id is None:
        return {'count': 0}
    
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM user_notifications WHERE user_id = ? AND is_read = 0', (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return {'count': count}

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Here you would typically check the credentials against a database
        cursor.execute("SELECT * FROM USERS WHERE USERNAME = ? AND PASSWORD = ?",(email,password))
        row_num = len(cursor.fetchall())
        if row_num == 1:
            signin_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO LOGIN_RECORD (EMAIL, TIMESTAMP) VALUES (?,?)",(email,signin_time))
            conn.commit()
            cursor.execute("SELECT * FROM LOGIN_RECORD")
            rows = cursor.fetchall()
            print(rows)
            return redirect(url_for('dashboard'))
        else:
            print('Sign In Denied')
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
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
                           (email, password, name, phone, gender, 'STUDENT'))
            conn.commit()
            conn.close()

            # Chuyển hướng đến trang đăng nhập (signin) và thông báo thành công
            return render_template('signin.html', message='Tạo tài khoản học sinh thành công')

        else:
            msg = 'Địa chỉ email này đã được sử dụng.'

    return render_template('signup.html', message=msg)

@app.route('/dashboard')
def dashboard():
    user_email = session.get('user_email')  # Replace with actual user email from session or login
    if not user_email:
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get notifications for the user
    cur.execute('''
    SELECT n.*, un.is_read FROM notifications n
    JOIN user_notifications un ON n.id = un.notification_id
    WHERE un.email = ?
    ORDER BY n.created_at DESC
    ''', (user_email,))
    notifications = cur.fetchall()
    
    # Count unread notifications
    cur.execute('SELECT COUNT(*) FROM user_notifications WHERE email = ? AND is_read = 0', (user_email,))
    unread_count = cur.fetchone()[0]
    
    conn.close()
    return render_template('dashboard.html', notifications=notifications, unread_count=unread_count)

@app.route('/get_notifications')
def get_notifications():
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
    SELECT n.notification_text, n.attachment_filename, n.created_at 
    FROM notifications n 
    JOIN user_notifications un ON n.id = un.notification_id 
    WHERE un.email = ? AND un.is_read = 0
    ORDER BY n.created_at DESC
    ''', (user_email,))
    notifications = cur.fetchall()

    conn.close()
    
    notifications_list = [
        {"text": n['notification_text'], "attachment": n['attachment_filename'], "created_at": n['created_at']}
        for n in notifications
    ]
    
    return jsonify(notifications_list)

@app.route('/flashcards')
def flashcards():
    return render_template('flashcards.html')

# Oxford API credentials
app_id = "cfb1f00e"
app_key = "8711ed0d4858793839ca6e2852e69b32"
base_url = "https://od-api-sandbox.oxforddictionaries.com/api/v2"

@app.route('/dictionary', methods=['GET', 'POST'])
def dictionary():
    definition = None
    if request.method == 'POST':
        word = request.form['word']
        url = f"{base_url}/entries/en-gb/{word.lower()}"
        headers = {
            "app_id": app_id,
            "app_key": app_key
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                lexical_entries = data['results'][0]['lexicalEntries']
                if lexical_entries:
                    entries = lexical_entries[0]['entries']
                    if entries:
                        senses = entries[0]['senses']
                        if senses:
                            definition = senses[0]['definitions'][0]
        else:
            definition = "No definition found or an error occurred."
    return render_template('dictionary.html', definition=definition)

@app.route('/mocktests')
def mocktests():
    return render_template('mocktests.html')


if __name__ == '__main__':
    app.run(debug=True)

conn.close()