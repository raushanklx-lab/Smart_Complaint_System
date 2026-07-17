from email.mime import image

from flask import Flask, render_template, request, redirect, flash, session, Response
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import csv
import os
import config

app = Flask(__name__)

app.config["MYSQL_HOST"] = config.MYSQL_HOST
app.config["MYSQL_USER"] = config.MYSQL_USER
app.config["MYSQL_PASSWORD"] = config.MYSQL_PASSWORD
app.config["MYSQL_DB"] = config.MYSQL_DB

app.secret_key = config.SECRET_KEY

mysql = MySQL(app)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Home Page
@app.route("/")
def home():
    return render_template("index.html")

# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect("/register")

        cur = mysql.connection.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user:
            flash("Email already exists")
            cur.close()
            return redirect("/register")

        hashed_password = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users(name,email,mobile,password)
            VALUES(%s,%s,%s,%s)
        """, (name, email, mobile, hashed_password))

        mysql.connection.commit()
        cur.close()

        flash("Registration Successful")
        return redirect("/login")

    return render_template("register.html")

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        cur.close()

        if user:

            if user[5] == "admin":

                if check_password_hash(user[4],password):

                    session["user_id"] = user[0]
                    session["name"] = user[1]
                    session["role"] = user[5]

                    return redirect("/admin_dashboard")

            else:

                if check_password_hash(user[4], password):

                    session["user_id"] = user[0]
                    session["name"] = user[1]
                    session["role"] = user[5]

                    return redirect("/dashboard")

        flash("Invalid Email or Password")

    return render_template("login.html")

# Dashboard Page
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM complaints WHERE user_id=%s",
        (session["user_id"],)
    )
    total = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM complaints WHERE user_id=%s AND status='Pending'",
        (session["user_id"],)
    )
    pending = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM complaints WHERE user_id=%s AND status='In Progress'",
        (session["user_id"],)
    )
    progress = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM complaints WHERE user_id=%s AND status='Resolved'",
        (session["user_id"],)
    )
    resolved = cur.fetchone()[0]

    cur.close()

    return render_template(
        "dashboard.html",
        name=session["name"],
        total=total,
        pending=pending,
        progress=progress,
        resolved=resolved
    )


# Logout Route
@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully")

    return redirect("/login")

#History Route
@app.route("/history")
def history():

    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT complaint_id,
               title,
               category,
               priority,
               status,
                image,
               created_at
        FROM complaints
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    complaints = cur.fetchall()

    cur.close()

    return render_template(
        "complaint_history.html",
        complaints=complaints
    )

#Profile Route
@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT name,email,mobile,role
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    user = cur.fetchone()

    cur.close()

    return render_template(
        "profile.html",
        user=user
    )

#Edit Profile Route
@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        name = request.form["name"]
        mobile = request.form["mobile"]

        cur.execute("""
            UPDATE users
            SET name=%s,
                mobile=%s
            WHERE id=%s
        """, (name, mobile, session["user_id"]))

        mysql.connection.commit()

        flash("Profile Updated Successfully")

        cur.close()

        return redirect("/profile")

    cur.execute("""
        SELECT name,email,mobile
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    user = cur.fetchone()

    cur.close()

    return render_template(
        "edit_profile.html",
        user=user
    )

# Change Password Route
@app.route("/change_password", methods=["GET", "POST"])
def change_password():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("New Password and Confirm Password do not match")
            return redirect("/change_password")

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT password FROM users WHERE id=%s",
            (session["user_id"],)
        )

        user = cur.fetchone()

        if not check_password_hash(user[0], current_password):
            cur.close()
            flash("Current Password is incorrect")
            return redirect("/change_password")

        hashed_password = generate_password_hash(new_password)

        cur.execute(
            "UPDATE users SET password=%s WHERE id=%s",
            (hashed_password, session["user_id"])
        )

        mysql.connection.commit()
        cur.close()

        flash("Password Changed Successfully")

        return redirect("/profile")

    return render_template("change_password.html")


