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
	from PIL import ImageOps
except ImportError:
	import Image
import requests
from mastodon import Mastodon, StreamListener
from bs4 import BeautifulSoup
import pyocr

from multiprocessing import Pool
import os, random, re, json, re, textwrap, sys, gettext

_ = gettext.gettext

cfg = json.load(open('config.json', 'r'))

print("Logging in...")

client = Mastodon(
	client_id=cfg['client']['id'],
	client_secret=cfg['client']['secret'],
	access_token=cfg['secret'],
	api_base_url=cfg['site'])
handle = "@{}@{}".format(client.account_verify_credentials()['username'], re.match("https://([^/]*)/?", cfg['site']).group(1)).lower()

def cw(toot):
	if cfg['char_count_in_cw']:
		return "{} (chars: {})".format(cfg['cw'], len(toot))
	return cfg['cw']


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

	for link in soup.select("a"): #convert <a href='https://example.com>example.com</a> to just https://example.com
		link.insert_after(link["href"])
		link.decompose()

	text = soup.get_text()
	text = re.sub("https://([^/]+)/(@[^ ]+)", r"\2@\1", text) #put mastodon-style mentions back in
	text = re.sub("https://([^/]+)/users/([^ ]+)", r"@\2@\1", text) #put pleroma-style mentions back in
	text = text.rstrip("\n") #remove trailing newline
	# text = re.sub(r"^@[^@]+@[^ ]+\s*", r"", text) #remove the initial mention
	text = text.lower() #treat text as lowercase for easier keyword matching
	return text

def error(message, acct, post_id, visibility):
	print("error: {}".format(message))
	temp_client = Mastodon(
		client_id=cfg['client']['id'],
		client_secret=cfg['client']['secret'],
		access_token=cfg['secret'],
		api_base_url=cfg['site'])
	temp_client.status_post(_("{}\n{}\nContact the admin ({}) for assistance.").format(acct, message, cfg['admin']), post_id, visibility = visibility, spoiler_text = "Error")

def process_mention(client, notification):
	acct = "@" + notification['account']['acct'] #get the account's @
	print("mention detected")
	post = None
	no_images = True
	visibility = "unlisted"
	post_id = notification['status']['id']
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
			# the person is either replying to nothing, or the post they're replying to hasn't federated yet.
			# we'll assume the latter first.
			try:
				# get instance, e.g. mastodon.social from https://mastodon.social/blah/blah
				temp_instance = re.match(r"(https://[^/]+)", notification['status']['uri']).group(1)
				temp_client = Mastodon(api_base_url=temp_instance)
				# get status, e.g. 12345 from https://instan.ce/statuses/blah/12345
				temp_status = re.match(r".*/([^/]+)").group(1)
				temp_toot = temp_client.status(temp_status)
				if temp_toot['in_reply_to_id'] != None:
					# we found the post!!
					post = temp_client.status(temp_toot['in_reply_to_id'])
				else:
					error(_("Couldn't find any media."), acct, post_id, visibility)
					return
			except Exception as e:
				error(_("Failed to find post containing image. This may be a federation issue, or you may have tagged OCRbot in a conversation without an image.\nDebug info:\n{}, {}".format(type(e), e), acct, post_id, visibility))
				return

	if post != None:
		print("found post with media, extracting content")
		toot = ""
		mention = extract_toot(notification['status']['content'])
		print("parsing mention: {}".format(mention))
		search = re.search("{}\\s(\\w+)".format(handle), mention)
		lang = cfg['default_language']
		if search != None:
			lang = search.group(1)
			found = False
			print("checking for language: {}".format(lang))
			if lang not in language_dict:
				for code in language_dict:
					for name in language_dict[code]:
						if lang == name:
							lang = code
							found = True
							break
			else:
				found = True

			# fixes for language codes not described by tesseract
			replacements = {
				"chi": "chi_sim",
				"zho": "chi_sim"
			}

			for code, replacement in replacements.items():
				if lang == code:
					lang = replacement
					break

			if not found:
				# fall back to default, because we didn't understand this language name
				toot += _("\n(Couldn't find a language with the name '{}', falling back to default.)\n").format(lang)
				lang = cfg['default_language']

			else:
				# now that we have a language code, we need to see if the tesseract language pack is actually installed
				if lang not in langs:
					toot += _("\n(Your requested language may be supported by OCRbot. Unfortunately, the necessary tesseract data package is not installed. Contact the admin ({}) and ask them to install language support for {}, if at all possible.)\n").format(cfg['admin'], lang)
					lang = cfg['default_language']

		# the actual OCR

		visibility = post['visibility']
		if visibility == "public":
			visibility = "unlisted"

		i = 0
		failed = 0
		for media in post['media_attachments']:
			if media['type'] == "image":
				i += 1
				no_images = False
				print("downloading image {}".format(i))
				try:
					image = Image.open(requests.get(media['url'], stream = True, timeout = 30).raw)
				except:
					error(_("Failed to read image. Download may have timed out."), acct, post_id, visibility)
					return

				image = check_image_background(image)


				try:
					print(lang)
					out = tool.image_to_string(image, lang).replace("|", "I") # tesseract often mistakenly identifies I as a |
					out = re.sub("(?:\n\s*){3,}", "\n\n", out) #replace any group of 3+ linebreaks with just two
					if out == "":
						failed += 1
						out = _("Couldn't read this image, sorry!\nOCRbot works best with plain black text on a plain white background. Here is some information about what it can and can't do: https://github.com/Lynnesbian/OCRbot/blob/master/README.md#caveats")

					if len(post['media_attachments']) > 1:
						# more than one image, need to seperate them
						toot += "\nImage {}:\n{}\n".format(i, out)
					else:
						# only one image -- don't bother saying "image 1"
						toot += "\n{}".format(out)

				except:
					error(_("Failed to run tesseract. Specified language was: {}").format(lang), acct, post_id, visibility)
					raise
					return
		if no_images:
			error(_("Specified post has no images."), acct, post_id, visibility)
			return

		toot = toot.replace("@", "@\u200B") # don't mistakenly @ people
		toot = acct + toot # prepend the @
		if toot.replace("\n", "").replace(" ", "") != "":
			# toot isn't blank -- go ahead
			if failed == i:
				# transcribing failed for every image
				error(out, acct, post_id, visibility)
				return
			if len(toot + cw(toot)) < cfg['char_limit']:
				client.status_post(toot, post_id, visibility=visibility, spoiler_text = cw(toot)) # send toost
			else:
				wrapped = textwrap.wrap(toot, cfg['char_limit'] - len(cw(toot)) - len(acct) - 1)
				first = False
				for post in wrapped:
					if not first:
						first = True
					else:
						post = acct + "\n" + post
					post_id = client.status_post(post, post_id, visibility=visibility, spoiler_text = cw(toot))['id']
		else:
			# it's blank :c
			error(_("Tesseract returned no text."), acct, post_id, visibility)
	else:
		error(_("Failed to find post with media attached."), acct, post_id, visibility)

