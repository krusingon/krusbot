# bot.py

# A custom Twitch bot for Hex + MtG card searches
# Based on tutorial here: http://www.instructables.com/id/Twitchtv-Moderator-Bot/
# (The tutorial has several non-functioning bits)
# Uses regex expressions to parse twitch messages and to match card names

# You will need an OAUTH token through Twitch

# written for Python 3.6
# author: Kevin Kruse
# contact: Twitter @krusingon

from time import sleep
import socket
import re
import csv
import sys

HOST = "irc.chat.twitch.tv"         # the Twitch IRC server
PORT = 6667                         # always use port 6667!
NICK = "botname"           			# your Twitch username, lowercase
PASS = "oauth:" # your Twitch OAuth token
global CHAN
CHAN = "#channelname"              # the channel you want to join
RATE = 20/30						# messages per second
global MODE
MODE = "mtg"						# default card search mode

PATT = [
    r"swear",
    r"idiot"
]

COMM = [
	r"!hello",
	r"!part",
	r"!card",
	r"!mode",
	r"!addcom",
	r"!delcom",
	r"!"
]


def chat(sock, msg):
	"""
	Send a chat message to the server.
	Keyword arguments:
	sock -- the socket over which to send the message
	msg  -- the message to be sent
	"""
	sock.send("PRIVMSG {} :{}\r\n".format(CHAN, msg).encode("utf-8"))

def ban(sock, user):
	"""
	Ban a user from the current channel.
	Keyword arguments:
	sock -- the socket over which to send the ban command
	user -- the user to be banned
	"""
	chat(sock, ".ban {}".format(user))

def timeout(sock, user, secs=600):
	"""
	Time out a user for a set period of time.
	Keyword arguments:
	sock -- the socket over which to send the timeout command
	user -- the user to be timed out
	secs -- the length of the timeout in seconds (default 600)
	"""
	chat(sock, ".timeout {} {}".format(user, secs))

def command(sock, message):
	"""
	Process a command that has been recognized
	Keyword arguments:
	sock -- the socket over which to communicate
	message -- the entire message which started with a command
	"""
	#chat(sock, "the command was {}".format(message))
	global MODE
	global CHAN
	getargs = re.compile(r"!.*? ", re.IGNORECASE)
	args = getargs.sub("", message)
	# !mode to change to mtg or hex
	if re.match("!mode", message):
		print("this is a !mode command")
		if re.match("mtg", args):
			MODE = "mtg"
			chat(sock, "Changed mode to {}".format(MODE))
		elif re.match("hex", args):
			MODE = "hex"
			chat(sock, "Changed mode to {}".format(MODE))
		else:
			chat(sock, "My mode is {}".format(MODE))
	# explicitly look for a card
	elif re.match("!card", message):
		print("this is a !card command")
		card(sock, args)
	# force krusbot to leave. should probably restrict this to streamer-only command
	elif re.match("!part", message):
		print("I was asked to leave")
		chat(sock, "I was asked to leave. Goodbye! (message krusingon if you want me to come back)")
		sock.send("PART {}\r\n".format(CHAN).encode("utf-8"))
		sys.exit()
	#ignore some commands commonly used for mtgbot. not needed if output is suppressed when card isn't found
	elif re.match("!addcom", message):
		print("Ignoring an addcom")
	elif re.match("!delcom", message):
		print("Ignoring a delcom")
	#assume someone wanted to search a card
	else:
		print("no !command explicitly given, but I'll do a card search")
		getname = re.compile(r"!(.+)$", re.IGNORECASE)
		assumed_name = getname.match(message)
		assumed_card = assumed_name.group(1)
		print("assumed cardname is {}".format(assumed_card))
		card(sock, assumed_card)


