from flask import Flask, render_template, request, redirect, url_for
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Here you would typically check the credentials against a database
        # For this example, we'll assume the login is successful
        return redirect(url_for('dashboard'))
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        gender = request.form['gender']
        # Here you would typically save the user details to a database
        # For this example, we'll just redirect to the home page
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

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
