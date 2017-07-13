#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015 Youmi
#
# @author: chenjiehua@youmi.net, lisongjian@youmi.net
#

import yaml
import redis
import os.path
import hashlib
import logging
import base64
import time
import random
import requests
import torndb
import db
import json
from math import ceil

from hashlib import sha256
from hmac import HMAC
from models import wechat, orders, users, oneshang, qianlu_push, checks

from xml.dom import minidom
from datetime import datetime, date, timedelta

SETTINGS_FILE = "settings.yaml"
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

class YamlLoader(yaml.Loader):
    """ Yaml loader

    Add some extra command to yaml.

    !include:
        see http://stackoverflow.com/questions/528281/how-can-i-include-an-yaml-file-inside-another
        include another yaml file into current yaml
    """

    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(YamlLoader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, 'r') as f:
            return yaml.load(f, YamlLoader)

YamlLoader.add_constructor('!include', YamlLoader.include)

# MySQL数据库连接配置
try:
    config = yaml.load(file(SETTINGS_FILE, 'r'), YamlLoader)
except yaml.YAMLError as e:
    print "Error in configuration file: %s" % e

# 数据库连接实例
db.mysql = torndb.Connection(**config['mysql'])
pool = redis.ConnectionPool(**config['redis'])
db.redis = redis.Redis(connection_pool=pool)


class Loggers(object):
    """简单的logging wrapper"""

    def __init__(self):
        self.loggers = {}

    def use(self, log_name, log_path):
        if not log_name in self.loggers:
            logger = logging.getLogger(log_name)
            logger.setLevel(logging.INFO)
            if not logger.handlers:
                fh = logging.FileHandler(log_path)
                fh.setLevel(logging.INFO)
                formatter = logging.Formatter('%(asctime)s - %(message)s')
                fh.setFormatter(formatter)
                logger.addHandler(fh)
            self.loggers[log_name] = logger
        return self.loggers[log_name]

loggers = Loggers()

def pagination(total_count, page, limit=50):
    """分页器

    data: 分页数据,
    page: 指定页码,
    limit: 每页长度,
    """
    total_page = (total_count - 1) / limit + 1 if total_count > 0 else 0
    page = total_count / limit if page * limit > total_count else page - 1
    pre_page = page if page > 0 else None
    next_page = page + 2 if page * limit < total_count else None
    offset = page * limit
    result = {
        "total_page": total_page,
        "cur_page": page + 1,
        "pre_page": pre_page,
        "next_page": next_page,
        "offset":offset,
        "limit": limit
    }
    return result


def paginator(data, page, limit=50):
    """分页器

    data: 分页数据,
    page: 指定页码,
    limit: 每页长度,
    """
    total_count = len(data)
    total_page = (total_count - 1) / limit + 1 if total_count > 0 else 0
    page = total_count / limit if page * limit > total_count else page - 1
    start = page * limit
    data = data[start:start+limit]
    pre_page = page if page > 0 else None
    next_page = page + 2 if page * limit < total_count else None
    result = {
        "data": data,
        "total_count": total_count,
        "total_page": total_page,
        "cur_page": page + 1,
        "pre_page": pre_page,
        "next_page": next_page,
    }
    return result


def md5(raw_str):
    return hashlib.new("md5", str(raw_str)).hexdigest()


def sha1(raw_str):
    return hashlib.new("sha1", str(raw_str)).hexdigest()


def gen_token():
    raw_str = '%s%s' % (time.time(), random.randint(1000000, 9999999))
    return sha1(md5(raw_str))


def encrypt_pwd(pwd, salt=None):
    """ 密码加密 """
    if salt is None:
        salt = os.urandom(8)
    else:
        salt = base64.b64decode(salt)

    result = pwd
    for i in xrange(3):
        result = HMAC(str(result), salt, sha256).hexdigest()

    return base64.b64encode(salt), result


def validate_pwd(enc_pwd, in_pwd, salt):
    """ 验证密码 """
    return enc_pwd == encrypt_pwd(in_pwd, salt)[1]

# 微信红包相关
def dict_to_xml(data):
    doc = minidom.Document()
    root = doc.createElement("xml")
    doc.appendChild(root)

    for k, v in data.items():
        item = doc.createElement(k)
        item.appendChild(doc.createTextNode(str(v)))
        root.appendChild(item)
    return doc.toxml()

