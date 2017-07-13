# -*- coding: utf-8 -*-
import utils
import tornado.escape
from protocols import BaseHandler
from models import accounts


class LoginHandler(BaseHandler):
    """用户登录"""
    def get(self):
        self.write('login')

    def post(self):
        errors = []
        username = self.get_argument('username', '')
        password = self.get_argument('password', '')

        if not username:
            errors.append(u"请输入用户名")
        if not password:
            errors.append(u"请输入用户密码！")
        if errors:
            return self.render('account/login.html', errors=errors)

        username = tornado.escape.xhtml_escape(username)
        account = accounts.get_info_by_username(username)
        if account and utils.validate_pwd(account['pwd'], password, account['salt']):
            token = utils.gen_token()
            self.set_secure_cookie('token', token, expires_days=2)
            self.redis.setex(token, account['id'], 86400)
            self.redirect('home')
        else:
            errors.append(u"用户名或密码错误")
            rerturn render("account/login.html", errors=errors)
            

        