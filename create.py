#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import markovify
import json
import re, random, multiprocessing, time, sqlite3, shutil, os

def make_sentence(output):
	class nlt_fixed(markovify.NewlineText):
		def test_sentence_input(self, sentence):
			return True #all sentences are valid <3

	# with open("corpus.txt", encoding="utf-8") as fp:
	#   model = nlt_fixed(fp.read())

	shutil.copyfile("toots.db", "toots-copy.db")
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
	sentence = re.sub("^@\u202B[^ ]* ", "", sentence)
	output.send(sentence)

def make_toot(force_markov = False, args = None):
	return make_toot_markov()

def make_toot_markov(query = None):
	tries = 0
	toot = None
	while toot == None and tries < 25:
		pin, pout = multiprocessing.Pipe(False)
		p = multiprocessing.Process(target = make_sentence, args = [pout])
		p.start()
		p.join(10)
		if p.is_alive():
			p.terminate()
			p.join()
			toot = None
			tries = tries + 1
		else:
			toot = pin.recv()
	if toot == None:
		toot = "Toot generation failed! Contact Lynne for assistance."
	return {
			"toot":toot,
			"media":None
		}
