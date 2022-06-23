import pymongo, os, sys, dotenv, random
from flask import *
import hashlib
dotenv.load_dotenv(".env")
# init app
app = Flask(__name__)
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client["shorting"]


def validate_login(uid):
    cursor = list(db.users.find())
    for a in cursor:
        if str(a["_id"]) == uid:
            return True
    return False


def user_from_id(uid):
    cursor = list(db.users.find())
    for a in cursor:
        if str(a["_id"]) == uid:
            return a["user"]
    return None

@app.route("/")
def main():
    logged = request.cookies.get("login_token") or False
    print(request.cookies)
    resp = make_response(render_template("index.html", login=logged))
    #resp.set_cookie('', user)
    return resp

@app.route("/register")
def register_ui():
    return render_template("register.html")

@app.route("/mkregister", methods=["POST"])
def register_user():
    user = request.form.get("username")
    passwd = request.form.get("password")
    passw = hashlib.sha256(passwd.encode('utf-8')).hexdigest()
    print([user, passwd])
    if db.users.find_one({"user": user}):
        resp = make_response(render_template("error.html", error="existingusr"))
        return resp
    else:
        db.users.insert_one({"user": user, "passwd": passw})
        resp = make_response(render_template("index.html", login=True))
        return redirect("/login")

@app.route("/login")
def login_ui():
    return render_template("login.html")

@app.route("/mklogin", methods=["POST"])
def login_user():
    user = request.form.get("username")
    passwd = request.form.get("password")
    if not db.users.find_one({"user": user}):
        return redirect("/login")
    passw = hashlib.sha256(passwd.encode('utf-8')).hexdigest()
    match = db.users.find_one({"user": user, "passwd": passw})
    if len(match) == 0:
        return redirect("/login")
    resp = make_response(redirect("/"))
    print(str(match))
    resp.set_cookie("login_token", str(match["_id"]))
    return resp

@app.route("/short", methods=["POST", "GET"])
def short():
    if request.method == "GET":
        return redirect("/")
    
    
    slug = request.form["slug"] or "".join(random.sample("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", 5))
    cursor = list(db.urls.find())
    logged_in = validate_login(request.cookies.get("login_token")) or False
    user = request.cookies.get("login_token") if logged_in else None
    print(cursor)
    duplicates = [x for x in cursor if x["short"] == slug]
    print(duplicates)
    if not len(duplicates) == 0:
        return ("<h1>This slug already exists</h1><a href='/'>Go back</a>")
    password = request.form["password"] or None
    print(password)
    values = {"url": request.form.get("url"), "short": slug, "password": password, "user": user}
    db.urls.insert_one(values)
    return f"<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bulma@0.9.3/css/bulma.min.css'><p>Link shortened to <a href='/{slug}'>{request.base_url[:-5]+slug}</a></p><a href='/'>Go back</a>"

@app.route("/<slug>")
def redirect_to_shorted(slug):

    cursor = list(db.urls.find())
    link = [x for x in cursor if x["short"] == slug]
    if len(link) == 0:
        return render_template("error.html", error="nolink")
    link = link[0]
    if link["password"]:
        return render_template("password.html", slug=slug)
    return redirect(link["url"])

@app.route("/redirect/<slug>", methods=["POST"])
def redirect_to_slug(slug):
    cursor = list(db.urls.find())
    link = [x for x in cursor if x["short"] == slug]
    if len(link) == 0:
        return '<h1>Link not found</h1><a href=\'/\'>Go back</a>'
    link = link[0]
    if link["password"]:
        if request.form["password"] == link["password"]:
            return redirect(link["url"])
        else:
            return render_template("error.html", error="password")
    else:
        return redirect(link["url"])


@app.route("/dashboard")
def dash():
    logged = validate_login(request.cookies.get("login_token"))
    if not logged:
        return redirect("/login")
    oof = list(db.urls.find({"user": request.cookies.get("login_token")}))
               
    print(oof)
    return render_template("dashboard.html", name=user_from_id(request.cookies.get("login_token")), links=oof)

@app.route("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.set_cookie("login_token", "")
    return resp

print("Running on port 5000")
from waitress import serve
serve(app, host="0.0.0.0", port=5000)
