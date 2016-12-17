# coding:utf-8
from functools import wraps
from flask import abort
from flask_login import current_user
from .models import Permission


def permission_required(permission):  # 用于限制用户访问的装饰器
    def decorator(f):
        @wraps(f)  # 把原始函数的属性复制到decorated_function中
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)  # 向非法的请求返回 403 错误代号
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMINISTER)(f)
