#!/usr/bin/env python3
# Copyright (C) 2019 Lynne (@lynnesbian@fedi.lynnesbian.space)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

import mastodon
import os, random, re, json
import functions
from bs4 import BeautifulSoup

cfg = json.load(open('config.json', 'r'))

client = mastodon.Mastodon(
  client_id=cfg['client']['id'],
  client_secret=cfg['client']['secret'], 
  access_token=cfg['secret'], 
  api_base_url=cfg['site'])

def extract_toot(toot):
	text = functions.extract_toot(toot)
	text = re.sub(r"^@[^@]+@[^ ]+\s*", r"", text) #remove the initial mention
	text = text.lower() #treat text as lowercase for easier keyword matching (if this bot uses it)
	return text

class ReplyListener(mastodon.StreamListener):
	def on_notification(self, notification): #listen for notifications
		if notification['type'] == 'mention': #if we're mentioned:
			acct = "@" + notification['account']['acct'] #get the account's @
			post_id = notification['status']['id']
			mention = extract_toot(notification['status']['content'])
			toot = functions.make_toot(True)['toot'] #generate a toot
			toot = acct + " " + toot #prepend the @
			print(acct + " says " + mention) #logging
			visibility = notification['status']['visibility']
			if visibility == "public":
				visibility = "unlisted"
			client.status_post(toot, post_id, visibility=visibility, spoiler_text = cfg['cw']) #send toost
			print("replied with " + toot) #logging

rl = ReplyListener()
client.stream_user(rl) #go!
