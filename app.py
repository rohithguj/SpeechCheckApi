import os
import sqlite3
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from nltk.corpus import cmudict

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# Initialize CMU dictionary
d = cmudict.dict()

# Function to get all possible phonetic sounds
def get_unique_phonetics():
    unique_phonetics = set()
    for word, phonetic_list in d.items():
        for phonetic_sequence in phonetic_list:
            unique_phonetics.update(phonetic_sequence)
    return sorted(unique_phonetics)

# Database connection
def connect_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# Database initialization
def init_db():
    if not os.path.exists("database.db"):
        with connect_db() as conn:
            cursor = conn.cursor()
            # Create users table with UUID
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    password TEXT NOT NULL
                )
            """)
            
            # Create phonetics table with user_id as TEXT
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS phonetics (
                    user_id TEXT PRIMARY KEY,  -- UUID stored as TEXT
                    {", ".join([f"{sound} INTEGER DEFAULT 0" for sound in get_unique_phonetics()])},
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()

# Call the init_db function to initialize tables if they don't exist
init_db()

# Signup endpoint
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    with connect_db() as conn:
        cursor = conn.cursor()
        try:
            # Insert user into users table
            cursor.execute("""
                INSERT INTO users (email, phone, password) 
                VALUES (?, ?, ?)
            """, (email, phone, hashed_password))
            user_id = cursor.lastrowid

            # Insert phonetics data for new user, initializing all phonetics to 0
            phonetic_values = ", ".join(["0"] * len(get_unique_phonetics()))
            cursor.execute(f"""
                INSERT INTO phonetics (user_id, {", ".join(get_unique_phonetics())})
                VALUES (?, {phonetic_values})
            """, (user_id,))
            
            conn.commit()
            return jsonify({"message": "User registered successfully!"}), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "User with this email already exists."}), 409

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            return jsonify({"message": "Login successful!"}), 200
        return jsonify({"error": "Invalid email or password."}), 401

# Phonetic score update endpoint
@app.route('/phonetics/update', methods=['POST'])
def update_phonetics():
    data = request.json
    email = data.get('email')
    phonetic = data.get('phonetic')
    
    with connect_db() as conn:
        cursor = conn.cursor()
        
        # Retrieve user ID from email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user:
            # Update the phonetic score for the user
            cursor.execute(f"""
                UPDATE phonetics
                SET {phonetic} = {phonetic} + 1
                WHERE user_id = ?
            """, (user['id'],))
            conn.commit()
            return jsonify({"message": f"Phonetic '{phonetic}' score updated successfully!"}), 200
        return jsonify({"error": "User not found."}), 404

if __name__ == '__main__':
    app.run(debug=True)

