#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mastodon import Mastodon
import argparse, sys, traceback, json
import functions

parser = argparse.ArgumentParser(description='Generate and post a toot.')
parser.add_argument('-s', '--simulate', dest='simulate', action='store_true',
	help="Print the toot without actually posting it. Use this to make sure your bot's actually working.")

args = parser.parse_args()

cfg = json.load(open('config.json'))

client = Mastodon(
  client_id=cfg['client']['id'],
  client_secret=cfg['client']['secret'], 
  access_token=cfg['secret'], 
  api_base_url=cfg['site'])

if __name__ == '__main__':
	toot = functions.make_toot()
	if not args.simulate:
		try:
			if toot['media'] != None:
				mediaID = client.media_post(toot['media'], description = toot['toot'])
				client.status_post(toot['toot'].replace("\n", " "),
					media_ids = [mediaID], visibility = "unlisted", spoiler_text = cfg['cw'])
			else:
				client.status_post(toot['toot'], visibility = 'unlisted', spoiler_text = cfg['cw'])
		except Exception as err:
			toot = {
			"toot": "An unknown error that should never happen occurred. Maybe it's because of the spoiler text, which is {}. If not, I have no idea what went wrong. This is an error message -- contact lynnesbian@fedi.lynnesbian.space for assistance.".format(cfg['cw'])
			}
			client.status_post(toot['toot'], visibility = 'unlisted', spoiler_text = "Error!")
	print(toot['toot'])