def xml_to_dict(str_xml):
    """将xml转换为dict，只支持单层级的xml解析, 如：<xml><name>wukai</name><age>29</age></xml>"""
    dict = {}
    tree = ET.fromstringlist(str_xml)
    for ele in tree.getchildren():
        dict[ele.tag] = ele.text
    return dict

def sign_mp(data, secret):
    """微信变量签名"""
    keys = data.keys()
    keys.sort()
    kvs = []
    for k in keys:
        kvs.append("%s=%s" % (k, data[k]))
    #拼接上密钥
    kvs.append("%s=%s" % ("key", secret))
    stringA = "&".join(kvs)
    return md5(stringA).upper()

def gen_billno(mch_id):
    """生成微信红包订单号"""
    dt = datetime.now()
    ds = dt.strftime("%Y%m%d")
    return "%s%s%s" % (mch_id, ds, random.randint(1000000000, 9999999999))

# 微信企业支付
def send_hongbao(wxappid, apikey, mchid, nonce_str, oid, partner_trade_no, user_name, openid, amount, desc, ip, path_to_cert, path_to_key, uid, user_points, parent_uid, return_amount, tid):
    """
    mch_id: 商户ID
    """
    url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers"
    headers = {
        "Accept": "text/xml",
        "Content-Type": "text/xml;charset=utf-8",
    }

    data = {
        "mch_appid":wxappid,
        "mchid": mchid,
        "nonce_str": nonce_str,
        "partner_trade_no": partner_trade_no,
        "check_name": "FORCE_CHECK",
        #"check_name": "OPTION_CHECK",
        "re_user_name": user_name,
        "amount": amount,
        "desc": desc,
        "openid": openid,
        "spbill_create_ip": ip
    }

    data["sign"] = sign_mp(data, apikey)

    r = requests.post(url, headers=headers, data = dict_to_xml(data), cert=(path_to_cert, path_to_key), verify=True)
    resp = xml_to_dict(r.content)
    # print `resp`+ 'partner_trade_no' + `oid`
    loggers.use('weixin', config['log']['weixin']).info('partner_trade_no=' + `oid` + str(resp))
    #if resp['return_code']=='SUCCESS' and resp['err_code']!='NAME_MISMATCH' :
    if resp['return_code']=='SUCCESS' and resp['result_code']=='SUCCESS' :
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'SUCC'
        calltime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
        wechat.set_status_paymentno(oid, 13, resp['payment_no'],calltime)
        # f_ex=users.get_first_exchange(uid)
        # if not f_ex:
        #     users.set_first_exchange(uid, parent_uid)
    if resp['err_code']=='FREQ_LIMIT':
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'MANY TIME'
        wechat.set_wx_order_note(oid, u'多次提交')
    if resp['err_code']=='NAME_MISMATCH':
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'NAME_MISMATCH'
        note = resp['return_msg']
        wechat.set_wx_order_status(oid, 14, note)
        users.add_ex_points(uid, return_amount)
        orders.new_global_order(
            uid, user_points, return_amount, orders.OTYPE_EXCHANGE,
            #u"微信兑换失败，退回 %d 元" % int(return_amount/100))
            u"微信兑换失败，退回")
    else:
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'WHY FAIL'
        wechat.set_wx_order_note(oid, resp['return_msg'])
    return r.content.decode("utf8")

def send_Qbi(phone, customOrderCode, orderId, userId, key, prizeId, prizePriceTypeId, cardNumber, points, uid, user_points, parent_uid):
    """
    1shang q币
    """
    url = "http://api.1shang.com/getAward/getBankCash"

    sign_str = (str(customOrderCode)+str(orderId)+str(userId)+str(cardNumber)+str(key))
    sign = md5(sign_str)

    data = {
        "phone": phone,
        "prizeId": prizeId,
        "userId": userId,
        "prizePriceTypeId": prizePriceTypeId,
        "orderId": orderId,
        "customOrderCode":customOrderCode,
        "count": '1',
        "cardNumber": cardNumber,
        "sign": sign,
    }

    r = requests.get(url, params=data)
    resp = json.loads(r.text)
    print `resp` + '&customOrderCode=' + `customOrderCode`
    loggers.use('yishang', config['log']['yishang']).info('type=Qbi&'+str(resp))
    if resp['result']=='10000' or resp['result']=='56' or resp['result']=='58':
        oneshang.update_code_no(customOrderCode, 11, resp['code'])
        f_ex=users.get_first_exchange(uid)
        if not f_ex:
            users.set_first_exchange(uid, parent_uid)
    else:
        oneshang.set_status(customOrderCode, 14)
        users.add_ex_points(uid, points)
        orders.new_global_order(
            uid, user_points, points, orders.OTYPE_EXCHANGE,
            u"Q币兑换失败，退回%d元" % int(points/100))
    return r.content.decode("utf8")

