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
				"toot": "An unknown error occurred. This is an error message -- contact lynnesbian@fedi.lynnesbian.space for assistance."
			}
			client.status_post(toot['toot'], visibility = 'unlisted', spoiler_text = "Error!")
	print(toot['toot'])
