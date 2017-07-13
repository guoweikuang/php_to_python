# -*- coding: utf-8 -*-
import tornado.web
from models import account


class BaseHandler(tornado.web.RequestHandler):
    
    @property
    def db(self):
        return self.application.debug

    @property
    def redis(self):
        return self.application.redis

    def get_current_user(self):
        token = self.get_secure_cookie('token')
        if not token:
            return None

        account = accounts.get_info(self.redis.get(token))
        if account:
            self.set_secure_cookie('token', token, expires_days=2)
            self.redis.setex(token, account['id'], 86400)
            return account
        else:
            return None