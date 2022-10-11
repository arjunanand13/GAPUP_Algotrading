# -*- coding: utf-8 -*-
"""
Created on Wed Oct  6 15:23:50 2021

@author: akhil
"""

import imaplib
import email
import html
import re

host = 'imap.gmail.com'
username = 'Your email id'
password = 'Your password'


def get_otp():
    mail = imaplib.IMAP4_SSL(host)
    mail.login(username, password)
    mail.select("inbox")
    _, search_data = mail.search(None, 'FROM "accesscode@kotaksecurities.com"')
    my_message = []
    num = search_data[0].split()[-1]
    email_data = {}
    _, data = mail.fetch(num, '(RFC822)')
        # print(data[0])
    _, b = data[0]
    email_message = email.message_from_bytes(b)
    for header in ['subject', 'to', 'from', 'date']:
        email_data[header] = email_message[header]

    otp = re.search(r'\d\d\d\d', email_data['subject']).group()
    print(otp)
    return otp
