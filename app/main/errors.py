# coding:utf-8
from flask import render_template, request, jsonify
from . import main


@main.app_errorhandler(403)  # app_errorhandler用类注册全局的错误处理器
def forbidden(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        # 这个if是为了根据客户端请求的格式改写响应，向web服务客户端发送json格式
        # 的响应，其他的发送html格式，request.accept_mimetypes.accept_json是由
        # werkzeug提供的。
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('403.html'), 403


@main.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('404.html'), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('500.html'), 500
