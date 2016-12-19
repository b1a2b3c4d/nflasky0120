# coding:utf-8
from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User


class LoginForm(Form):  # 登陆表
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    password = PasswordField(u'密码', validators=[DataRequired()])
    remember_me = BooleanField(u'保持登录')
    submit = SubmitField(u'登陆')


class RegistrationForm(Form):  # 注册表
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                           Email()])
    username = StringField(u'用户名', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                          u'用户名只能包含字母，数字，点和下划线'
                                          )])
    password = PasswordField(u'密码', validators=[
        DataRequired(), EqualTo('password2', message=u'两次输入的密码应该一致')])
    password2 = PasswordField(u'确认密码', validators=[DataRequired()])
    submit = SubmitField(u'注册')

    def validate_email(self, field):  # 验证邮箱是否存在
        # 如果表单类中定义了以validate_ 开头且后面跟着字段名的方法，
        # 这个方法就和常规的验证函数一起调用。
        # Datarequired()，Length()和Email()，EqualTo()均为常规验证函数。
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已被注册。')

    def validate_username(self, field): # 验证用户名是否存在
        if User.query.filter_by(username=field.data).first():
            raise ValidationError(u'用户名已被使用')


class ChangePasswordForm(Form):  # 修改密码
    old_password = PasswordField(u'旧密码', validators=[DataRequired()])
    password = PasswordField(u'新密码', validators=[
        DataRequired(), EqualTo('password2', message=u'两次输入的密码应一致。')])
    password2 = PasswordField(u'确认新密码', validators=[DataRequired()])
    submit = SubmitField(u'更新密码')


class PasswordResetRequestForm(Form):  # 请求密码重置
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    submit = SubmitField(u'重设密码')


class PasswordResetForm(Form):  # 密码重置表
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    password = PasswordField(u'新密码', validators=[
        DataRequired(), EqualTo('password2', message=u'两次输入的密码应一致。')])
    password2 = PasswordField(u'确认新密码', validators=[DataRequired()])
    submit = SubmitField(u'重置密码')

    def validate_email(self, field):  # 验证已存在的邮箱
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError(u'未知的邮箱。')


class ChangeEmailForm(Form):  # 更该邮箱表
    email = StringField(u'新邮箱', validators=[DataRequired(), Length(1, 64),
                                                 Email()])
    password = PasswordField(u'密码', validators=[DataRequired()])
    submit = SubmitField(u'更新邮箱地址')

    def validate_email(self, field):  # 验证已存在的邮箱
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已被注册。')
