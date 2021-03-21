# metadater

> A tool that adds date and location to the photos (and other files) based on EXIF, filenames and Google Photos JSON

Initially I created this script to retag the photos I exported from Google Photos, since they all had the today's date. This script now can be used for all sorts of photos.

This script finds the photo metadata (more specifically, date, time, and location of the shot) in EXIF tags, Google Photos JSON or file name (date and time only).

The Google Photos JSON can be acquired when you export ypur photos with Google Takeout

## Usage

Clone the repo. Then, install the (only) requirement:

```sh
pip install -r requirements.txt
```

Then launch the script:

```sh
# to only parse EXIF and JSON
python3 metadater.py -s "exif,json" ./input ./output

# to get date only from filename, while patterns "IMG_YYYYMMDD_HHMMSS*" and "YYYYMMDDHHMMSS*" are present
python3 metadater.py -s "filename" -n "IMG_%Y%m%d_%H%M%S,%Y%m%d%H%M%S" ./input ./output
```

See `python3 metadater.py --help` for more info.

## License

Unlicense © Nikita Karamov
