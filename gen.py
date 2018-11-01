#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mastodon import Mastodon
import argparse, sys, traceback, json
import create

parser = argparse.ArgumentParser(description='Generate and post a toot.')
parser.add_argument('reply', metavar='reply', type=str, nargs='?', 
	help='ID of the status to reply to')
parser.add_argument('-s', '--simulate', dest='simulate', action='store_true',
	help="Print the toot to stdout without posting it")

args = parser.parse_args()

cfg = json.load(open('config.json'))

client = Mastodon(
  client_id=cfg['client']['id'],
  client_secret=cfg['client']['secret'], 
  access_token=cfg['secret'], 
  api_base_url=cfg['site'])

if __name__ == '__main__':
	toot = create.make_toot()
	if not args.simulate:
		try:
			if toot['media'] != None:
				mediaID = client.media_post(toot['media'], description = toot['toot'])
				client.status_post(toot['toot'].replace("\n", " "),
					media_ids = [mediaID], visibility = "unlisted")
			else:
				client.status_post(toot['toot'], visibility = 'unlisted')
		except Exception as err:
			toot = {
			"toot":
			"Mistress @lynnesbian@fedi.lynnesbian.space, something has gone terribly" \
			+ " wrong! While attempting to post a toot, I received the following" \
			+ " error:\n" + "\n".join(traceback.format_tb(sys.exc_info()[2]))
			}
			client.status_post(toot['toot'], visibility = 'unlisted', spoiler_text = "Error!")
	print(toot['toot'])
