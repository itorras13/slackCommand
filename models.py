from app import db
from datetime import datetime
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy.orm import validates


class Game(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	completed = db.Column(db.Boolean)
	channel = db.Column(db.String(50))
	player_x = db.Column(db.String(50))
	player_o = db.Column(db.String(50))
	time_started=  db.Column(db.DateTime)

	def __init__(self, player_x, player_o, time_started, channel):
		self.completed = False
		self.player_x = player_x
		self.player_o = player_o
		self.channel = channel
		self.time_started = datetime.utcnow()

	def __repr__(self):
		return "<Game(completed='%r', player_x='%s', player_y='%s'>" % (self.completed, self.player_x, self.player_y)

class Turn(db.Model):
	__tablename__ = 'Turn'
	__table_args__ = (
        PrimaryKeyConstraint('game_id', 'position'),
    )
	game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
	piece = db.Column(db.String(50))
	position = db.Column(db.Integer)

	def __init__(self, game_id, piece, position):
		self.position = position
		self.piece = piece
		self.game_id = game_id

