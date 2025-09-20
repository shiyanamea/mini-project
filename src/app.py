import pymysql
from flask import Flask, request, jsonify, render_template, redirect, url_for, g, flash, session

import numpy as np
import joblib
import os
from werkzeug.utils import secure_filename

# Initialize Flask app..
app = Flask(__name__)
app.secret_key = "qwer"

# Function to get database connection per request
def get_db_connection():
    if 'db' not in g:
        g.db = pymysql.connect(host="localhost", user="root", password="1234", port=3306, db="shiya")
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/')
def main():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['textfield']
        password = request.form['textfield2']
        
        try:
            con = get_db_connection()
            cmd = con.cursor()
            
            # Protect against SQL injection using parameterized queries
            cmd.execute("SELECT * FROM login WHERE username=%s AND password=%s", (username, password))
            s = cmd.fetchone()

            if s:
                if s[3] == "admin":
                    return render_template("sample.html")
                elif s[3] == "user":
                    session['username'] = username # Store username in session
                    return redirect(url_for('user_dashboard'))  # Redirect to user dashboard
                else:
                    flash("Invalid user type", "error")
                    return render_template("login.html")
            else:
                flash("Invalid username or password", "error")
                return render_template("login.html")
        except Exception as e:
            flash("An error occurred. Please try again.", "error")
            print("Login error:", e)
            return render_template("login.html")
        
    return redirect(url_for('main'))

@app.route('/register')
def register():
    return render_template("reg.html")

@app.route('/register1', methods=['POST', 'GET'])
def register1():
    if request.method == 'POST':
        try:
            fn = request.form.get('fname')
            ln = request.form.get('lname')
            cont = request.form.get('contacts')
            usn = request.form.get('username')
            pwd = request.form.get('password')
            confirm_pwd = request.form.get('confirm_password')
            
            if not all([fn, ln, cont, usn, pwd, confirm_pwd]):
                flash("All fields are required", "error")
                return render_template("reg.html")
            
            # Password validation
            if len(pwd) < 8:
                flash("Password must be at least 8 characters long", "error")
                return render_template("reg.html")
            
            if not any(c.isupper() for c in pwd):
                flash("Password must contain at least one uppercase letter", "error")
                return render_template("reg.html")
            
            if not any(c.islower() for c in pwd):
                flash("Password must contain at least one lowercase letter", "error")
                return render_template("reg.html")
            
            if not any(c.isdigit() for c in pwd):
                flash("Password must contain at least one number", "error")
                return render_template("reg.html")
            
            if not any(c in "!@#$%^&*" for c in pwd):
                flash("Password must contain at least one special character (!@#$%^&*)", "error")
                return render_template("reg.html")
            
            if pwd != confirm_pwd:
                flash("Passwords do not match", "error")
                return render_template("reg.html")
            
            try:
                con = get_db_connection()
                cmd = con.cursor()

                # Check if username already exists
                cmd.execute("SELECT * FROM login WHERE username=%s", (usn,))
                if cmd.fetchone():
                    flash("Username already exists", "error")
                    return render_template("reg.html")

                # Insert user into login table
                try:
                    cmd.execute("INSERT INTO login (username, password, type) VALUES (%s, %s, %s)", (usn, pwd, 'user'))
                except Exception as e:
                    print("Login table insert error:", str(e))
                    flash(f"Error creating login account: {str(e)}", "error")
                    return render_template("reg.html")
                
                # Insert user details into user table
                try:
                    cmd.execute("INSERT INTO user (first_name, last_name, contact, username) VALUES (%s, %s, %s, %s)", 
                              (fn, ln, cont, usn))
                except Exception as e:
                    print("User table insert error:", str(e))
                    flash(f"Error creating user profile: {str(e)}", "error")
                    return render_template("reg.html")
                
                con.commit()
                flash("Registration successful! Please login.", "success")
                return redirect(url_for('main'))
                
            except Exception as e:
                print("Database connection error:", str(e))
                flash(f"Database connection error: {str(e)}", "error")
                return render_template("reg.html")
            
        except Exception as e:
            print("Registration error:", str(e))
            flash(f"Registration error: {str(e)}", "error")
            return render_template("reg.html")
    
    return render_template("reg.html")

