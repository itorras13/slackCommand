from flask import Flask, request, jsonify, abort
import requests
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import os
import re

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

from models import *

positions = ['tl', 'tc', 'tr', 'ml', 'mc', 'mr', 'bl', 'bc', 'br']

@app.route('/')
def hello():
	return "Hey, not much to see here!"

@app.route('/ttt', methods=['POST'])
def tic_tac_toe():
	token = request.form.get('token', None)
	if token != os.environ['slackKey']:
		return jsonify({'text': 'Wrong token'})

	channel_id = request.form.get('channel_id', None)

	text = request.form.get('text', None)
	if text == 'help':
		return help_text()
	elif text == 'board':
		return show_board(channel_id)
	elif text == 'destroy':
		return close_game(channel_id)

	user_name = request.form.get('user_name', None)
	user_pattern = re.compile('^@([a-z]|[0-9]){1,21}$')
	if user_pattern.match(text):
		return create_game(channel_id, user_name, text)
	else:
		return play_turn(channel_id, user_name, text)

def close_game(channel):
	game = Game.query.filter(Game.channel == channel, Game.completed == False).first()
	if game == None:
		return response('There is no game to end in this channel.', False)
	game.completed = True
	db.session.commit()
	return response('Game has been ended.', True)

def response(text, to_channel, attachments = None):
	if to_channel:
		response_type = 'in_channel'
	else:
		response_type = 'ephermal'
	return jsonify({
		'text': text,
		'response_type': response_type,
		'attachments': [attachments]
		}) 


def play_turn(channel, user, position):
	if position in positions:
		game = Game.query.filter(Game.channel == channel, Game.completed == False).first()
		if game == None:
			return response('There is no open game in this channel.', False)
		if user != game.players_turn:
			return response('It is not your turn or you are not in this game.', False)
		turn = Turn.query.filter(Turn.position == position, Turn.game_id == game.id).first()
		if turn.empty == False:
			return response('That position is already taken.', False)
		if user == game.player_x:
			turn.piece = 'X'
			game.players_turn = game.player_o
		else:
			turn.piece = 'O'
			game.players_turn = game.player_x
		turn.empty = False
		db.session.commit()
		done, winning_piece = is_game_done(game.id)
		if done:
			if winning_piece == 'X':
				winner = game.player_x
			else:
				winner = game.player_o
			winner_id = get_user_id(winner)
			winning_text = 'Congratulations to <@' + winner_id + '|' + winner + '>!\n'
			winning_text += 'You have won!!!!'
			board = show_board(channel, winning_text)
			game.completed = True
			db.session.commit()
			return board
		else:	
			return show_board(channel, 'Play Made')
	else:
		return response('That is not a valid move, type `/ttt help` to see the moves.', False)

def get_turn_dict(game_id):
	turn_dict = {}
	turns = Turn.query.filter(Turn.game_id == game_id).all()
	for turn in turns:
		turn_dict[turn.position] = turn.piece
	return turn_dict

def is_game_done(game_id):
	turn_dict = get_turn_dict(game_id)
	finished = False
	winning_piece = ' '
	if turn_dict['tl'] == turn_dict['tc'] and turn_dict['tc'] == turn_dict['tr'] and turn_dict['tr'] != ' ':
		finished = True
		winning_piece = turn_dict['tl']
	elif turn_dict['ml'] == turn_dict['mc'] and turn_dict['mc'] == turn_dict['mr'] and turn_dict['mr'] != ' ':
		finished = True
		winning_piece = turn_dict['ml']
	elif turn_dict['bl'] == turn_dict['bc'] and turn_dict['bc'] == turn_dict['br'] and turn_dict['br'] != ' ':
		finished = True
		winning_piece = turn_dict['bl']
	elif turn_dict['tl'] == turn_dict['ml'] and turn_dict['ml'] == turn_dict['bl'] and turn_dict['bl'] != ' ':
		finished = True
		winning_piece = turn_dict['tl']
	elif turn_dict['tc'] == turn_dict['mc'] and turn_dict['mc'] == turn_dict['bc'] and turn_dict['bc'] != ' ':
		finished = True
		winning_piece = turn_dict['tc']
	elif turn_dict['tr'] == turn_dict['mr'] and turn_dict['mr'] == turn_dict['br'] and turn_dict['br'] != ' ':
		finished = True
		winning_piece = turn_dict['tr']
	elif turn_dict['tl'] == turn_dict['mc'] and turn_dict['mc'] == turn_dict['br'] and turn_dict['br'] != ' ':
		finished = True
		winning_piece = turn_dict['tl']
	elif turn_dict['tr'] == turn_dict['mc'] and turn_dict['mc'] == turn_dict['bl'] and turn_dict['bl'] != ' ':
		finished = True
		winning_piece = turn_dict['tr']
	return finished, winning_piece

def show_board(channel, text = None):
	game = Game.query.filter(Game.channel == channel, Game.completed == False).first()
	if not game:
		return response("There is no game going on in this channel", False)
	else:
		turn_dict = get_turn_dict(game.id)
		board = '``` %s | %s | %s \n' % (turn_dict['tl'], turn_dict['tc'], turn_dict['tr'])
		board += '---+---+---\n'
		board += ' %s | %s | %s \n' % (turn_dict['ml'], turn_dict['mc'], turn_dict['mr'])
		board += '---+---+---\n'
		board += ' %s | %s | %s ```' % (turn_dict['bl'], turn_dict['bc'], turn_dict['br'])
		if text == None:
			text = 'Here is the board'
		return response(text, True, {'text': board, 'mrkdwn_in': ['text', 'pretext']})

def create_game(channel, user_name, text):
	second_user = text.replace('@', '')
	second_user_id = get_user_id(second_user)
	if user_name == second_user:
		return response('You cannot play against yourself.', False)
	elif second_user_id:
		if db.session.query(Game).filter(Game.channel == channel, Game.completed == False).count():
			return response('Already a game in this Channel', False)
		else:
			new_game = Game(user_name, second_user, channel)
			db.session.add(new_game)
			db.session.commit()
			for position in positions:
				new_position = Turn(new_game.id, ' ', position)
				db.session.add(new_position)
			db.session.commit()
			return response('Game has begun! <@' + second_user_id + '|' + second_user + '> get ready!', True)
	else:
		return response(second_user + ' is not a person.', False)

def get_user_id(user):
	response = (requests.get('https://slack.com/api/users.list?pretty=1&token=' + os.environ['slackApiKey'])).json()
	members = response['members']
	for member in members:
		if user == member['name']:
			return member['id']
	return None


def help_text():
	text = 'To start a game just enter `/ttt @a_user`.\n'
	text += 'Enter `/ttt board` to show board.\n'
	text += 'To make move, enter /ttt and one of the movements.\n'
	text += 'Movements include top,middle,bottm and left,center,right.\n'
	text += 'So to put your choice on top left you enter `/ttt tl`.\n'
	return response(text, False)

if __name__ == "__main__":
    app.run()