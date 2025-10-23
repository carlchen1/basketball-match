from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///match_auth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    team_name = db.Column(db.String(128), nullable=True)
    contact = db.Column(db.String(64), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)  # 管理员标志
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(128), nullable=False)
    contact = db.Column(db.String(64), nullable=False)
    start_time = db.Column(db.String(64), nullable=False)
    location = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(32), default='待约战')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', backref='matches')

class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    challenger_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default='待确认')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    match = db.relationship('Match', backref='challenges')
    challenger = db.relationship('User', backref='challenges')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='messages')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 在Flask 2.3.0+中，before_first_request已被弃用
# 使用before_request并添加标志来确保只执行一次
tables_created = False
@app.before_request
def create_tables():
    global tables_created
    if not tables_created:
        with app.app_context():
            db.create_all()
        tables_created = True

def create_message(user_id, content):
    """创建新消息"""
    message = Message(user_id=user_id, content=content)
    db.session.add(message)
    return message

@app.route('/')
def index():
    # 只显示非已取消状态的约球
    matches = Match.query.filter(Match.status != '已取消').order_by(Match.created_at.desc()).all()
    # 查询用户的未读消息数量（如果已登录）
    unread_messages = 0
    if current_user.is_authenticated:
        unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('index.html', matches=matches, unread_messages=unread_messages)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # 未登录用户未读消息数为0
    unread_messages = 0
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        team_name = request.form.get('team_name', '').strip()
        contact = request.form.get('contact', '').strip()
        phone = request.form.get('phone', '').strip()

        if not username or not password or not team_name or not contact or not phone:
            flash('所有字段为必填项', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('用户名已存在，请换一个', 'warning')
            return redirect(url_for('register'))

        # 检查是否是第一个注册用户，如果是则自动设为管理员
        is_first_user = User.query.count() == 0
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            team_name=team_name,
            contact=contact,
            phone=phone,
            is_admin=is_first_user  # 第一个用户自动成为管理员
        )
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', unread_messages=unread_messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 未登录用户未读消息数为0
    unread_messages = 0
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            # 登录后计算未读消息数量
            unread_messages = Message.query.filter_by(user_id=user.id, is_read=False).count()
            flash('登录成功', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('用户名或密码错误', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html', unread_messages=unread_messages)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已登出', 'info')
    # 登出后重定向到首页，首页会处理未登录状态的未读消息显示
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_match():
    # 查询用户的未读消息数量
    unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    if request.method == 'POST':
        team_name = request.form['team_name']
        start_time = request.form['start_time']
        location = request.form['location']

        if not (team_name and start_time and location):
            flash('请填写必填项', 'danger')
            return redirect(url_for('create_match'))

        m = Match(
            team_name=team_name,
            contact=current_user.contact or current_user.username,
            start_time=start_time,
            location=location,
            owner=current_user
        )
        db.session.add(m)
        db.session.commit()
        flash('约球已发布', 'success')
        return redirect(url_for('index'))
    return render_template('create.html', unread_messages=unread_messages)

@app.route('/match/<int:match_id>')
def match_detail(match_id):
    match = Match.query.get_or_404(match_id)
    # 查询用户的未读消息数量（如果已登录）
    unread_messages = 0
    if current_user.is_authenticated:
        unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('match_detail.html', match=match, unread_messages=unread_messages)

@app.route('/match/<int:match_id>/challenge', methods=['GET', 'POST'])
@login_required
def make_challenge(match_id):
    match = Match.query.get_or_404(match_id)
    # 查询用户的未读消息数量
    unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        ch = Challenge(match=match, challenger=current_user, message=message)
        db.session.add(ch)
        match.status = '匹配中'
        # 给约球发起人发送消息通知
        create_message(match.owner_id, f'您的约球「{match.team_name}」收到了来自「{current_user.username}」的挑战请求')
        db.session.commit()
        flash('约战已发出，等待对方确认', 'success')
        return redirect(url_for('match_detail', match_id=match_id))
    return render_template('challenge.html', match=match, unread_messages=unread_messages)

@app.route('/challenge/<int:challenge_id>/confirm', methods=['POST'])
@login_required
def confirm_challenge(challenge_id):
    ch = Challenge.query.get_or_404(challenge_id)
    match = ch.match
    # only match owner can confirm
    if match.owner_id != current_user.id:
        flash('只有约球发起人可以确认', 'danger')
        # 查询用户的未读消息数量
        unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
        return redirect(url_for('match_detail', match_id=match.id))
    ch.status = '已同意'
    match.status = '约战成功'
    # reject others
    others = Challenge.query.filter(Challenge.match_id==match.id, Challenge.id!=ch.id).all()
    for o in others:
        if o.status == '待确认':
            o.status = '已拒绝'
            # 给被拒绝的挑战者发送消息
            create_message(o.challenger_id, f'您对约球「{match.team_name}」的挑战已被拒绝')
    # 给同意的挑战者发送消息
    create_message(ch.challenger_id, f'您对约球「{match.team_name}」的挑战已被接受！约战成功！')
    # 给约球发起人发送约战成功的消息
    create_message(match.owner_id, f'您的约球「{match.team_name}」已成功匹配，对手是「{ch.challenger.username}」')
    db.session.commit()
    flash('已确认约战', 'success')
    return redirect(url_for('match_detail', match_id=match.id))

@app.route('/challenge/<int:challenge_id>/reject', methods=['POST'])
@login_required
def reject_challenge(challenge_id):
    ch = Challenge.query.get_or_404(challenge_id)
    match = ch.match
    if match.owner_id != current_user.id:
        flash('只有约球发起人可以拒绝', 'danger')
        return redirect(url_for('match_detail', match_id=match.id))
    ch.status = '已拒绝'
    # 给被拒绝的挑战者发送消息
    create_message(ch.challenger_id, f'您对约球「{match.team_name}」的挑战已被拒绝')
    # if no pending left, revert match status
    pending = Challenge.query.filter_by(match_id=match.id, status='待确认').count()
    if pending == 0 and match.status == '匹配中':
        match.status = '待约战'
    db.session.commit()
    flash('已拒绝该约战', 'info')
    return redirect(url_for('match_detail', match_id=match.id))

@app.route('/match/<int:match_id>/cancel', methods=['POST'])
@login_required
def cancel_match(match_id):
    match = Match.query.get_or_404(match_id)
    # 只有约球发起人可以取消
    if match.owner_id != current_user.id:
        flash('只有约球发起人可以取消约球', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))
    
    # 将约球状态改为已取消
    match.status = '已取消'
    
    # 更新所有待确认的挑战为已取消，并通知挑战者
    pending_challenges = Challenge.query.filter_by(match_id=match_id, status='待确认').all()
    for challenge in pending_challenges:
        challenge.status = '已取消'
        create_message(challenge.challenger_id, f'您挑战的约球「{match.team_name}」已被发起人取消')
    
    db.session.commit()
    flash('约球已成功取消', 'success')
    return redirect(url_for('profile'))

