# OCRbot

OCRbot is a Mastodon (and compatible, such as Pleroma) bot that uses OCR to automatically generate text descriptions of images. It reads the image and outputs what it thinks is the text contained, using [tesseract](https://github.com/tesseract-ocr/tesseract). **It requires Python 3.**

![Screenshot of OCRbot in action](https://lynnesbian.space/res/ceres/sshot_2019-02-21_at_14-41-06-1550724066.png)

## Working Example

A working version of OCRbot can be found [here](https://fedi.lynnesbian.space/@OCRbot). I'll always run the latest version, and the instance hosting it has a much higher character limit than Mastodon's default of 500 or Pleroma's default of 5000 (specifically, it has a limit of 65535 chars). If you'd like to run your own version that works differently (for example, maybe you want a version that works with Japanese text instead, or a version that uses a different OCR engine), then you're free to fork and modify!

## Installation
### Tesseract (Required)

- Debian/Ubuntu: `sudo apt install tesseract-ocr`
- Arch Linux: `sudo pacman -Syu tesseract tesseract-data-eng`

### OCRbot (Required)

```
git clone https://github.com/Lynnesbian/OCRbot/
cd OCRbot
pip3 install -r requirements.txt
```

## Running OCRbot
Copy or rename `config.sample.json` to `config.json`, and edit the settings as you wish. Most importantly, make sure you choose the instance your OCRbot account will post from. Then, run `main.py` and log in with the account you'd like OCRbot to post from. Finally, run `reply.py` and OCRbot will take care of the rest.

You can use something like systemd or SysVinit to manage running `reply.py` for you.

## Caveats
OCRbot is *not* designed to replace captions, merely to supplement them. It works best with plain black text on a plain white background. For example, PDF scans and Wikipedia screenshots will work great, but handwriting and distorted text won't. It will fail (at least partially) for:
- Anything using handwriting
- Anything that's not in English (although I'm planning on fixing this)
- Text that is skewed, rotated, stretched, or otherwise distorted
- Handwriting
- Heavily compressed images
- Text with layouts more complex than this page
- WordArt
- Unusual fonts
- Videos and GIFs
- Very large or very small text

So in short, please caption your images. Don't rely on OCRbot.

## Donating
Donations can be provided via [LiberaPay](https://liberapay.com/lynnesbian) (recurring), [PayPal](https://paypal.me/lynnesbian) (singular), or [Ko-fi](https://ko-fi.com/lynnesbian) (singular). Don't feel obligated to donate!

## License
Copyright (C)2019 Lynnesbian (https://fedi.lynnesbian.space/@lynnesbian)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

The full text of the license is provided under the name "LICENSE" in the root directory of this repository.
