# mstdn-ebooks

**Lynnear Edition**

This version makes quite a few changes from [the original](https://github.com/Jess3Jane/mastodon-ebooks), such as:
- Unicode support
- Non-Markov stuff
- Stores toots in a sqlite database rather than a text file
  - Doesn't unecessarily redownload all toots every time
  
## Install/usage guide
An installation and usage guide is available [here](https://cloud.lynnesbian.space/s/jozbRi69t4TpD95). It's primarily targeted at Linux, but it should be possible on BSD, macOS, etc. I've also put some effort into providing steps for Windows, but I can't make any guarantees as to its effectiveness.

## Original README
hey look it's an ebooks bot

python3

install the requirements with `sudo pip3 install -r requirements.txt`

make a bot (probably on bots in space) and follow the target accounts

run `python3 main.py` to login and scrape

run `python3 gen.py` to make a toot

cron is an okay choice to make it toot regularly