@app.route('/profile')
@login_required
def profile():
    # 查询用户发布的所有约球信息
    user_matches = Match.query.filter_by(owner_id=current_user.id).order_by(Match.created_at.desc()).all()
    # 查询用户收到的挑战请求
    challenges_received = []
    for match in user_matches:
        for challenge in match.challenges:
            if challenge.status == '待确认':
                challenges_received.append(challenge)
    # 查询用户的未读消息
    unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('profile.html', user_matches=user_matches, challenges_received=challenges_received, unread_messages=unread_messages)

@app.route('/messages')
@login_required
def messages():
    # 获取用户的所有消息，按时间倒序排列
    user_messages = Message.query.filter_by(user_id=current_user.id).order_by(Message.created_at.desc()).all()
    # 将未读消息标记为已读
    for msg in user_messages:
        if not msg.is_read:
            msg.is_read = True
    db.session.commit()
    # 查询最新的未读消息数量（用于导航栏显示）
    unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('messages.html', messages=user_messages, unread_messages=unread_messages)

@app.route('/message/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    message = Message.query.get_or_404(message_id)
    if message.user_id != current_user.id:
        flash('无权操作此消息', 'danger')
        return redirect(url_for('messages'))
    message.is_read = True
    db.session.commit()
    return redirect(url_for('messages'))

@app.route('/messages/read-all', methods=['POST'])
@login_required
def mark_all_messages_read():
    Message.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('所有消息已标记为已读', 'success')
    return redirect(url_for('messages'))

@app.route('/admin')
@login_required
def admin_panel():
    # 检查用户是否为管理员
    if not current_user.is_admin:
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('index'))
    
    # 查询所有用户、约球和挑战
    users = User.query.all()
    matches = Match.query.all()
    challenges = Challenge.query.all()
    
    # 统计未读消息数量
    unread_messages = Message.query.filter_by(is_read=False).count()
    
    return render_template('admin.html', 
                          users=users,
                          matches=matches,
                          challenges=challenges,
                          unread_messages=unread_messages)
    
    # 查询所有用户、约球和挑战数据
    users = User.query.all()
    matches = Match.query.order_by(Match.created_at.desc()).all()
    challenges = Challenge.query.order_by(Challenge.created_at.desc()).all()
    
    # 查询用户的未读消息数量
    unread_messages = Message.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('admin.html', users=users, matches=matches, challenges=challenges, unread_messages=unread_messages)

if __name__ == '__main__':
    print("Starting Flask application...")
    # 手动创建数据库表
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created.")
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
