from flask import Flask, request, render_template, jsonify
import pickle
import numpy as np
import json
import sqlite3

app = Flask(__name__)

app.config.update(
    dict(SECRET_KEY="powerful secretkey", WTF_CSRF_SECRET_KEY="a csrf secret key")
)

__locations = None
__data_columns = None
model = pickle.load(open("bangalore_home_prices_model.pickle", "rb"))

def init_db():
    """Initialize the SQLite database and create a feedback table if not exists."""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()  #creates a cursor that interacts with database
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating INTEGER,
            suggestion TEXT
        )
    """) #run sql commands
    conn.commit() # Saves all changes
    conn.close() # Closes the connection to database

# Initialize the database
init_db()

def get_estimated_price(input_json):
    """Predict the price of the property."""
    try:
        loc_index = __data_columns.index(input_json['location'].lower())
    except ValueError:
        loc_index = -1
    x = np.zeros(244)
    x[0] = input_json['sqft']
    x[1] = input_json['bath']
    x[2] = input_json['bhk']
    if loc_index >= 0:
        x[loc_index] = 1
    result = round(model.predict([x])[0], 2)
    return result

def load_saved_artifacts():
    """Load model and data artifacts."""
    global __data_columns, __locations
    with open("columns.json") as f:
        __data_columns = json.loads(f.read())["data_columns"]
        __locations = __data_columns[3:]

@app.route("/")
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route("/prediction", methods=["POST"])
def prediction():
    """Handle prediction and feedback."""
    if request.method == 'POST':
        # Handle prediction
        input_json = {
            "location": request.form['sLocation'],
            "sqft": float(request.form['Squareft']),
            "bhk": int(request.form['uiBHK']),
            "bath": int(request.form['uiBathrooms'])
        }
        result = get_estimated_price(input_json)
        if result > 100:
            result = round(result / 100, 2)
            result = str(result) + ' Crore'
        else:
            result = str(result) + ' Lakhs'

        # Handle feedback
        rating = request.form.get('rating')
        suggestion = request.form.get('suggestion')
        if rating and suggestion:
            try:
                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO feedback (rating, suggestion) VALUES (?, ?)",
                    (rating, suggestion)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error saving feedback: {e}")

    return render_template('prediction.html', result=result)

@app.route("/save_feedback", methods=["POST"])
def save_feedback():
    """Save feedback to the database."""
    try:
        # Get the feedback data from the request
        data = request.get_json()
        rating = data.get('rating')
        suggestion = data.get('suggestion')

        # Insert feedback into the database
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO feedback (rating, suggestion) VALUES (?, ?)',
            (rating, suggestion)
        )
        conn.commit()
        conn.close()

        return jsonify({'message': 'Feedback saved successfully!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    print("Starting Python Flask Server")
    load_saved_artifacts()
    app.run(debug=True)