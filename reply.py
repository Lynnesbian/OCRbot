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
	from PIL import Image, ImageOps, ImageEnhance
except ImportError:
	import Image, ImageOps, ImageEnhance
import pytesseract
import requests
from mastodon import Mastodon, StreamListener
from bs4 import BeautifulSoup
import cv2
import numpy as np

from multiprocessing import Pool
import os, random, re, json, re

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
	acct = "@" + notification['account']['acct'] #get the account's @
	print("mention detected")
	post = None
	no_images = True
	if len(notification['status']['media_attachments']) != 0:
		post = notification['status']
	else:
		# get the post it's replying to
		try:
			print("fetching post being replied to")
			post = client.status(notification['status']['in_reply_to_id'])
			if len(post['media_attachments']) == 0:
				post = None
		except:
			client.status_post(acct + "\nFailed to find post containing image. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")

	if post != None:
		print("found post with media, extracting content")
		post_id = notification['status']['id']
		mention = extract_toot(post['content'])

		toot = ""

		# the actual OCR
		i = 0
		for media in post['media_attachments']:
			if media['type'] == "image":
				i += 1
				no_images = False
				print("downloading image {}".format(i))
				try:
					image = Image.open(requests.get(media['url'], stream = True, timeout = 30).raw)
				except:
					client.status_post(acct + "\nFailed to read image. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")
					return

				try:
					if False:
						# this part is switched off because it doesn't work at all :c
						print("downloaded image successfully, cleaning it up...")
						# image cleanup. most of these ideas come from this page: https://github.com/tesseract-ocr/tesseract/wiki/ImproveQuality
						# step 1: add a 10px white border around the image. this helps tesseract work with characters that are right on the edge of the image
						print("step 1/2")
						image = ImageOps.expand(image, 10, "white")
						# step 2: increase the sharpness
						print("step 2/3")
						enhancer = ImageEnhance.Sharpness(image)
						image = enhancer.enhance(1.5)
						# step 3: binarisation (making it so the pixels are either 100% black or 100% white)
						# tesseract does this by itself but the default method is kinda unreliable, so we'll use openCV
						print("step 3/3")
						print("converting to array")
						image = image.convert("L")
						image_array = np.asarray(image)
						print("binarising")
						image_array = cv2.adaptiveThreshold(image_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
						# # steps such as de-skewing and flattening the image are rather difficult to do, and the recommended python scripts linked in the article are standalone scripts. they're not on pypi and they seem to break with newer versions of openCV.

						# # convert image array back to pillow image
						print("converting to pillow image")
						image = Image.fromarray(image_array)

				except:
					client.status_post(acct + "\nFailed to process image. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")
					return
				try:
					out = pytesseract.image_to_string(image).replace("|", "I") # tesseract often mistakenly identifies I as a |
					out = re.sub("(?:\n\s*){3,}", "\n\n", out) #replace any group of 3+ linebreaks with just two
					if out == "":
						out = "Couldn't read this image, sorry!"

					if len(post['media_attachments']) > 1:
						# more than one image, need to seperate them
						toot += "\nImage {}:\n{}".format(i, out)
					else: 
						# only one image -- don't bother saying "image 1"
						toot += "\n{}".format(out)

				except:
					client.status_post(acct + "\nFailed to run tesseract. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")
					return

		toot = acct + toot #prepend the @
		visibility = post['visibility']
		if visibility == "public":
			visibility = "unlisted"
		if toot.replace("\n", "").replace(" ", "") != "":
			# toot isn't blank -- go ahead
			client.status_post(toot, post_id, visibility=visibility, spoiler_text = cfg['cw']) #send toost
		else:
			# it's blank :c
			client.status_post(acct + "\nGeneric error occurred. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")

	else:
		client.status_post(acct + "\nFailed to find post with media attached. Contact lynnesbian@fedi.lynnesbian.space for assistance.", post_id, visibility=visibility, spoiler_text = "Error")

class ReplyListener(StreamListener):
	def __init__(self):
		self.pool = Pool(cfg['ocr_threads'])

	def on_notification(self, notification): #listen for notifications
		if notification['type'] == 'mention': #if we're mentioned:
			# p = Process(target=process_mention, args=(client, notification))
			self.pool.apply_async(process_mention, args=(client, notification))
			

rl = ReplyListener()
client.stream_user(rl) #go!
