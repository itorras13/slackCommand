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

#Possible Positions on Board
positions = ['tl', 'tc', 'tr', 'ml', 'mc', 'mr', 'bl', 'bc', 'br']

@app.route('/')
def hello():
	return "Hey, not much to see here!"

@app.route('/ttt', methods=['POST'])
def tic_tac_toe():
	token = request.form.get('token', None)
	#This is to make sure incoming requests are from our team
	if token != os.environ['slackKey']:
		return jsonify({'text': 'Wrong token'})

	channel_id = request.form.get('channel_id', None)

	text = request.form.get('text', None)
	#Hardcoded words
	if text == 'help':
		return help_text()
	elif text == 'board':
		return show_board(channel_id)
	elif text == 'destroy':
		return close_game(channel_id)

	#Use regex to see if the text is a user to start a game or not
	user_name = request.form.get('user_name', None)
	user_pattern = re.compile('^@([a-z]|[0-9]){1,21}$')
	if user_pattern.match(text):
		return create_game(channel_id, user_name, text)
	else:
		return play_turn(channel_id, user_name, text)

#Ends a game if there is one in the current channel and returns response
def close_game(channel):
	game = Game.query.filter(Game.channel == channel, Game.completed == False).first()
	if game == None:
		return response('There is no game to end in this channel.', False)
	game.completed = True
	db.session.commit()
	return response('Game has been ended.', True)

#This is used to make responses all go through here
def response(text, to_channel, attachments = None):
	#In channel makes everyone will see and ephermal just the user that sent request
	if to_channel:
		response_type = 'in_channel'
	else:
		response_type = 'ephermal'
	return jsonify({
		'text': text,
		'response_type': response_type,
		'attachments': [attachments]
		}) 


#This plays the turn
def play_turn(channel, user, position):
	#Makes sure there is a game in channel, and that it is the users turn
	if position in positions:
		game = Game.query.filter(Game.channel == channel, Game.completed == False).first()
		if game == None:
			return response('There is no open game in this channel.', False)
		if user != game.players_turn:
			return response('It is not your turn or you are not in this game.', False)
		turn = Turn.query.filter(Turn.position == position, Turn.game_id == game.id).first()
		#Checks to see if the position is empty or not
		if turn.empty == False:
			return response('That position is already taken.', False)
		#then finds if user is Xs or Os and plays that piece
		if user == game.player_x:
			turn.piece = 'X'
			game.players_turn = game.player_o
		else:
			turn.piece = 'O'
			game.players_turn = game.player_x
		turn.empty = False
		db.session.commit()
		#Then chicks if game is done after every turn
		done, winning_piece = is_game_done(game.id)
		if done:
			if winning_piece == ' ':
				ending_text = 'It is a draw!'
			else:
				if winning_piece == 'X':
					winner = game.player_x
				else:
					winner = game.player_o
				winner_id = get_user_id(winner)
				ending_text = 'Congratulations to <@%s|%s>!\n' % (winner_id, winner)
				ending_text += 'You have won!!!!'
			board = show_board(channel, ending_text)
			game.completed = True
			db.session.commit()
			return board
		else:
			players_turn_id = get_user_id(game.players_turn)
			response_text = 'Play Made. <@%s|%s>, you are up!\n' % (players_turn_id, game.players_turn)
			return show_board(channel, response_text)
	else:
		return response('That is not a valid move, type `/ttt help` to see the moves.', False)

#Makes a dictionary of all the positions on a board and the piece
def get_position_dict(game_id):
	pos_dict = {}
	turns = Turn.query.filter(Turn.game_id == game_id).all()
	for turn in turns:
		pos_dict[turn.position] = turn.piece
	return pos_dict

