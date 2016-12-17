# coding:utf-8
from flask import Blueprint  # 导入蓝本模块

main = Blueprint('main', __name__)  # 通行过实例化创建蓝本

from . import views, errors  # 避免循环导入，因为在view.py里还要导入蓝本main
from ..models import Permission


@main.app_context_processor  # 把 Permission 类加入模板上下文
def inject_permissions():
    return dict(Permission=Permission)  # 工厂函数dict()创建字典