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
import os, json, re, shutil

scopes = ["read:statuses", "read:accounts", "write:statuses", "read:notifications"]
try:
	cfg = json.load(open('config.json', 'r'))
except:
	shutil.copy2("config.sample.json", "config.json")
	cfg = json.load(open('config.json', 'r'))

#config.json *should* contain the instance URL, the instance blacklist (for dead/broken instances), the instance character limit, and the CW text. if they're not provided, we'll fall back to defaults.
#TODO: clean this up
if 'site' not in cfg:
	cfg['website'] = "https://botsin.space"
if 'cw' not in cfg:
	cfg['cw'] = None
if 'instance_blacklist' not in cfg:
	cfg["instance_blacklist"] = [
		"bofa.lol",
		"witches.town"
	]	
if 'char_limit' not in cfg:
	cfg['char_limit'] = 500
if 'ocr_threads' not in cfg:
	cfg['ocr_threads'] = None

if "client" not in cfg:
	print("No application info -- registering application with {}".format(cfg['site']))
	client_id, client_secret = Mastodon.create_app("OCRbot",
		api_base_url=cfg['site'],
		scopes=scopes,
		website="https://github.com/Lynnesbian/OCRbot")

	cfg['client'] = {
		"id": client_id,
		"secret": client_secret
	}

if "secret" not in cfg:
	print("No user credentials -- logging in to {}".format(cfg['site']))
	client = Mastodon(client_id = cfg['client']['id'],
		client_secret = cfg['client']['secret'],
		api_base_url=cfg['site'])

	print("Open this URL and authenticate to give OCRbot access to your bot's account: {}".format(client.auth_request_url(scopes=scopes)))
	cfg['secret'] = client.log_in(code=input("Secret: "), scopes=scopes)

json.dump(cfg, open("config.json", "w+"))

client = Mastodon(
	client_id=cfg['client']['id'],
	client_secret = cfg['client']['secret'], 
	access_token=cfg['secret'], 
	api_base_url=cfg['site'])

me = client.account_verify_credentials()
