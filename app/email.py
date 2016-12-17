# coding:utf-8
from flask_mail import Message  #
from threading import Thread
from flask import current_app, render_template
from . import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)   # mail是Mail的实例


def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    # current_app实际是一个代理，重开了线程后有影响，所以用了
    # get_current_object()属性
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    # 创建线程的实例来发送邮件
    thr.start()
    # 启动线程
    return thr