#Checks to see if someone won or tied
def is_game_done(game_id):
	pos_dict = get_position_dict(game_id)
	#the 8 possible ways to win are checked
	if pos_dict['tl'] == pos_dict['tc'] and pos_dict['tc'] == pos_dict['tr'] and pos_dict['tr'] != ' ':
		return True, pos_dict['tl']
	elif pos_dict['ml'] == pos_dict['mc'] and pos_dict['mc'] == pos_dict['mr'] and pos_dict['mr'] != ' ':
		return True, pos_dict['ml']
	elif pos_dict['bl'] == pos_dict['bc'] and pos_dict['bc'] == pos_dict['br'] and pos_dict['br'] != ' ':
		return True, pos_dict['bl']
	elif pos_dict['tl'] == pos_dict['ml'] and pos_dict['ml'] == pos_dict['bl'] and pos_dict['bl'] != ' ':
		return True, pos_dict['tl']
	elif pos_dict['tc'] == pos_dict['mc'] and pos_dict['mc'] == pos_dict['bc'] and pos_dict['bc'] != ' ':
		return True, pos_dict['tc']
	elif pos_dict['tr'] == pos_dict['mr'] and pos_dict['mr'] == pos_dict['br'] and pos_dict['br'] != ' ':
		return True, pos_dict['tr']
	elif pos_dict['tl'] == pos_dict['mc'] and pos_dict['mc'] == pos_dict['br'] and pos_dict['br'] != ' ':
		return True, pos_dict['tl']
	elif pos_dict['tr'] == pos_dict['mc'] and pos_dict['mc'] == pos_dict['bl'] and pos_dict['bl'] != ' ':
		return True, pos_dict['tr']

	#Checks if all positions on board are filled in but no one won
	all_filed = True
	for position in positions:
		if pos_dict[position] == ' ':
			all_filed = False
			break
	return all_filed, ' '

#prints a string of a board
def show_board(channel, text = None):
	#first checks to make sure game is going on in channel
	game = Game.query.filter(Game.channel == channel, Game.completed == False).first()
	if not game:
		return response("There is no game going on in this channel", False)
	else:
		pos_dict = get_position_dict(game.id)
		board = '``` %s | %s | %s \n' % (pos_dict['tl'], pos_dict['tc'], pos_dict['tr'])
		board += '---+---+---\n'
		board += ' %s | %s | %s \n' % (pos_dict['ml'], pos_dict['mc'], pos_dict['mr'])
		board += '---+---+---\n'
		board += ' %s | %s | %s ```' % (pos_dict['bl'], pos_dict['bc'], pos_dict['br'])
		if text == None:
			players_turn_id = get_user_id(game.players_turn)
			text = 'Here is the board. We are waiting on <@%s|%s> to choose a move.' % (players_turn_id, game.players_turn)
		return response(text, True, {'text': board, 'mrkdwn_in': ['text', 'pretext']})

#Creates a new game in channel
def create_game(channel, user_name, text):
	#makes sure that the second user is a user in the team
	second_user = text.replace('@', '')
	second_user_id = get_user_id(second_user)
	if user_name == second_user:
		return response('You cannot play against yourself.', False)
	elif second_user_id:
		if db.session.query(Game).filter(Game.channel == channel, Game.completed == False).count():
			return response('Already a game in this Channel', False)
		else:
			#New game is added and then every position added to turns table
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

#Gets the user id of a user, also used to check if user is in team
def get_user_id(user):
	response = (requests.get('https://slack.com/api/users.list?pretty=1&token=' + os.environ['slackApiKey'])).json()
	members = response['members']
	for member in members:
		if user == member['name']:
			return member['id']
	return None

#the Text returned with help
def help_text():
	text = 'To start a game just enter `/ttt @a_user`.\n'
	text += 'Enter `/ttt board` to show board.\n'
	text += 'To make move, enter /ttt and one of the movements.\n'
	text += 'Movements include top,middle,bottm and left,center,right.\n'
	text += 'So to put your choice on top left you enter `/ttt tl`.\n'
	text += 'To end a game enter `/ttt destroy`.'
	return response(text, False)

if __name__ == "__main__":
    app.run()