#Admin Route
@app.route("/admin_dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "admin":
        return redirect("/dashboard")

    cur = mysql.connection.cursor()

    search = request.args.get("search", "")

    cur.execute("SELECT COUNT(*) FROM users WHERE role='user'")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM complaints")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
    progress = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cur.fetchone()[0]

    if search:

        cur.execute("""
        SELECT complaints.complaint_id,
            users.name,
            complaints.title,
            complaints.category,
            complaints.priority,
            complaints.status,
            complaints.created_at
        FROM complaints
        JOIN users
        ON complaints.user_id = users.id
        WHERE complaints.title LIKE %s
            OR complaints.category LIKE %s
        ORDER BY complaints.created_at DESC
        """, (f"%{search}%", f"%{search}%"))

    else:

        cur.execute("""
        SELECT complaints.complaint_id,
           users.name,
           complaints.title,
           complaints.category,
           complaints.priority,
           complaints.status,
           complaints.created_at
        FROM complaints
        JOIN users
        ON complaints.user_id = users.id
        ORDER BY complaints.created_at DESC
        """)

    complaints = cur.fetchall()

    cur.close()

    return render_template(
    "admin_dashboard.html",
    complaints=complaints,
    name=session["name"],
    total=total,
    pending=pending,
    progress=progress,
    resolved=resolved,
    total_users=total_users,
    search=search
)

# Update Complaint Status Route
@app.route("/update_status/<int:complaint_id>", methods=["GET", "POST"])
def update_status(complaint_id):

    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "admin":
        return redirect("/dashboard")

    if request.method == "POST":

        status = request.form["status"]

        cur = mysql.connection.cursor()

        cur.execute("""
            UPDATE complaints
            SET status=%s
            WHERE complaint_id=%s
        """, (status, complaint_id))

        mysql.connection.commit()
        cur.close()

        flash("Complaint Status Updated")

        return redirect("/admin_dashboard")

    return render_template(
        "update_status.html",
        complaint_id=complaint_id
    )

# Delete Complaint Route
@app.route("/delete_complaint/<int:complaint_id>")
def delete_complaint(complaint_id):

    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "admin":
        return redirect("/dashboard")

    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM complaints WHERE complaint_id=%s",
        (complaint_id,)
    )

    mysql.connection.commit()

    cur.close()

    flash("Complaint Deleted Successfully")

    return redirect("/admin_dashboard")

# Export Complaints Route
@app.route("/export_csv")
def export_csv():

    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "admin":
        return redirect("/dashboard")

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT complaints.complaint_id,
           users.name,
           complaints.title,
           complaints.category,
           complaints.priority,
           complaints.status,
           complaints.created_at
    FROM complaints
    JOIN users
    ON complaints.user_id = users.id
    ORDER BY complaints.created_at DESC
    """)

    complaints = cur.fetchall()
    cur.close()

    def generate():
        data = csv.writer(
            open("complaints.csv", "w", newline="", encoding="utf-8")
        )

        yield "ID,User,Title,Category,Priority,Status,Date\n"

        for row in complaints:
            yield ",".join(map(str, row)) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=complaints.csv"
        }
    )


# Complaint Route
@app.route("/complaint", methods=["GET", "POST"])
def complaint():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]
        category = request.form["category"]
        priority = request.form["priority"]
        description = request.form["description"]

        image = request.files["image"]

        filename = ""

        if image and image.filename != "":
            filename = secure_filename(image.filename)

            image.save(
                os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
                )
            )
    

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO complaints
            (user_id, title, category, description, priority, image)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            title,
            category,
            description,
            priority,
            filename
        ))

        mysql.connection.commit()
        cur.close()

        flash("Complaint Submitted Successfully")

        return redirect("/dashboard")

    return render_template("complaint_form.html")


if __name__ == "__main__":
    app.run(debug=True)