# Copyright (c) 2024, nidha and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns, data, report_summary = get_columns(filters), get_data(filters), get_report_summary(filters)
    message = "This is Report"
    return columns, data, message, None, report_summary

def get_columns(filters):
    columns = [
        {
            "fieldname": "name",
            "label": "ID",
            "fieldtype": "Link",
            "options": "Article",
            "width": 150
        },
        {
            "fieldname": "author",
            "label": "Author",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "publisher",
            "label": "Publisher",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "isbn",
            "label": "ISBN",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "status",
            "label": "Status",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "image",
            "label": "Image",
            "fieldtype": "Data",
            "width": 150x
        },
        {
            "fieldname": "issued_transaction",
            "label": "Total Issues",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "returned_transaction",
            "label": "Total Returns",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "current_status",
            "label": "Current Status",
            "fieldtype": "Data",
            "width": 100
        }
    ]
    return columns

def get_data(filters):
    filter_dict = {}

    if filters.name:
        filter_dict["name"] = filters.name

    if filters.author:
        filter_dict["author"] = ["like", f"%{filters.author}%"]

    if filters.publisher:
        filter_dict["publisher"] = ["like", f"%{filters.publisher}%"]

    if filters.isbn:
        filter_dict["isbn"] = ["like", f"%{filters.isbn}%"]

    if filters.status:
        filter_dict["status"] = ["like", f"%{filters.status}%"]

    if filters.get('image'):
        filter_dict["image"] = ["like", f"%{filters.image}%"]

    article_list = frappe.db.get_all("Article", filters=filter_dict, fields=["name", "author", "publisher", "isbn", "status", "image"])

    for article in article_list:
        article['issued_transaction'] = frappe.db.count("Library Transaction", filters={"article": article['name'], 'docstatus': 1, 'type': "Issue"})
        article['returned_transaction'] = frappe.db.count("Library Transaction", filters={"article": article['name'], 'docstatus': 1, 'type': "Return"})
        article['current_status'] = "Issued" if article['status'] == "Issued" else "Available"

    return article_list

def get_report_summary(filters):
    available_book = frappe.db.count("Article", filters={"status": "Available"})
    issued_book = frappe.db.count("Article", filters={"status": "Issued"})
    transactions_on_issue = frappe.db.count("Library Transaction", filters={"type": "Issue"})
    transactions_on_return = frappe.db.count("Library Transaction", filters={"type": "Return"})

    return [
        {
            "value": available_book,
            "label": _("Available Books"),
            "indicator": "Blue",
            "datatype": "Data"
        },
        {
            "value": issued_book,
            "label": _("Issued Books"),
            "indicator": "Blue",
            "datatype": "Data"
        },
        {
            "value": transactions_on_issue,
            "label": _("Transactions on Issue"),
            "indicator": "Red",
            "datatype": "Data"
        },
        {
            "value": transactions_on_return,
            "label": _("Transactions on Return"),
            "indicator": "Red",
            "datatype": "Data"
        }
    ]
