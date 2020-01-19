#!/usr/bin/env python3
# OCRbot login code
# Copyright (C) 2020 Lynne (@lynnesbian@fedi.lynnesbian.space)

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

# specify defaults

cfg = {
	# "site": "https://botsin.space",
	"cw": "OCR Output",
	"ocr_threads": 8,
	"char_limit": 500,
	"default_language":"eng",
	"ui_language": "eng",
	"admin": "admin@example.com",
	"char_count_in_cw": True
}

scopes = ["read:statuses", "read:accounts", "write:statuses", "read:notifications", "read:search"]
try:
	cfg.update(json.load(open('config.json', 'r')))
except:
	print("No config.json found, creating default...")
	json.dump(cfg, open("config.json", "w+"))

if "site" not in cfg:
	print("Enter site to post from, e.g. https://botsin.space.")
	while "site" not in cfg:
		site = input("Site: ")
		if not re.match(r"^https:\/\/[^\/]+\/?$", site):
			print("Invalid input. Please format your input as 'https://[domain name]'.")
		else:
			cfg['site'] = site

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
print("Ready! To get started, run service.py.")
