# -*- coding: utf-8 -*-
"""
# php to Python
# @author guoweikuang
"""
import db
import redis
import torndb

import tornado.web
import tornado.ioloop
import tornado.httpserver


from tornado.options import define, options
from utils import YamlLoader
from protocols import BaseHandler


define('address', default="127.0.0.1", help="绑定指定地址"， type=str)
define('port', default=8000, help="绑定指定端口", type=int)
define("debug", default=False, help="是否开启Debug模式", type=bool)
define("config", default="settings.yaml", help="配置文件路径", type=str)


class Appliction(tornado.web.Application):
    def __init__(self):
        try:
            self.config = yaml.load(file(options.config, 'r'), YamlLoader)
        except yaml.YAMLError as e:
            logging.critical("Error in configuration file: %s", e)

        settings = dict(
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            template_path=os.path.join(os.path.dirname(__file__), 'template'),
            login_url="/welcome",
            cookie_secret=self.config['secret']['cookie'],
            session_secret=self.config['secret']['session'],
            debug=options.debug,
        )
        handlers = [
            (r"/", HomeHandler),
            (r"/login", LoginHandler),
        ]

        if 'tornado' in self.config:
            settings.update(self.config['tornado'])

        self.db = db.mysql = torndb.Connection(**self.config['mysql'])
        pool = redis.ConnectionPool(**self.config['redis'])
        self.redis = db.redis = redis.Redis(connection_pool=pool)
        tornado.web.Application.__init__(self, handlers, **settings)

        self.startup()

    def startup(self):
        """初始化工作"""
        pass


class HomeHandler(BaseHandler):
    def get(self):
        self.write('hello, world')


class LoginHandler(BaseHandler):
    def get(self):
        self.write('login')

    @tornado.web.authenticated
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


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Appliction())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

        
if __name__ == '__main__':
    main()


