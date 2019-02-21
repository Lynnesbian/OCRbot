# OCRbot

OCRbot is a Mastodon (and compatible, such as Pleroma) bot that uses OCR to automatically generate text descriptions of images. It reads the image and outputs what it thinks is the text contained, using [tesseract](https://github.com/tesseract-ocr/tesseract). **It requires Python 3.**

![Screenshot of OCRbot in action](https://lynnesbian.space/res/ceres/sshot_2019-02-21_at_14-41-06-1550724066.png)

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
