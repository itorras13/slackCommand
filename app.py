from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import os

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

from models import *

@app.route('/')
def hello():
	return "Hey, not much to see here!"

@app.route('/ttt', methods=['POST'])
def tic_tac_toe():
	token = request.form.get('token', None)
	if token != os.environ['slackKey']:
		return jsonify({'text': 'Wrong token'})
	text = request.form.get('text', None)
	return jsonify({
	 	'text': token + ' ' + text
	})

if __name__ == "__main__":
    app.run()