#!/usr/bin/python
# -*- coding: utf-8 -*-
import unicodedata
import datetime,time
from flask import Flask, session, request, render_template, redirect, url_for, Response



app = Flask(__name__)
app.secret_key = 'M@rekdsd*&6465445646asd!#$%'

app.client_id = '4246e027fcc217b24452'
app.client_secret = '41abfc5154c8d46b46143ec39b2f2bb2f756c0ac'


@app.route("/",methods=['POST','GET'])
@app.route("/index",methods=['POST','GET'])
def index():
    return render_template('dashboard.html')

@app.route("/search",methods=['POST','GET'])
def find():
    if request.method == "POST":
        project = request.form.get('project')
        return render_template('index.html')
    else:
        return "error"








if __name__ == "__main__":
    app.run(debug=True)