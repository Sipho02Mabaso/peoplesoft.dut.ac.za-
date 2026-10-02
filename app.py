import hmac
import json
import os
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, send_from_directory, session

from users import USERS

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-before-real-use")


def current_user():
    """Return the logged-in user's public data (never the password), or None."""
    uid = session.get("user_id")
    user = USERS.get(uid)
    if not user:
        return None
    return {"userId": uid, "name": user["name"], "history": user["history"]}


def send_page(filename):
    response = send_from_directory(BASE_DIR, filename)
    response.headers["Cache-Control"] = "no-store"
    return response


# ---------- pages ----------
@app.get("/")
@app.get("/dut-login.html")
def login_page():
    return send_page("dut-login.html")


@app.get("/dut-homepage.html")
def homepage():
    return send_page("dut-homepage.html") if current_user() else redirect("/")


@app.get("/dut-residence-status.html")
def residence_page():
    return send_page("dut-residence-status.html") if current_user() else redirect("/")


# ---------- the pages load this as <script src="users.js"> ----------
JS_TEMPLATE = """
const CURRENT_USER = __USER__;
const DUTAuth = {
  current() { return CURRENT_USER; },
  require() { if (!CURRENT_USER) location.href = "/"; return CURRENT_USER; },
  logout() {
    fetch("/api/logout", { method: "POST" }).finally(() => { location.href = "/"; });
  }
};
"""


@app.get("/users.js")
def users_js():
    js = JS_TEMPLATE.replace("__USER__", json.dumps(current_user()))
    return Response(js, mimetype="application/javascript", headers={"Cache-Control": "no-store"})


@app.get("/letter/<user_id>.pdf")
def checkin_letter(user_id):
    user = current_user()
    if not user:
        return redirect("/")
    if user_id != user["userId"]:
        return "Not your letter", 403
    return send_from_directory(BASE_DIR / "letter", f"{user_id}.pdf")


# ---------- API ----------
@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("userId", "")).strip()
    password = str(data.get("password", ""))
    user = USERS.get(user_id)
    if user is None or not hmac.compare_digest(user["password"].encode(), password.encode()):
        return jsonify(ok=False), 401
    session.clear()
    session["user_id"] = user_id
    return jsonify(ok=True)


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify(ok=True)


if __name__ == "__main__":
    # HOST=0.0.0.0 lets a phone on the same Wi-Fi open the site
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=5000, debug=True)