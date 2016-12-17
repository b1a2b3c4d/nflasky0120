#!/usr/bin/env python
# coding:utf-8
import os
COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

from app import create_app, db
# create_app是程序的工厂函数用来创建程序实例，在app.__init__中定义
# db是SQLAlchemy()的对象
from app.models import User, Follow, Role, Permission, Post, Comment
# 导入模型
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
# create_app是程序的工厂函数用来创建程序实例
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():  # 自定义函数,返回包含XXX的字典
    return dict(app=app, db=db, User=User, Follow=Follow, Role=Role,
                Permission=Permission, Post=Post, Comment=Comment)
manager.add_command("shell", Shell(make_context=make_shell_context))
# add_command在flask_script.__init__.py里,第一个参数是命令的名字，
# 第二个参数是命令的命名空间
# Shell类在flask_script.commandes.py里，make_context返回
# a callable returning a dict of variables used in the shell namespace
manager.add_command('db', MigrateCommand)


@manager.command  # 添加一个命令函数到registry
def test(coverage=False):
    """运行测试单元"""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
        # execvp 执行一个带有参数列表的可执行文件,替换当前进程
        # executable在sys.py里，是executable = 'C:\\Python27\\python.exe'
        # argv 在sys.py里，是argv = [] 此列表包含的是脚本传递的命令行参数
        # 如 [ manage.py, -runserver]
    import unittest
    tests = unittest.TestLoader().discover('tests')
    # lib文件夹下的unittest包里的loader.py里的Test Loader()类里的discover方法
    # 接受的第一个参数表示开始的目录
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


@manager.command
def profile(length=25, profile_dir=None):
    """在请求分析器的监视下运行程序"""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


@manager.command
def deploy():
    """运行部署任务"""
    from flask_migrate import upgrade
    from app.models import Role, User

    # 迁移数据库到最新版本
    upgrade()

    # 创建角色列表
    Role.insert_roles()

    # 给每个用户添加粉丝
    User.add_self_follows()


if __name__ == '__main__':  # 如果manager.py被直接调用就是true
    manager.run()
# __init__里Manager类run方法，接收参数后，handle方法来处理