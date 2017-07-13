# -*- coding: utf-8 -*-
import db


def get_info(id):
    return db.mysql.get(
        "SELECT * FROM `accounts` WHERE `id` = %s "
        "AND `status` = 1", id)


def get_info_by_username(username):
    return db.mysql.get(
        "SELECT * FROM `accounts` WHERE `username` = %s "
        "AND `status` = 1", username)