from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'secretkey'
DB_NAME = 'match.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        team_name TEXT,
                        contact TEXT,
                        start_time TEXT,
                        location TEXT,
                        status TEXT DEFAULT '待约战'
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS challenges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id INTEGER,
                        team_name TEXT,
                        contact TEXT,
                        message TEXT,
                        FOREIGN KEY(match_id) REFERENCES matches(id)
                    )''')
        conn.commit()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM matches ORDER BY id DESC')
    matches = c.fetchall()
    conn.close()
    return render_template('index.html', matches=matches)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        team_name = request.form['team_name']
        contact = request.form['contact']
        start_time = request.form['start_time']
        location = request.form['location']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO matches (team_name, contact, start_time, location) VALUES (?, ?, ?, ?)',
                  (team_name, contact, start_time, location))
        conn.commit()
        conn.close()
        flash('约球信息已发布！')
        return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/challenge/<int:match_id>', methods=['GET', 'POST'])
def challenge(match_id):
    if request.method == 'POST':
        team_name = request.form['team_name']
        contact = request.form['contact']
        message = request.form['message']
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO challenges (match_id, team_name, contact, message) VALUES (?, ?, ?, ?)',
                  (match_id, team_name, contact, message))
        c.execute("UPDATE matches SET status='匹配中' WHERE id=?", (match_id,))
        conn.commit()
        conn.close()
        flash('约战申请已提交！')
        return redirect(url_for('index'))
    return render_template('challenge.html', match_id=match_id)

@app.route('/approve/<int:match_id>/<int:challenge_id>')
def approve(match_id, challenge_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE matches SET status='约战成功' WHERE id=?", (match_id,))
    conn.commit()
    conn.close()
    flash('约战已确认成功！')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
