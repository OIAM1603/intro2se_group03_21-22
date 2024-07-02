from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
    return render_template('dashboard.html')
count = 0;
@app.route('/flashcards')
@app.route('/flashcards', methods=['GET', 'POST'])
def flashcards():
    if 'email' in session:
        email = session['email']
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

@app.route('/mocktests')
def mocktests():
    return render_template('mocktests.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