def send_Mobi(phone, customOrderCode, orderId, userId, key, prizeId, prizePriceTypeId, uid, points, user_points, parent_uid):
    """
    1shang 话费
    """
    url = "http://api.1shang.com/orders/getAward"

    sign_str = (str(customOrderCode)+str(orderId)+str(userId)+str(key))
    sign = md5(sign_str)
    operation = "recharge"

    data = {
        "phone": phone,
        "prizeId": prizeId,
        "userId": userId,
        "prizePriceTypeId": prizePriceTypeId,
        "orderId": orderId,
        "customOrderCode":customOrderCode,
        "count": '1',
        "sign": sign,
        "operation": operation
    }

    r = requests.get(url, params=data)
    resp = json.loads(r.text)
    print resp
    loggers.use('yishang', config['log']['yishang']).info('type=Mobi&'+str(resp))
    if resp['result']=='10000' or resp['result']=='56' or resp['result']=='58':
        oneshang.update_code_no(customOrderCode, 11, resp['code'])
        f_ex=users.get_first_exchange(uid)
        if not f_ex:
            users.set_first_exchange(uid, parent_uid)
    else:
        oneshang.set_status(customOrderCode, 14)
        users.add_ex_points(uid, points)
        orders.new_global_order(
            uid, user_points, points, orders.OTYPE_EXCHANGE,
            u"话费兑换失败，退回%d元" % int(points/100))
    return r.content.decode("utf8")

# 又拍地址token
def once_token(url):
    data = url.split('/')
    uri = '/%s/%s/%s' % (data[len(data)-3], data[len(data)-2], data[len(data)-1])
    endtime = str(int(time.time()) + 600)
    upuri = md5('&'.join([config['upai']['key'], endtime, uri]))[12:20] + endtime
    img_url = "%s?_upt=%s" % (url, upuri)
    return img_url

# jpush
def push(phone, msg, jpid, jpkey):
    import jpush as jpush
    if jpid and jpkey:
        app_key = jpid
        master_secret = jpkey
    else:
        from conf import app_key, master_secret

    _jpush = jpush.JPush(app_key, master_secret)

    push = _jpush.create_push()
    push.audience = jpush.audience(
                jpush.alias(phone)
            )
    ios_msg = jpush.ios(alert=msg, sound="default")
    push.notification = jpush.notification(alert=msg, ios=ios_msg)
    push.platform = jpush.all_
    #push.message = {"msg_content":'test'}
    # push.options = {"time_to_live":86400, "sendno":12345,"apns_production":False}
    push.send()

class Pagination(object):

    def __init__(self, page, total_count, per_page=10):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or
               num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num

def parse_date(req_handler):
    """处理日期"""
    edate = req_handler.get_argument('edate', None)
    sdate = req_handler.get_argument('sdate', None)
    strdate = {}
    if edate:
        strdate['e'] = edate
        edate = datetime.strptime(edate, "%Y-%m-%d")
    else:
        edate = date.today() + timedelta(days=1)
        strdate['e'] = edate.strftime("%Y-%m-%d")
    if sdate:
        strdate['s'] = sdate
        sdate = datetime.strptime(sdate, "%Y-%m-%d")
    else:
        sdate = date.today() - timedelta(days=14)
        strdate['s'] = sdate.strftime("%Y-%m-%d")

    return strdate, sdate, edate

# qlpush
def qlpush_by_idfa(idfa,push_message):
    item = qianlu_push.get_message_by_idfa(idfa)
    send_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    from tasks.startup import qlpush2
    for i in item:
        token, pem = i['token'], i['pem'].split('-')[1]
        qlpush2.apply_async(args=['%s.pem'%pem,token,push_message,send_time],queue='qlpush2')

