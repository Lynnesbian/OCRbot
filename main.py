#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mastodon import Mastodon
from os import path
from bs4 import BeautifulSoup
import shutil, os, sqlite3, signal, sys, json
# import re

scopes = ["read:statuses", "read:accounts", "read:follows", "write:statuses"]
cfg = json.load(open('config.json', 'r'))

if not path.exists("clientcred.secret"):

    print("No clientcred.secret, registering application")
    Mastodon.create_app("lynnesbian_mastodon_ebooks", api_base_url=cfg['site'], to_file="clientcred.secret", scopes=scopes, website="https://github.com/Lynnesbian/mastodon-ebooks")

if not path.exists("usercred.secret"):
    print("No usercred.secret, registering application")
    client = Mastodon(client_id="clientcred.secret", api_base_url=cfg['site'])
    print("Visit this url:")
    print(client.auth_request_url(scopes=scopes))
    client.log_in(code=input("Secret: "), to_file="usercred.secret", scopes=scopes)

def parse_toot(toot):
	if toot.spoiler_text != "": return
	if toot.reblog is not None: return
	if toot.visibility not in ["public", "unlisted"]: return

	soup = BeautifulSoup(toot.content, "html.parser")
	
	# pull the mentions out
	# for mention in soup.select("span.h-card"):
	#     mention.unwrap()

	# for mention in soup.select("a.u-url.mention"):
	#     mention.unwrap()

	# this is the code that removes all mentions
	# TODO: make it so that it removes the @ and instance but keeps the name
	for mention in soup.select("span.h-card"):
		mention.decompose()
	
	# make all linebreaks actual linebreaks
	for lb in soup.select("br"):
		lb.insert_after("\n")
		lb.decompose()

	# make each p element its own line because sometimes they decide not to be
	for p in soup.select("p"):
		p.insert_after("\n")
		p.unwrap()
	
	# keep hashtags in the toots
	for ht in soup.select("a.hashtag"):
		ht.unwrap()

	# unwrap all links (i like the bots posting links)
	for link in soup.select("a"):
		link.insert_after(link["href"])
		link.decompose()

	text = map(lambda a: a.strip(), soup.get_text().strip().split("\n"))

	# next up: store this and patch markovify to take it
	# return {"text": text, "mentions": mentions, "links": links}
	# it's 4am though so we're not doing that now, but i still want the parser updates
	#todo: we split above and join now, which is dumb, but i don't wanna mess with the map code bc i don't understand it uwu
	text = "\n".join(list(text)) 
	text = text.replace("&apos;", "'")
	return text

def get_toots(client, id, since_id):
	i = 0
	toots = client.account_statuses(id, since_id = since_id)
	while toots is not None and len(toots) > 0:
		for toot in toots:
			t = parse_toot(toot)
			if t != None:
				yield {
					"content": t,
					"id": toot.id
				}
		try:
			toots = client.fetch_next(toots)
		except TimeoutError:
			print("Operation timed out, committing to database and exiting.")
			db.commit()
			db.close()
			sys.exit(1)
		i += 1
		if i%10 == 0:
			print(i)

client = Mastodon(
		client_id="clientcred.secret", 
		access_token="usercred.secret", 
		api_base_url=cfg['site'])

me = client.account_verify_credentials()
following = client.account_following(me.id)

db = sqlite3.connect("toots.db")
db.text_factory=str
c = db.cursor()
c.execute("CREATE TABLE IF NOT EXISTS `toots` (id INT NOT NULL UNIQUE PRIMARY KEY, userid INT NOT NULL, content VARCHAR NOT NULL) WITHOUT ROWID")
db.commit()

def handleCtrlC(signal, frame):
	print("\nPREMATURE EVACUATION - Saving chunks")
	db.commit()
	sys.exit(1)

signal.signal(signal.SIGINT, handleCtrlC)

for f in following:
	last_toot = c.execute("SELECT id FROM `toots` WHERE userid LIKE ? ORDER BY id DESC LIMIT 1", (f.id,)).fetchone()
	if last_toot != None:
		last_toot = last_toot[0]
	else:
		last_toot = 0
	print("Downloading toots for user @{}, starting from {}".format(f.username, last_toot))
	for t in get_toots(client, f.id, last_toot):
		# try:
		c.execute("REPLACE INTO toots (id, userid, content) VALUES (?, ?, ?)", (t['id'], f.id, t['content']))
		# except:
		# 	pass #ignore toots that can't be encoded properly

db.commit()
db.execute("VACUUM") #compact db
db.commit()
db.close()