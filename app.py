from flask import Flask, request, jsonify, abort
import os

app = Flask(__name__)

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