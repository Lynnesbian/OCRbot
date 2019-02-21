#!/usr/bin/env python3
# toot downloader version two!!
# Copyright (C) 2019 Lynne (@lynnesbian@fedi.lynnesbian.space)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

from mastodon import Mastodon
from os import path
from bs4 import BeautifulSoup
import os, sqlite3, signal, sys, json, re, shutil
import requests
import functions

scopes = ["read:statuses", "read:accounts", "read:follows", "write:statuses", "read:notifications"]
try:
	cfg = json.load(open('config.json', 'r'))
except:
	shutil.copy2("config.sample.json", "config.json")
	cfg = json.load(open('config.json', 'r'))

#config.json *MUST* contain the instance URL, the instance blacklist (for dead/broken instances), and the CW text. if they're not provided, we'll fall back to defaults.
if 'site' not in cfg:
	cfg['website'] = "https://botsin.space"
if 'cw' not in cfg:
	cfg['cw'] = None
if 'instance_blacklist' not in cfg:
	cfg["instance_blacklist"] = [
		"bofa.lol",
		"witches.town"
	]

#if the user is using a (very!) old version that still uses the .secret files, migrate to the new method
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
	print("No application info -- registering application with {}".format(cfg['site']))
	client_id, client_secret = Mastodon.create_app("mstdn-ebooks",
		api_base_url=cfg['site'],
		scopes=scopes,
		website="https://github.com/Lynnesbian/mstdn-ebooks")

	cfg['client'] = {
		"id": client_id,
		"secret": client_secret
	}

if "secret" not in cfg:
	print("No user credentials -- logging in to {}".format(cfg['site']))
	client = Mastodon(client_id = cfg['client']['id'],
		client_secret = cfg['client']['secret'],
		api_base_url=cfg['site'])

	print("Open this URL and authenticate to give mstdn-ebooks access to your bot's account: {}".format(client.auth_request_url(scopes=scopes)))
	cfg['secret'] = client.log_in(code=input("Secret: "), scopes=scopes)

json.dump(cfg, open("config.json", "w+"))

def extract_toot(toot):
	toot = functions.extract_toot(toot)
	toot = toot.replace("@", "@\u200B") #put a zws between @ and username to avoid mentioning
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

for f in following:
	last_toot = c.execute("SELECT id FROM `toots` WHERE userid LIKE ? ORDER BY id DESC LIMIT 1", (f.id,)).fetchone()
	if last_toot != None:
		last_toot = last_toot[0]
	else:
		last_toot = 0
	print("Harvesting toots for user @{}, starting from {}".format(f.acct, last_toot))

	#find the user's activitypub outbox
	print("WebFingering... (do not laugh at this. WebFinger is a federated protocol. https://wikipedia.org/wiki/WebFinger)")
	instance = re.search(r"^.*@(.+)", f.acct)
	if instance == None:
		instance = re.search(r"https?:\/\/(.*)", cfg['site']).group(1)
	else:
		instance = instance.group(1)

	if instance in cfg['instance_blacklist']:
		print("skipping blacklisted instance: {}".format(instance))
		continue

	try:
		r = requests.get("https://{}/.well-known/host-meta".format(instance), timeout=10)
		uri = re.search(r'template="([^"]+)"', r.text).group(1)
		uri = uri.format(uri = "{}@{}".format(f.username, instance))
		r = requests.get(uri, headers={"Accept": "application/json"}, timeout=10)
		j = r.json()
		for link in j['links']:
			if link['rel'] == 'self':
				#this is a link formatted like "https://instan.ce/users/username", which is what we need
				uri = link['href']
		uri = "{}/outbox?page=true".format(uri)
		r = requests.get(uri, timeout=10)
		j = r.json()
	except Exception:
		print("oopsy woopsy!! we made a fucky wucky!!!\n(we're probably rate limited, please hang up and try again)")
		sys.exit(1)

	pleroma = False
	if 'first' in j and type(j['first']) != str:
		print("Pleroma instance detected")
		pleroma = True
		j = j['first']
	else:
		print("Mastodon/Misskey instance detected")
		uri = "{}&min_id={}".format(uri, last_toot)
		r = requests.get(uri)
		j = r.json()

	print("Downloading and saving toots", end='', flush=True)
	done = False
	try:
		while not done and len(j['orderedItems']) > 0:
			for oi in j['orderedItems']:
				if oi['type'] != "Create":
					continue #this isn't a toot/post/status/whatever, it's a boost or a follow or some other activitypub thing. ignore
				
				# its a toost baby
				content = oi['object']['content']
				if oi['object']['summary'] != None:
					#don't download CW'd toots. if you want your bot to download and learn from CW'd toots, replace "continue" with "pass". (todo: add a config.json option for this)
					continue
				toot = extract_toot(content)
				# print(toot)
				try:
					if pleroma:
						if c.execute("SELECT COUNT(*) FROM toots WHERE id LIKE ?", (oi['object']['id'],)).fetchone()[0] > 0:
							#we've caught up to the notices we've already downloaded, so we can stop now
							#you might be wondering, "lynne, what if the instance ratelimits you after 40 posts, and they've made 60 since main.py was last run? wouldn't the bot miss 20 posts and never be able to see them?" to which i reply, "it's called mstdn-ebooks not fediverse-ebooks. pleroma support is an afterthought"
							done = True
							break
					pid = re.search(r"[^\/]+$", oi['object']['id']).group(0)
					c.execute("REPLACE INTO toots (id, userid, uri, content) VALUES (?, ?, ?, ?)", (
						pid,
						f.id,
						oi['object']['id'],
						toot
						)
					)
					pass
				except:
					pass #ignore any toots that don't successfully go into the DB
			if not pleroma:
				r = requests.get(j['prev'], timeout=15)
			else:
				r = requests.get(j['next'], timeout=15)
			j = r.json()
			print('.', end='', flush=True)
		print(" Done!")
		db.commit()
	except:
		print("Encountered an error! Saving toots to database and moving to next followed account.")
		db.commit()

print("Done!")

db.commit()
db.execute("VACUUM") #compact db
db.commit()
db.close()