@app.route('/user_dashboard')
def user_dashboard():
    if 'username' not in session:
        return redirect(url_for('main'))
    username = session['username']
    con = get_db_connection()
    cmd = con.cursor()
    # Get user info
    cmd.execute("SELECT * FROM user WHERE username=%s", (username,))
    user = cmd.fetchone()
    # Get todos
    cmd.execute("SELECT * FROM todo WHERE user_id=(SELECT id FROM user WHERE username=%s)", (username,))
    todos = cmd.fetchall()
    return render_template("user_dashboard.html", user=user, todos=todos)

@app.route('/todo/create', methods=['POST'])
def create_todo():
    if 'username' not in session:
        return redirect(url_for('main'))
    title = request.form.get('title')
    description = request.form.get('description')
    username = session['username']
    con = get_db_connection()
    cmd = con.cursor()
    cmd.execute("SELECT id FROM user WHERE username=%s", (username,))
    user_id = cmd.fetchone()[0]
    cmd.execute("INSERT INTO todo (user_id, title, description) VALUES (%s, %s, %s)", (user_id, title, description))
    con.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/todo/update/<int:todo_id>', methods=['POST'])
def update_todo(todo_id):
    if 'username' not in session:
        return redirect(url_for('main'))
    title = request.form.get('title')
    description = request.form.get('description')
    status = request.form.get('status')
    con = get_db_connection()
    cmd = con.cursor()
    cmd.execute("UPDATE todo SET title=%s, description=%s, status=%s WHERE id=%s", (title, description, status, todo_id))
    con.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/todo/delete/<int:todo_id>', methods=['POST'])
def delete_todo(todo_id):
    if 'username' not in session:
        return redirect(url_for('main'))
    con = get_db_connection()
    cmd = con.cursor()
    cmd.execute("DELETE FROM todo WHERE id=%s", (todo_id,))
    con.commit()
    return redirect(url_for('user_dashboard'))

@app.route('/profile/view')
def view_profile():
    if 'username' not in session:
        return redirect(url_for('main'))
    username = session['username']
    con = get_db_connection()
    cmd = con.cursor()
    cmd.execute("SELECT * FROM user WHERE username=%s", (username,))
    user = cmd.fetchone()
    return render_template("profile.html", user=user)

UPLOAD_FOLDER = os.path.join('static', 'profile_photos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('main'))
    username = session['username']
    con = get_db_connection()
    cmd = con.cursor()
    if request.method == 'POST':
        fn = request.form.get('fname')
        ln = request.form.get('lname')
        cont = request.form.get('contacts')
        photo = request.files.get('photo')
        photo_filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_filename = f"{username}_{filename}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            photo.save(photo_path)
            cmd.execute("UPDATE user SET first_name=%s, last_name=%s, contact=%s, photo=%s WHERE username=%s", (fn, ln, cont, photo_filename, username))
        else:
            cmd.execute("UPDATE user SET first_name=%s, last_name=%s, contact=%s WHERE username=%s", (fn, ln, cont, username))
        con.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('user_dashboard'))
    else:
        cmd.execute("SELECT * FROM user WHERE username=%s", (username,))
        user = cmd.fetchone()
        return render_template("edit_profile.html", user=user)

@app.route('/reset_password', methods=['POST'])
def reset_password():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            phone = request.form.get('phone')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not all([username, phone, new_password, confirm_password]):
                flash("All fields are required", "error")
                return redirect(url_for('main'))
            
            if new_password != confirm_password:
                flash("Passwords do not match", "error")
                return redirect(url_for('main'))
            
            con = get_db_connection()
            cmd = con.cursor()
            
            # Verify username and phone number
            cmd.execute("SELECT * FROM user WHERE username=%s AND contact=%s", (username, phone))
            user = cmd.fetchone()
            
            if not user:
                flash("Invalid username or phone number", "error")
                return redirect(url_for('main'))
            
            # Update password
            cmd.execute("UPDATE login SET password=%s WHERE username=%s", (new_password, username))
            con.commit()
            
            flash("Password reset successful! Please login with your new password.", "success")
            return redirect(url_for('main'))
            
        except Exception as e:
            print("Password reset error:", str(e))
            flash("An error occurred while resetting your password. Please try again.", "error")
            return redirect(url_for('main'))
    
    return redirect(url_for('main'))

if __name__ == '__main__':
    app.run(debug=True)
