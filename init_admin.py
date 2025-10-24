from app import app, db, User
from werkzeug.security import generate_password_hash
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('init_admin')

# 初始化管理员账户的脚本
def create_admin():
    try:
        with app.app_context():
            # 检查是否已存在管理员账户
            admin = User.query.filter_by(username='admin').first()
            
            if admin:
                logger.info('管理员账户已存在！')
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
                logger.info('管理员账户创建成功！')
                print('管理员账户创建成功！')
                print('用户名: admin')
                print('密码: admin123')
                print('请登录后及时修改密码！')
    except Exception as e:
        logger.error(f'创建管理员账户时出错: {str(e)}')
        print(f'创建管理员账户时出错: {str(e)}')
        db.session.rollback()

if __name__ == '__main__':
    create_admin()