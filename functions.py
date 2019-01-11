#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import markovify
from bs4 import BeautifulSoup
import re, random, multiprocessing, sqlite3, shutil, os, json

def make_sentence(output):
	class nlt_fixed(markovify.NewlineText): #modified version of NewlineText that never rejects sentences
		def test_sentence_input(self, sentence):
			return True #all sentences are valid <3

	shutil.copyfile("toots.db", "toots-copy.db") #create a copy of the database because reply.py will be using the main one
	db = sqlite3.connect("toots-copy.db")
	db.text_factory=str
	c = db.cursor()
	toots = c.execute("SELECT content FROM `toots`").fetchall()
	toots_str = ""
	for toot in toots:
		toots_str += "\n{}".format(toot[0])
	model = nlt_fixed(toots_str)
	toots_str = None
	db.close()
	os.remove("toots-copy.db")

	sentence = None
	tries = 0
	while sentence is None and tries < 10:
		sentence = model.make_short_sentence(500, tries=10000)
		tries = tries + 1

	sentence = re.sub("^(?:@\u202B[^ ]* )*", "", sentence) #remove leading pings (don't say "@bob blah blah" but still say "blah @bob blah")
	sentence = re.sub("^(?:@\u200B[^ ]* )*", "", sentence)

	output.send(sentence)

def make_toot(force_markov = False, args = None):
	return make_toot_markov()

def make_toot_markov(query = None):
	tries = 0
	toot = None
	while toot == None and tries < 10: #try to make a toot 10 times
		pin, pout = multiprocessing.Pipe(False)
		p = multiprocessing.Process(target = make_sentence, args = [pout])
		p.start()
		p.join(10) #wait 10 seconds to get something
		if p.is_alive(): #if it's still trying to make a toot after 10 seconds
			p.terminate()
			p.join()
			toot = None
			tries = tries + 1 #give up, and increment tries by one
		else:
			toot = pin.recv()
	if toot == None: #if we've tried and failed ten times, just give up
		toot = "Toot generation failed! Contact Lynne (lynnesbian@fedi.lynnesbian.space) for assistance."
	return {
			"toot": toot,
			"media": None
		}

def extract_toot(toot):
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

	toot = soup.get_text()
	text = re.sub("https://([^/]+)/(@[^ ]+)", r"\2@\1", text) #put mastodon-style mentions back in
	text = re.sub("https://([^/]+)/users/([^ ]+)", r"@\2@\1", text) #put pleroma-style mentions back in
	text = text.rstrip("\n") #remove trailing newline
	return text