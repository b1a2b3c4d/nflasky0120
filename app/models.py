# coding:utf-8
from datetime import datetime # 时间戳
import hashlib  # 摘要算法
from werkzeug.security import generate_password_hash, check_password_hash
# 生成密码哈希值，校验密码哈希值
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
# 生成身份认证令牌
from markdown import markdown
# 支持markdown语法
import bleach
# 使用python实现的html清理器
from flask import current_app, request, url_for
# current_app应用上下文，获取当前的request对象，url_for生成相应的url
from flask_login import UserMixin, AnonymousUserMixin
# 用户注册的类
from app.exceptions import ValidationError
# 认证错误
from . import db, login_manager


class Permission:  # 设定权限 0x是十六进制
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):  # 角色表 记录角色及其权限
    __tablename__ = 'roles'  # 表的名字
    id = db.Column(db.Integer, primary_key=True)  # id主键
    name = db.Column(db.String(64), unique=True)  # 角色名
    default = db.Column(db.Boolean, default=False, index=True)  # 默认角色
    permissions = db.Column(db.Integer)  # 权限
    users = db.relationship('User', backref='role', lazy='dynamic')  # 外键
    # 0.添加到Role模型中的users属性代表这个关系的面向对象视角。对于一个Role类的实例，
    # 其users属性将返回与角色相关联的用户组成的列表。
    # 1.db.Relationship()第一个参数表明这个关系的另一端是哪个模型（类）。
    # 如果模型类尚未定义，可使用字符串形式指定。
    # 2.db.Relationship()第二个参数backref，将向User类中添加一个role属性，
    # 从而定义反向关系。这一属性可替代role_id访问Role模型，此时获取的是模型对象，
    # 而不是外键的值。

    @staticmethod
    def insert_roles():  # 创建角色 "|"是或运算符
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
            db.session.commit()
        db.session.commit()

    def __repr__(self):  # 输出字符串
        return '<Role %r>' % self.name


class Follow(db.Model):  # 关注表 记录关注的关系的表
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    # 关注者
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    # 被关注者
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # 时间戳


class User(UserMixin, db.Model): # 用户表 记录用户信息的表
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)  # 主键
    email = db.Column(db.String(64), unique=True, index=True)  # 邮箱
    username = db.Column(db.String(64), unique=True, index=True)  # 用户名
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    # 外键 指定用户角色 传给 db.ForeignKey() 的参数 'roles.id' 表明，
    # 这列的值是 roles 表中行的 id 值
    password_hash = db.Column(db.String(128))  # 密码哈希值
    confirmed = db.Column(db.Boolean, default=False)  # 是否认证过了
    name = db.Column(db.String(64))  # 角色名字
    location = db.Column(db.String(64))  # 地址
    about_me = db.Column(db.Text())  # 关于我
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)  # 注册时间
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)  # 最后一次访问的时间
    avatar_hash = db.Column(db.String(32))  # 头像的哈希值
    posts = db.relationship('Post', backref='author', lazy='dynamic')  # 博客内容
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    # 此用户已关注的人
    # 使用可选参数foreign_keys指定外键
    # db.backref()是用来回引Follow模型，其中lazy的joined模式可以实现从连接查询中加载相关对象
    # dynamic因此关系属性不会直接返回记录，而是返回查询对象，
    # 所以在执行查询之前还可以添加额外的过滤器。
    # cascade中为 all,delete-orphan 的意思是启用所有默认层叠选项，而且还要删除孤儿记录。
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    # 关注此用户的人
    comments = db.relationship('Comment', backref='author', lazy='dynamic')  # 评论

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py  # 用于生成虚拟信息的包

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            db.session.commit()
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    @staticmethod
    def add_self_follows():  # 批量添加自关注
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # super()不但能找到基类方法，而且还为我们传进 self
        if self.role is None:  # 判断角色
            if self.email == current_app.config['FLASKY_ADMIN']:
                #  判断是否是管理员
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                # 分配默认角色
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            # 将邮箱地址进行散列
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()
        self.followed.append(Follow(followed=self))
        # 添加自关注

    @property  # 只读属性
    def password(self):  # 密码
        raise AttributeError('password is not a readable attribute')

    @password.setter  # 可读写的属性
    def password(self, password):  # 保存密码的哈希值
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):  # 检查密码哈希值
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):  # 生成认证令牌
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):  # 确认用户
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def generate_reset_token(self, expiration=3600):  # 新设置令牌
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):  # 重新设置密码
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        db.session.commit()
        return True

    def generate_email_change_token(self, new_email, expiration=3600):  #
        # 生成修改邮箱的令牌
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):  # 更改邮箱
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        db.session.commit()
        return True

    def can(self, permissions):  # 判断当前用户角色权限
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):  # 判断是否是管理员
        return self.can(Permission.ADMINISTER)

    def ping(self):  # 最后登陆时间
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar(self, size=100, default='identicon', rating='g'):
        # 生成头像
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def follow(self, user):  # 关注
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
            db.session.commit()

    def unfollow(self, user):  # 取消关注
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):  # 用于判定是否已关注
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):  # 用于判定是否已被关注
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    @property
    def followed_posts(self):  # 此用户关注的博客
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id, _external=True),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts': url_for('api.get_user_posts', id=self.id, _external=True),
            'followed_posts': url_for('api.get_user_followed_posts',
                                      id=self.id, _external=True),
            'post_count': self.posts.count()
        }
        return json_user

    def generate_auth_token(self, expiration):  # 生成授权令牌
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):  # 确认授权令牌
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):  # 匿名用户
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader  # 加载用户的回调函数
def load_user(user_id):
    return User.query.get(int(user_id))


class Post(db.Model):  # 博客表
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)  # 文章内容
    body_html = db.Column(db.Text)  # html格式的文章内容
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 作者
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    # 评论
    @staticmethod
    def generate_fake(count=100):  # 生成假数据
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """on_changed_body 函数注册在 body 字段上，是 SQLAlchemy“ set”事件的
        监听程序，这意味着只要这个类实例的 body 字段设了新值，函数就会自动被调
        用。 on_changed_body 函数把 body 字段中的文本渲染成 HTML 格式，结果保
        存在 body_html 中，自动且高效地完成Markdown 文本到 HTML 的转换。"""
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


    def to_json(self):  # 转化为 JSON
        json_post = {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
            'comments': url_for('api.get_post_comments', id=self.id,
                                _external=True),
            'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):  # 从 JSON 格式数据创建一篇博客文章
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)


db.event.listen(Post.body, 'set', Post.on_changed_body)
# on_changed_body 函数注册在 body 字段上，是 SQLAlchemy“ set”事件的
# 监听程序，这意味着只要这个类实例的 body 字段设了新值，函数就会自动被调用。


class Comment(db.Model):  # 评论表
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id, _external=True),
            'post': url_for('api.get_post', id=self.post_id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
