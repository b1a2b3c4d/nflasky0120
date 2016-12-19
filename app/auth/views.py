# coding:utf-8
from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import db
from ..models import User
from ..email import send_email
from .forms import LoginForm, RegistrationForm, ChangePasswordForm,\
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm


@auth.before_app_request
# 若想在蓝本中使用针对程序全局请求的钩子， 必须使用 before_app_request 修饰器
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        # 因为每次请求都会调用before_request,
        # ping被用于记录最近登录时间
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():  # 未确认
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():  # 登陆
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            # login_user,由flask_login提供
            return redirect(request.args.get('next') or url_for('main.index'))
        flash(u'密码或用户名错误。')
        # 用户访问未授权的 URL 时会显示登录表单， Flask-Login
        # 会把原地址保存在查询字符串的 next 参数中，这个参数可从 request.args
        # 字典中读取。如果查询字符串中没有 next 参数，则重定向到首页。
        # 如果用户输入的电子邮件或密码不正确，程序会设定一个 Flash 消息，
        # 再次渲染表单，让用户重试登录。
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():  # 登出
    logout_user()
    flash(u'您已退出登录。')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():  # 注册
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, u'确认你的账号',
                   'auth/email/confirm', user=user, token=token)
        flash(u'已发送一封确认邮件到您的邮箱。')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):  # 确认
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash(u'您已确认您的邮箱，谢谢。')
    else:
        flash(u'确认链接无效或已过期。')
    return redirect(url_for('main.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():  # 再次发送确认
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, u'确认您的账户。',
               'auth/email/confirm', user=current_user, token=token)
    flash(u'一封新的确认邮件已经发送给您。')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():  # 更改密码
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash(u'您的密码已经更改。')
            return redirect(url_for('main.index'))
        else:
            flash(u'密码无效。')
    return render_template("auth/change_password.html", form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():  # 忘记密码后发送重置邮件
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, u'重置您的密码',
                       'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash(u'一封密码更改说明已发送到您的邮箱。')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):  # 重置密码页面
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash(u'您的密码已更改。')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():  # 发送更改邮箱链接
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, u'确认您的邮箱地址',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash(u'一封邮箱更改说明已发送到您的邮箱。')
            return redirect(url_for('main.index'))
        else:
            flash(u'密码或邮箱无效。')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change-email/<token>')
@login_required
def change_email(token):  # 更改邮箱的确认页面
    if current_user.change_email(token):
        flash(u'您的邮箱已更改。')
    else:
        flash(u'请求无效。')
    return redirect(url_for('main.index'))
