#!/usr/bin/env python
# -*- encoding:UTF-8 -*-
import db


def generate_insert_sql(table, attrs, **kwargs):
    insert_names = ', '.join(attr for attr in attrs if attr in kwargs)
    values = ', '.join(kwargs[i] for i in attrs if i in kwargs)
    sql = u"""INSERT INTO {} ({}) VALUES ({});""".format(table, insert_names, values)
    return sql


def generate_update_sql(table, attrs, **kwargs):
    cond_clause = u', '.join(i + ' = ' + kwargs[i] for i in attrs if i in kwargs)
    sql = u"""UPDATE {} SET {} WHERE id = {};""".format(table, cond_clause, kwargs['id'])
    return sql

def generate_update_sql_ad_delivery_id(table, attrs, **kwargs):
    cond_clause = u', '.join(i + ' = ' + kwargs[i] for i in attrs if i in kwargs)
    sql = u"""UPDATE {} SET {} WHERE ad_delivery_id = {};""".format(table, cond_clause, kwargs['ad_delivery_id'])
    return sql


def generate_upsert_sql(table, attrs, **kwargs):
    if 'id' in kwargs:
        sql = generate_update_sql(table, attrs, **kwargs)
    else:
        sql = generate_insert_sql(table, attrs, **kwargs)
    return sql


def get_item_by_attr(table, name, value):
    sql = _generate_get_by_attr_sql(table, name, value)
    item = db.mysql.get(sql)
    return item


def get_items_by_attr(table, name, value):
    sql = _generate_get_by_attr_sql(table, name, value)
    item = db.mysql.query(sql)
    return item


def _generate_get_by_attr_sql(table, name, value):
    sql = "SELECT * FROM {} WHERE {} = {};"
    return sql.format(table, name, value)


def get_table_total_count(table):
    sql = 'SELECT COUNT(1) AS total FROM {};'.format(table)
    return db.mysql.get(sql)['total']


def delete_item_by_attr(table, name, value):
    sql = 'DELETE FROM {} WHERE {} = {};'.format(table, name, value)
    count = db.mysql.execute(sql)
    return count

def delete_item_by_attr_id(table, name, value):
    sql = 'DELETE FROM {} WHERE {} = {};'.format(table, name, value)
    lastrowid = db.mysql.execute(sql)
    return lastrowid


def update_item_by_attr(table, attr_name, attr_value, **kwargs):
    cond_clause = ', '.join(i + ' = ' + kwargs[i] for i in kwargs)
    sql = u'UPDATE {} SET {} WHERE {} = {};'.format(
        table, cond_clause, attr_name, attr_value)
    db.mysql.execute(sql)


def quote(value):
    return "\'" + value + "\'"


def datetime_toString(dt):
    return dt.strftime("%Y-%m-%d")
