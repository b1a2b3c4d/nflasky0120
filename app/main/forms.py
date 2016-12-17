# coding:utf-8
from flask_wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp
# regexp是正则表达式
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField  # Markdown模块
from ..models import Role, User


class NameForm(Form):  # 姓名表格
    name = StringField(u'你的名字是?', validators=[DataRequired()])
    submit = SubmitField(u'提交')


class EditProfileForm(Form):  # 编辑资料表格
    name = StringField(u'真实姓名', validators=[Length(0, 64)])
    location = StringField(u'地址', validators=[Length(0, 64)])
    about_me = TextAreaField(u'随便说说')
    submit = SubmitField(u'提交')


class EditProfileAdminForm(Form):  # 管理员用编辑资料表
    email = StringField(u'邮箱', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField(u'用户名', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                          u'用户名必须是字母 '
                                          u'数字或者下划线')])
    confirmed = BooleanField(u'是否认证')
    role = SelectField(u'角色', coerce=int)
    name = StringField(u'真实姓名', validators=[Length(0, 64)])
    location = StringField(u'地址', validators=[Length(0, 64)])
    about_me = TextAreaField(u'随便说说')
    submit = SubmitField(u'提交')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        # WTForms 对 HTML 表单控件 <select> 进行 SelectField 包装，从而实
        # 现下拉列表，用来在这个表单中选择用户角色。 SelectField 实例必须在其
        # choices 属性中设置各选项。选项必须是一个由元组组成的列表， 各元组都
        # 包含两个元素：选项的标识符和显示在控件中的文本字符串。 choices 列表
        # 在表单的构造函数中设定，其值从 Role 模型中获取，使用一个查询按照角色
        # 名的字母顺序排列所有角色。 元组中的标识符是角色的 id，因为这是个整数，
        # 所以在 SelectField 构造函数中添加 coerce=int 参数，从而把字段的值转
        # 换为整数，而不使用默认的字符串。
        self.user = user

    def validate_email(self, field):  # 检验邮箱是否已被使用
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已经认证.')

    def validate_username(self, field): # 检验用户名是否已被试用
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError(u'用户名已被使用.')


class PostForm(Form):  # 文章表
    body = PageDownField(u"你在想什么?", validators=[DataRequired()])
    submit = SubmitField(u'提交')


class CommentForm(Form):  # 评论表
    body = StringField(u'此处评论', validators=[DataRequired()])
    submit = SubmitField(u'提交')
