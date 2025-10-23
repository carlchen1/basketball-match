from app import app, db, User
from werkzeug.security import generate_password_hash

# 初始化管理员账户的脚本
with app.app_context():
    # 检查是否已存在管理员账户
    admin = User.query.filter_by(username='admin').first()
    
    if admin:
        print('管理员账户已存在！')
    else:
        # 创建新的管理员账户
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),  # 默认密码
            team_name='管理员球队',
            contact='管理员',
            phone='13800138000',
            is_admin=True  # 设置为管理员
        )
        db.session.add(admin)
        db.session.commit()
        print('管理员账户创建成功！')
        print('用户名: admin')
        print('密码: admin123')
        print('请登录后及时修改密码！')