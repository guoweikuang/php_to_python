#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
php to python

@author: guoweikuang
"""
from protocols import BaseHandler


class GetJopall(BaseHandler):
    def get(self):
        idfa = self.get_argument('idfa', '')
        idfv = self.get_argument('idfv', '')
        server = self.get_argument('server', '')
        version = self.get_argument('version', '')

        