def convert_to_bw(image):
	gray = image.convert('L')
	# decide what is black and what is white. Very basic as it doesn't need to be nice.
	gray.point(lambda x: 0 if x < 128 else 255, '1')
	return gray

def check_image_background(image):
	im = convert_to_bw(image)
	im.show()
	im_smol = im.resize((int(x / 4) for x in im.size), Image.NEAREST)
	im_smol.show()
	pixels = im_smol.getdata()
	black_threshold = 150 # Threshold doesnt really matter as the image is only 0 and 255
	nblack = 0
	n = len(pixels)
	for pixel in pixels:
		if pixel < black_threshold:
			nblack += 1

	if (nblack / float(n)) > 0.5:
		image = invert_image(image) # Invert image is more than half of the bw image is considered black
	image.show()
	return image

def invert_image(image):
	if image.mode == 'RGBA':
		# Remove alpha channel before inverting image then re-add it
		r, g, b, a = image.split()
		rgb_image = Image.merge('RGB', (r, g, b))
		inverted_image = ImageOps.invert(rgb_image)
		r2, g2, b2 = inverted_image.split()
		final_transparent_image = Image.merge('RGBA', (r2, g2, b2, a))
		return final_transparent_image
	else:
		inverted_image = ImageOps.invert(image)
		return inverted_image


class ReplyListener(StreamListener):
	def __init__(self):
		self.pool = Pool(cfg['ocr_threads'])

	def on_notification(self, notification): #listen for notifications
		if notification['type'] == 'mention': #if we're mentioned:
			self.pool.apply_async(process_mention, args=(client, notification))


tools = pyocr.get_available_tools()
if len(tools) == 0:
	print(_("No OCR tools found. Please install tesseract-ocr and/or libtesseract."))
	sys.exit(1)

tool = tools[0]
print("Using {}".format(tool.get_name()))

language_dict = json.load(open("language-codes.json"))

langs = tool.get_available_languages()
langs.remove("osd") # remove orientation and script detection from the list, as it's not actually a language
print("Available languages: {}".format(", ".join(langs)))
if cfg['default_language'] not in langs:
	print("{} is not a supported language. Please edit default_language in config.json to choose a supported option.")
	sys.exit(1)
if cfg['char_limit'] < len(cw("test")) + 1:
	print("Character limit is too low. It must be at least ~{}, preferably more. Try setting it to the character limit on {}.".format(len(cw("test")) + 50), cfg['site'])
print("Starting OCRbot.")

rl = ReplyListener()
client.stream_user(rl) #go!
