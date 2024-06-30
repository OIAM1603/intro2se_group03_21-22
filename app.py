<<<<<<< HEAD
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
app = Flask(__name__)
=======
from flask import Flask, render_template, request, redirect, url_for, session
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'BILINGGO'
conn = sqlite3.connect('database.db', check_same_thread= False)

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

cursor.execute('''CREATE TABLE IF NOT EXISTS FLASHCARD(
               ID INTEGER PRIMARY KEY AUTOINCREMENT,
               EMAIL TEXT,
               WORD TEXT,
               PRONUNCIATION TEXT,
               FORM TEXT,
               MEANING TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS LOGIN_RECORD(
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    EMAIL TEXT,
    TIMESTAMP INTEGER)''')
conn.commit()
cursor.execute("DELETE FROM USERS")
conn.commit()
>>>>>>> 853d3791c430fbd014aa5ab8377e2d60b0deba73

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
<<<<<<< HEAD
=======
    msg = ''
>>>>>>> 853d3791c430fbd014aa5ab8377e2d60b0deba73
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Here you would typically check the credentials against a database
<<<<<<< HEAD
        # For this example, we'll assume the login is successful
        return redirect(url_for('dashboard'))
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
=======
        cursor.execute("SELECT * FROM USERS WHERE USERNAME = ? AND PASSWORD = ?",(email,password))
        row_num = len(cursor.fetchall())
        if row_num == 1:
            session['email'] = email
            test = session['email']
            print('Test ' + test);
            signin_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO LOGIN_RECORD (EMAIL, TIMESTAMP) VALUES (?,?)",(email,signin_time))
            conn.commit()
            cursor.execute("SELECT * FROM LOGIN_RECORD")
            rows = cursor.fetchall()
            print(rows)
            return redirect(url_for('dashboard'))
        
        cursor.execute("SELECT * FROM USERS WHERE USERNAME = ?",(email,))
        row_num = len(cursor.fetchall())
        if row_num == 0:
            msg = 'This email has not been registered!'
        else:
            msg = 'Wrong password!'

    return render_template('signin.html',message = msg)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
>>>>>>> 853d3791c430fbd014aa5ab8377e2d60b0deba73
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        gender = request.form['gender']
        # Here you would typically save the user details to a database
        # For this example, we'll just redirect to the home page
<<<<<<< HEAD
        return redirect(url_for('home'))
    return render_template('signup.html')
=======
        cursor.execute("SELECT * FROM USERS WHERE USERNAME = ?", (email,))
        count = len(cursor.fetchall())
        if(count == 0):
            cursor.execute("INSERT INTO USERS VALUES (?,?,?,?,?,?)", (email,password,name,phone,gender,'STUDENT'))
            return redirect(url_for('signin'))
        else:
            msg = 'This email address has been used'
    return render_template('signup.html',message = msg)
>>>>>>> 853d3791c430fbd014aa5ab8377e2d60b0deba73

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/flashcards')
def flashcards():
<<<<<<< HEAD
    return render_template('flashcards.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', admin_name="Admin Name")


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/admin_view_account')
def admin_view_account():
    conn = get_db_connection()
    students = conn.execute('SELECT name FROM users WHERE role = "student"').fetchall()
    teachers = conn.execute('SELECT name FROM users WHERE role = "teacher"').fetchall()
    recent_accounts = conn.execute('SELECT name, role FROM users ORDER BY created_at DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('admin_view_account.html', students=students, teachers=teachers, recent_accounts=recent_accounts)

@app.route('/admin_report')
def admin_report():
    return render_template('admin_report.html')

@app.route('/admin_create_account', methods=['GET', 'POST'])
def admin_create_account():
    if request.method == 'POST':
        # Xử lý logic tạo tài khoản ở đây
        pass
    return render_template('admin_create_account.html')

@app.route('/admin_create_notification', methods=['POST'])
def admin_create_notification():
    # Xử lý logic tạo thông báo ở đây
    pass
=======
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

@app.route('/admin')
def admin():
    return render_template('admin.html')
>>>>>>> 853d3791c430fbd014aa5ab8377e2d60b0deba73

if __name__ == '__main__':
    app.run(debug=True)
