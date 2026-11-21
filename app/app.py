from flask import render_template_string
from flask import Flask, render_template, request, redirect, url_for, session
from database import initialize_database, get_db

app = Flask(__name__)
app.secret_key = "smarthome-lab-secret"

# Initialize database
initialize_database()


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        connection = get_db()

        # Intentionally vulnerable SQL query for the SQL injection challenge
        query = (
            "SELECT * FROM users "
            f"WHERE username = '{username}' AND password = '{password}'"
        )

        user = connection.execute(query).fetchone()
        connection.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    connection = get_db()
    devices = connection.execute("SELECT * FROM devices").fetchall()
    connection.close()

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session["role"],
        devices=devices
    )

@app.route("/temperature", methods=["GET", "POST"])
def temperature():
    if "username" not in session:
        return redirect(url_for("login"))

    message = None

    if request.method == "POST":
        value = request.form.get("temperature", "")

        # Intentionally vulnerable SSTI for the isolated Boot2Root lab
        template = "Temperature updated to: " + value
        message = render_template_string(template)

    return render_template("temperature.html", message=message)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
