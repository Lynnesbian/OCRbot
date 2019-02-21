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
try:
	from PIL import Image
except ImportError:
	import Image
import pytesseract
import requests
from mastodon import Mastodon, StreamListener
from bs4 import BeautifulSoup

from multiprocessing import Pool
import os, random, re, json

cfg = json.load(open('config.json', 'r'))

client = Mastodon(
  client_id=cfg['client']['id'],
  client_secret=cfg['client']['secret'], 
  access_token=cfg['secret'], 
  api_base_url=cfg['site'])

def extract_toot(toot):
	toot = toot.replace("&apos;", "'") #convert HTML stuff to normal stuff
	toot = toot.replace("&quot;", '"') #ditto
	soup = BeautifulSoup(toot, "html.parser")
	for lb in soup.select("br"): #replace <br> with linebreak
		lb.insert_after("\n")
		lb.decompose()

	for p in soup.select("p"): #ditto for <p>
		p.insert_after("\n")
		p.unwrap()

	for ht in soup.select("a.hashtag"): #make hashtags no longer links, just text
		ht.unwrap()

	for link in soup.select("a"): #ocnvert <a href='https://example.com>example.com</a> to just https://example.com
		link.insert_after(link["href"])
		link.decompose()

	text = soup.get_text()
	text = re.sub("https://([^/]+)/(@[^ ]+)", r"\2@\1", text) #put mastodon-style mentions back in
	text = re.sub("https://([^/]+)/users/([^ ]+)", r"@\2@\1", text) #put pleroma-style mentions back in
	text = text.rstrip("\n") #remove trailing newline
	text = re.sub(r"^@[^@]+@[^ ]+\s*", r"", text) #remove the initial mention
	text = text.lower() #treat text as lowercase for easier keyword matching
	return text

def process_mention(client, notification):
	# for now we'll just ignore what the mention says, but in future we should check for a language name to use
	# first, we'll check if the mention contains at least one image. if so, we'll use that.
	# otherwise, we'll check if the post the mention is replying to (if any) contains any images.
	# if not, we'll give up.
	post = None
	no_images = True
	if len(notification['status']['media_attachments']) != 0:
		post = notification['status']
	else:
		# get the post it's replying to
		try:
			post = Mastodon.status(notification['status']['in_reply_to_id'])
			if len(post['media_attachments']) == 0:
				post = None
		except:
			pass # todo: specific error message?

	if post != None:
		acct = "@" + post['account']['acct'] #get the account's @
		post_id = post['id']
		mention = extract_toot(post['content'])

		# the actual OCR
		for media in post['media_attachments']:
			if media['type'] == "image":
				no_images = False
				try:
					i = Image.open(requests.get(media['url'], stream = True, timeout = 30).raw)
				except:
					client.status_post(acct + "\nFailed to read image. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")
				try:
					toot = pytesseract.image_to_string(i)
					toot = toot.replace("|", "I") # tesseract often mistakenly identifies I as a |
				except:
					client.status_post(acct + "\nFailed to run tesseract. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")

		toot = acct + "\n" + toot #prepend the @
		visibility = post['visibility']
		if visibility == "public":
			visibility = "unlisted"
		client.status_post(toot, post_id, visibility=visibility, spoiler_text = cfg['cw']) #send toost

	else:
		pass
		# post error message

class ReplyListener(StreamListener):
	def __init__(self):
		self.pool = Pool(cfg['ocr_threads'])

	def on_notification(self, notification): #listen for notifications
		if notification['type'] == 'mention': #if we're mentioned:
			# p = Process(target=process_mention, args=(client, notification))
			self.pool.apply_async(process_mention, args=(client, notification))
			

rl = ReplyListener()
client.stream_user(rl) #go!
