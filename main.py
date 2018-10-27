#!/usr/bin/env python3
# toot downloader version two!!
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mastodon import Mastodon
from os import path
from bs4 import BeautifulSoup
import os, sqlite3, signal, sys, json, re
import requests

scopes = ["read:statuses", "read:accounts", "read:follows", "write:statuses"]
cfg = json.load(open('config.json', 'r'))

if os.path.exists("clientcred.secret"):
		print("Upgrading to new storage method")
		cc = open("clientcred.secret").read().split("\n")
		cfg['client'] = {
				"id": cc[0],
				"secret": cc[1]
		}
		cfg['secret'] = open("usercred.secret").read().rstrip("\n")
		os.remove("clientcred.secret")
		os.remove("usercred.secret")
		

if "client" not in cfg:
	print("No client credentials, registering application")
	client_id, client_secret = Mastodon.create_app("mstdn-ebooks",
		api_base_url=cfg['site'],
		scopes=scopes,
		website="https://github.com/Lynnesbian/mstdn-ebooks")

	cfg['client'] = {
		"id": client_id,
		"secret": client_secret
	}

if "secret" not in cfg:
	print("No user credentials, logging in")
	client = Mastodon(client_id = cfg['client']['id'],
		client_secret = cfg['client']['secret'],
		api_base_url=cfg['site'])

	print("Open this URL: {}".format(client.auth_request_url(scopes=scopes)))
	cfg['secret'] = client.log_in(code=input("Secret: "), scopes=scopes)

json.dump(cfg, open("config.json", "w+"))

def extract_toot(toot):
	toot = toot.replace("&apos;", "'")
	toot = toot.replace("&quot;", '"')
	soup = BeautifulSoup(toot, "html.parser")
	
	# this is the code that removes all mentions
	# TODO: make it so that it removes the @ and instance but keeps the name
	for mention in soup.select("span.h-card"):
		mention.a.unwrap()
		mention.span.unwrap()
	
	# replace <br> with linebreak
	for lb in soup.select("br"):
		lb.insert_after("\n")
		lb.decompose()

	# replace <p> with linebreak
	for p in soup.select("p"):
		p.insert_after("\n")
		p.unwrap()
	
	# fix hashtags
	for ht in soup.select("a.hashtag"):
		ht.unwrap()

	# fix links
	for link in soup.select("a"):
		link.insert_after(link["href"])
		link.decompose()

	toot = soup.get_text()
	toot = toot.rstrip("\n") #remove trailing newline
	toot = toot.replace("@", "@\u202B") #put a zws between @ and username to avoid mentioning
	return(toot)

client = Mastodon(
	client_id=cfg['client']['id'],
	client_secret = cfg['client']['secret'], 
	access_token=cfg['secret'], 
	api_base_url=cfg['site'])

me = client.account_verify_credentials()
following = client.account_following(me.id)

db = sqlite3.connect("toots.db")
db.text_factory=str
c = db.cursor()
c.execute("CREATE TABLE IF NOT EXISTS `toots` (id INT NOT NULL UNIQUE PRIMARY KEY, userid INT NOT NULL, uri VARCHAR NOT NULL, content VARCHAR NOT NULL) WITHOUT ROWID")
db.commit()

def handleCtrlC(signal, frame):
	print("\nPREMATURE EVACUATION - Saving chunks")
	db.commit()
	sys.exit(1)

signal.signal(signal.SIGINT, handleCtrlC)

def get_toots_legacy(client, id):
	i = 0
	toots = client.account_statuses(id)
	while toots is not None and len(toots) > 0:
		for toot in toots:
			if toot.spoiler_text != "": continue
			if toot.reblog is not None: continue
			if toot.visibility not in ["public", "unlisted"]: continue
			t = extract_toot(toot.content)
			if t != None:
				yield {
					"toot": t,
					"id": toot.id,
					"uri": toot.uri
				}
			toots = client.fetch_next(toots)
			i += 1
			if i%20 == 0:
				print('.', end='', flush=True)

for f in following:
	last_toot = c.execute("SELECT id FROM `toots` WHERE userid LIKE ? ORDER BY id DESC LIMIT 1", (f.id,)).fetchone()
	if last_toot != None:
		last_toot = last_toot[0]
	else:
		last_toot = 0
	print("Harvesting toots for user @{}, starting from {}".format(f.acct, last_toot))

	#find the user's activitypub outbox
	print("WebFingering...")
	instance = re.search(r"^.*@(.+)", f.acct)
	if instance == None:
		instance = re.search(r"https?:\/\/(.*)", cfg['site']).group(1)
	else:
		instance = instance.group(1)

	if instance == "bofa.lol":
		print("rest in piece bofa, skipping")
		continue
				
	# print("{} is on {}".format(f.acct, instance))
	try:
		r = requests.get("https://{}/.well-known/host-meta".format(instance))
		uri = re.search(r'template="([^"]+)"', r.text).group(1)
		uri = uri.format(uri = "{}@{}".format(f.username, instance))
		r = requests.get(uri, headers={"Accept": "application/json"})
		j = r.json()
		if len(j['aliases']) == 1: #TODO: this is a hack on top of a hack, fix it
			uri = j['aliases'][0]
		else:
			uri = j['aliases'][1]
		uri = "{}/outbox?page=true&min_id={}".format(uri, last_toot)
		r = requests.get(uri)
		j = r.json()
	except Exception:
		print("oopsy woopsy!! we made a fucky wucky!!!\n(we're probably rate limited, please hang up and try again)")
		sys.exit(1)

	pleroma = False
	if 'first' in j:
		print("{} is a pleroma instance -- falling back to legacy toot collection method".format(instance))
		pleroma = True
	
	print("Downloading and parsing toots", end='', flush=True)
	current = None
	try:
		if pleroma:
			for t in get_toots_legacy(client, f.id):
				try:
					c.execute("REPLACE INTO toots (id, userid, uri, content) VALUES (?, ?, ?, ?)",
						(t['id'],
						f.id,
						t['uri'],
						t['toot']
						)
					)
				except:
					pass

		else:
			while len(j['orderedItems']) > 0:
				for oi in j['orderedItems']:
					if (not pleroma and oi['type'] == "Create") or (pleroma and oi['to']['type'] == "Create"):
						# its a toost baby
						content = oi['object']['content']
						if oi['object']['summary'] != None:
							#don't download CW'd toots
							continue
						toot = extract_toot(content)
						# print(toot)
						try:
							pid = re.search(r"[^\/]+$", oi['object']['id']).group(0)
							c.execute("REPLACE INTO toots (id, userid, uri, content) VALUES (?, ?, ?, ?)",
								(pid,
								f.id,
								oi['object']['id'],
								toot
								)
							)
							pass
						except:
							pass #ignore any toots that don't go into the DB
				# sys.exit(0)
				r = requests.get(j['prev'])
				j = r.json()
				print('.', end='', flush=True)
		print(" Done!")
		db.commit()
	except:
		print("Encountered an error! Saving toots to database and exiting.")
		db.commit()
		db.close()
		sys.exit(1)

db.commit()
db.execute("VACUUM") #compact db
db.commit()
db.close()