# 微信现金券企业支付
def send_check(wxappid, apikey, mchid, nonce_str, oid, partner_trade_no, user_name, openid, amount, desc, ip, path_to_cert, path_to_key, uid, user_points, parent_uid, return_amount, tid, checkid):
    """
    mch_id: 商户ID
    """
    url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers"
    headers = {
        "Accept": "text/xml",
        "Content-Type": "text/xml;charset=utf-8",
    }

    data = {
        "mch_appid":wxappid,
        "mchid": mchid,
        "nonce_str": nonce_str,
        "partner_trade_no": partner_trade_no,
        "check_name": "FORCE_CHECK",
        #"check_name": "OPTION_CHECK",
        "re_user_name": user_name,
        "amount": amount,
        "desc": desc,
        "openid": openid,
        "spbill_create_ip": ip
    }

    data["sign"] = sign_mp(data, apikey)

    r = requests.post(url, headers=headers, data = dict_to_xml(data), cert=(path_to_cert, path_to_key), verify=True)
    resp = xml_to_dict(r.content)
    # print `resp`+ 'partner_trade_no' + `oid`
    loggers.use('weixin', config['log']['weixin']).info('wxcheck&partner_trade_no=' + `oid` + str(resp))
    if resp['return_code']=='SUCCESS' and resp['result_code']=='SUCCESS' :
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'SUCC'
        calltime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
        checks.set_status_paymentno(oid, 13, resp['payment_no'],calltime)
        checks.set_check_status(checkid, 4)
        # f_ex=users.get_first_exchange(uid)
        # if not f_ex:
        #     users.set_first_exchange(uid, parent_uid)
    if resp['err_code']=='FREQ_LIMIT':
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'MANY TIME'
        checks.set_wx_order_note(oid, u'多次提交')
    if resp['err_code']=='NAME_MISMATCH':
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'NAME_MISMATCH'
        note = resp['return_msg']
        checks.set_wx_order_status(oid, 14, note)
        checks.set_check_status(checkid, 1)
        orders.new_global_order(
            uid, user_points, return_amount, orders.OTYPE_EXCHANGE,
            u"微信用户名错误，退回现金券")
    else:
        print `resp`+ 'partner_trade_no' + `partner_trade_no` + 'WHY FAIL'
        checks.set_wx_order_note(oid, resp['return_msg'])
    return r.content.decode("utf8")

# 发送邮件
def send_mail(message):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    me = "13710326741@139.com"
    you = "ad@qianlu.com"
    #you = "zhongsihang@qianlu.com"
    mail_user = '13710326741@139.com'
    mail_pass = 'qq542652833'
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "导出文件链接"
    msg['From'] = me
    msg['To'] = you

    html = """
    <html>
      <head></head>
      <body>
        <p><br>%s<br></p>
      </body>
    </html>
    """%(message)

    # Record the MIME types of both parts - text/plain and text/html.
    part2 = MIMEText(html, 'html')

    msg.attach(part2)
    s = smtplib.SMTP('smtp.139.com')
    s.login(mail_user,mail_pass)
    s.sendmail(me, you, msg.as_string())
    s.quit()

def time_format(get_times):
    """ 对时间转换"""
    # redis缓存时times为int，判断times是否为int
    if type(get_times)==type(1):
        times=datetime.datetime.utcfromtimestamp(get_times)
        return_times = datetime.datetime.strftime(times, "%Y%m%d %H:%M:%S")
        return_times = datetime.datetime.strptime(return_times, "%Y%m%d %H:%M:%S")
    # 无缓存时为datetime类型
    else:
        return_times = get_times
    return return_times

def today_earn(uid, points):
    """ 缓存记录今日赚取 """
    key_name = "qianka:earn:%s:%s" % (uid, date.today().strftime("%Y%m%d"))
    rate = 100
    data = db.redis.get(key_name)
    if not data:
        db.redis.setex(key_name, "%.2f" % (float(points) / int(rate)), 86400)
    else:
        db.redis.setex(key_name, "%.2f" % (float(data) + (float(points) / int(rate))), 86400)
