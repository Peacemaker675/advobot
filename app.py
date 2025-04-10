from flask import Flask,redirect, render_template, request, flash
from flask_session import Session
import re
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import *
import psycopg2
import os
import urllib.parse as up

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = "1234"
Session(app)

up.uses_netloc.append("postgres")
url = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(url)
conn.autocommit = True
curr = conn.cursor()




@app.route("/")
def index():
    if session.get("user_id"):
        lawyer_id = session["user_id"]
        query = """
            SELECT c.case_id, c.case_number
            FROM cases c
            JOIN lawyers_cases lc ON c.case_id = lc.case_id
            WHERE lc.lawyer_id = %s;
        """
        curr.execute(query, (lawyer_id,))
        cases = curr.fetchall()
        print(cases)
        return render_template("home.html",cases = cases)
    else:
        return render_template("index.html")

@app.route("/register", methods = ['GET','POST'])
def register():
    try:
        curr.execute('SELECT court_name FROM courts')
        court_names = []
        for row in curr.fetchall():
            words = row[0].split()
            words.insert(1,"High")
            court_names.append(' '.join(words))

        if request.method == 'POST':
            if not request.form.get("username"):
                flash("Invalid username","danger")
                return render_template("register.html",court_names = court_names)
            elif not request.form.get("email") or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",request.form.get("email")):
                flash("Invalid Email",'danger')
                return render_template("register.html",court_names = court_names)
            elif not request.form.get('court'):
                flash("please select court","warning")
                return render_template("register.html",court_names = court_names)
            elif not request.form.get('password') or len(request.form.get('password')) < 8:
                flash("Invalid password","danger")
                return render_template("register.html",court_names = court_names)
            else:
                name  = request.form.get("username")
                email = request.form.get("email")
                curr.execute("SELECT * FROM lawyers WHERE email = %s",(email,))
                rows = curr.fetchall()
                if len(rows) == 1 :
                    flash("Email already in use","warning")
                    return render_template("register.html",court_names = court_names)
                curr.execute("SELECT court_id FROM courts WHERE court_name = %s", (request.form.get("court"),))
                court = curr.fetchone()[0]
                password = generate_password_hash(request.form.get("password"))
                curr.execute("INSERT INTO lawyers(name,email,court_id,password) VALUES(%s,%s,%s,%s)",(name,email,court,password))
                curr.execute("SELECT lawyer_id FROM lawyers WHERE email = %s",(email,))
                l_id = curr.fetchall()[0][0]
                session["user_id"] = l_id
                return redirect("/")
        else:
            return render_template("register.html",court_names = court_names)
    except:
        flash("Something Went Wrong","danger")
        return redirect("/")

@app.route("/login", methods = ['GET','POST'])
def login():
    try:
        session.clear()
        if request.method == 'POST':
            if not request.form.get("email"):
                flash("Invalid Email","danger")
                return render_template("login.html")
            elif not request.form.get("password"):
                flash("Invalid password","danger")
                return render_template("login.html")
            else:
                curr.execute("SELECT * FROM lawyers WHERE email = %s",(request.form.get("email"),))
                row = curr.fetchall()
                if len(row) != 1 or not check_password_hash(row[0][4],request.form.get("password")):
                    flash("Invalid Password","danger")
                    return render_template("login.html")
                session["user_id"] = row[0][0]
                return redirect("/")
        else:
            return render_template("login.html")
    except:
        flash("Something went wrong","danger")
        return render_template("/")
    
@login_required
@app.route("/add_case", methods = ['POST'])
def add_case():
    try:
        lawyer_id = session["user_id"]
        case_number  = request.form.get('case_id')
        curr.execute("SELECT court_id FROM lawyers WHERE lawyer_id = %s",(lawyer_id,))
        rows = curr.fetchall()
        court_id = rows[0]
        curr.execute("INSERT INTO cases(case_number,court_id) VALUES(%s,%s)",(case_number,court_id))
        curr.execute("SELECT case_id FROM cases WHERE case_number = %s AND court_id = %s",(case_number,court_id))
        rows = curr.fetchall()
        case_id = rows[0]
        curr.execute("INSERT INTO lawyers_cases(lawyer_id,case_id) VALUES(%s,%s)",(lawyer_id,case_id))
        return redirect("/")
    except:
        flash("Something went wrong","danger")
        return redirect("/")

@login_required
@app.route('/delete_case/<int:case_id>', methods = ['POST'])
def delete_case(case_id):
    try:
        lawyer_id = session["user_id"]
        curr.execute("DELETE FROM lawyers_cases WHERE lawyer_id = %s AND case_id = %s",(lawyer_id,case_id))
        curr.execute("SELECT * FROM lawyers_cases WHERE case_id = %s",(case_id,))
        rows = curr.fetchall()
        if len(rows) == 0:
            curr.execute("DELETE FROM cases WHERE case_id = %s", (case_id,))
        return redirect("/")
    except:
        flash("Something went wrong","danger")
        return redirect("/")

@login_required
@app.route('/news')
def get_news():
    try:
        curr.execute("SELECT c.court_name FROM courts c JOIN lawyers l ON l.court_id = c.court_id WHERE lawyer_id = %s", (session["user_id"],))
        court = curr.fetchall()[0][0]
        news_articles = get_court_news(court)
        return render_template("news.html", news_articles=news_articles, court = court)
    except:
        flash("Something went wrong","danger")
        return redirect("/")

@login_required
@app.route("/delete-account", methods=["POST"])
def delete_account():
    user_id = session.get("user_id")
    password = request.form.get("password")

    curr.execute("SELECT password FROM lawyers WHERE lawyer_id = %s", (user_id,))
    user_pass = curr.fetchall()[0][0]
    if check_password_hash(user_pass,password):
        curr.execute("DELETE FROM lawyers WHERE lawyer_id = %s",(user_id,))
        conn.commit()
        curr.execute("DELETE FROM lawyers_cases WHERE lawyer_id = %s",(user_id,))
        conn.commit()
        session.clear()
        flash("Account Deleted Successfully !","success")
        return redirect("/")
    else:
        flash("Please check your password","danger")
        return redirect(request.referrer or "/")

@login_required
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
        
