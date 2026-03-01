from flask import Flask, request, redirect, session
import sqlite3
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_NAME = "database.db"

# -----------------------------
# データベース初期化
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        class_name TEXT,
        max_lessons INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        class_name TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------
# 登録
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except:
            return "ユーザー名が既に存在します"
        finally:
            conn.close()

        return redirect("/login")

    return """
    <h1>新規登録</h1>
    <form method="POST">
        <input name="username" placeholder="ユーザー名"><br>
        <input name="password" type="password" placeholder="パスワード"><br>
        <button type="submit">登録</button>
    </form>
    """

# -----------------------------
# ログイン
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return "ログイン失敗"

    return """
    <h1>ログイン</h1>
    <form method="POST">
        <input name="username" placeholder="ユーザー名"><br>
        <input name="password" type="password" placeholder="パスワード"><br>
        <button type="submit">ログイン</button>
    </form>
    """

# -----------------------------
# ログアウト
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -----------------------------
# メイン画面
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    conn = get_db()

    # 出席登録
    if request.method == "POST" and "attend" in request.form:
        conn.execute(
            "INSERT INTO attendance (user_id, class_name, date) VALUES (?, ?, ?)",
            (user_id, request.form["attend"], date.today())
        )
        conn.commit()

    # 授業追加
    if request.method == "POST" and "new_class" in request.form:
        conn.execute(
            "INSERT INTO lessons (user_id, class_name, max_lessons) VALUES (?, ?, ?)",
            (user_id, request.form["new_class"], request.form["max_lessons"])
        )
        conn.commit()

    # 授業削除
    if request.method == "POST" and "delete_class" in request.form:
        class_name = request.form["delete_class"]
        conn.execute("DELETE FROM lessons WHERE user_id=? AND class_name=?", (user_id, class_name))
        conn.execute("DELETE FROM attendance WHERE user_id=? AND class_name=?", (user_id, class_name))
        conn.commit()

    # 出席削除
    if request.method == "POST" and "delete_attendance" in request.form:
        conn.execute("DELETE FROM attendance WHERE id=?", (request.form["delete_attendance"],))
        conn.commit()

    # ソート
    order = request.args.get("order", "DESC")
    attendance = conn.execute(
        f"SELECT * FROM attendance WHERE user_id=? ORDER BY date {order}",
        (user_id,)
    ).fetchall()

    lessons = conn.execute("SELECT * FROM lessons WHERE user_id=?", (user_id,)).fetchall()

    html = """
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <h1>出席管理アプリ</h1>
    <a href='/logout'>ログアウト</a>
    """

    # 出席ボタン＋回数表示
    html += "<h2>授業一覧</h2>"

    for lesson in lessons:

        count = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE user_id=? AND class_name=?",
            (user_id, lesson["class_name"])
        ).fetchone()[0]

        remaining = lesson["max_lessons"] - count
        color = "red" if remaining <= 0 else "black"

        html += f"""
        <div style="margin-bottom:10px;">
            <strong>{lesson['class_name']}</strong><br>
            出席 {count}回 / 上限 {lesson['max_lessons']}回<br>
            <span style="color:{color};">
                残り {remaining} 回
            </span><br>
            <form method="POST" style="display:inline;">
                <button name="attend" value="{lesson['class_name']}">出席</button>
            </form>
            <form method="POST" style="display:inline;">
                <button name="delete_class" value="{lesson['class_name']}">削除</button>
            </form>
        </div>
        """

    # 授業追加
    html += """
    <h2>授業追加</h2>
    <form method="POST">
        <input name="new_class" placeholder="授業名">
        <input name="max_lessons" type="number" placeholder="上限回数">
        <button type="submit">追加</button>
    </form>
    """

    # 出席履歴
    html += """
    <h2>出席履歴</h2>
    <a href="/?order=DESC">新しい順</a> |
    <a href="/?order=ASC">古い順</a>
    <table border="1">
    <tr><th>授業名</th><th>日付</th><th>削除</th></tr>
    """

    for row in attendance:
        html += f"""
        <tr>
            <td>{row['class_name']}</td>
            <td>{row['date']}</td>
            <td>
                <form method="POST">
                    <button name="delete_attendance" value="{row['id']}">削除</button>
                </form>
            </td>
        </tr>
        """

    html += "</table>"

    conn.close()
    return html


import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))