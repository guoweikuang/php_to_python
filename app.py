# -*- coding: utf-8 -*-
"""
# php to Python
# @author guoweikuang
"""
import torndb

import tornado.web
import tornado.ioloop
import tornado.httpserver


from tornado.options import define, options
from utils import YamlLoader


define('address', default="127.0.0.1", help="绑定指定地址"， type=str)
define('port', default=8000, help="绑定指定端口", type=int)
define("debug", default=False, help="是否开启Debug模式", type=bool)
define("config", default="settings.yaml", help="配置文件路径", type=str)


class Appliction(tornado.web.Application):
    def __init__(self, handlers):
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

        if 'tornado' in self.config:
            settings.update(self.config['tornado'])

        self.db = torndb.Connection(**self.config['mysql'])