def card(sock, cardname):
	"""
	Look up a card, taking into account whether it is hex or mtg
	Print the mode if no match is found
	Keyword arguments:
	sock -- the socket
	cardname -- the cardname, all on its own
	"""
	#chat(sock, "searching for the card {}".format(cardname))
	global match
	match = 0
	print("searching for |{}|".format(cardname))

	# search mtg .csv
	if MODE == "mtg":
		with open('cards/mtg.csv', encoding='utf-8') as file:
			reader = csv.reader(file, delimiter='|')
			for row in reader:
				if re.search(cardname, row[1], re.IGNORECASE):
					match = 1
					print("match is {}".format(row[1]))
					print(row)
					gettypes = re.compile(r"^", re.IGNORECASE)
					types = gettypes.sub("", row[3])
					# format based on card type
					if re.search("Creature", types) or re.search("Vehicle", types):
						chat(sock, "{} | {} | cost: {} | {} | P/T: {}/{}".format(row[1], row[3], row[5], row[10], row[7], row[8]))
					elif re.search("Instant", types) or re.search("Sorcery", types) or re.search("Enchantment", types):
						chat(sock, "{} | {} | cost: {} | {}".format(row[1], row[3], row[5], row[10]))
					elif re.search("Planeswalker", types):
						chat(sock, "{} | {} | cost: {} | {} | loyalty: {}".format(row[1], row[3], row[5], row[10], row[9]))
					elif re.search("Land", types):
						chat(sock, "{} | {} | {}".format(row[1], row[3], row[10]))
					break

	# search hex .csv
	elif MODE == "hex":
		with open('cards/hex.csv', encoding='utf-8') as file:
			reader = csv.reader(file, delimiter='|')
			for row in reader:
				if re.search(cardname, row[2], re.IGNORECASE):
					match = 1
					print("match is {}".format(row[2]))
					print(row)
					gettypes = re.compile(r"^", re.IGNORECASE)
					types = gettypes.sub("", row[5])
					# format based on card type
					if re.search("Troop", types):
						chat(sock, "{} | {} - {} | cost: {} | threshold: {} | {} | A/D: {}/{}".format(row[2], row[5], row[6], row[9], row[4], row[12], row[10], row[11]))
					elif re.search("Champion", types):
						chat(sock, "{} | {} - {} | {}".format(row[2], row[5], row[6], row[12]))
					elif re.search("Resource", types):
						chat(sock, "{} | {} | threshold: {} | {} | A/D: {}/{}".format(row[2], row[5], row[4], row[12], row[10], row[11]))
					elif re.search("Constant", types):
						chat(sock, "{} | {} | cost: {} | threshold: {} | {}".format(row[2], row[5], row[9], row[4], row[12]))
					elif re.search("Action", types):
						chat(sock, "{} | {} | cost: {} | threshold: {} | {}".format(row[2], row[5], row[9], row[4], row[12]))
					else: match = 0
					break


	if not match:
		#chat(sock, "Didn't find that card. My mode is {}. Type !mode mtg or !mode hex to change".format(MODE))
		print("Couldn't find card")


s = socket.socket()

# initiate connection to channel
s.connect((HOST, PORT))
s.send("PASS {}\r\n".format(PASS).encode("utf-8"))
s.send("NICK {}\r\n".format(NICK).encode("utf-8"))
s.send("JOIN {}\r\n".format(CHAN).encode("utf-8"))

# parse the chat message. normally looks like:
# :username!username@username.tmi.twitch.tv PRIVMSG #channel :message content
p=re.compile(r"(^:(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :)(.+)\r\n", re.IGNORECASE)


while True:
	response = s.recv(1024).decode("utf-8")
	# Twitch sends pings every 5 mins or so. respond to these
	if response == "PING :tmi.twitch.tv\r\n":
		print("found a ping")
		s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
		print("sent a pong")
	else:
		m = p.match(response)
		if m:
			username = m.group(2)
			message = m.group(3)

			print(username + ": " + message)
			# Search for "curse words," mostly used for debug
			for pattern in PATT:
				if re.search(pattern, message):
					#s.send("PRIVMSG {} :{} watch the swearing!\r\n".format(CHAN, username).encode("utf-8"))
					print("found a swear")
					break
			# Search for commands
			for comm in COMM:
				if re.match(comm, message):
					print("found a command")
					command(s, message)
					break
		# any messages that don't match a standard chat msg will be printed in the console
		else:
			print(response)
	sleep(1 / RATE)
