#!/usr/bin/env python3

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, List

from exif import Image, DATETIME_STR_FORMAT


def esc(code: int) -> str:
    """
    Converts the integer code to an ANSI escape sequence

    :param code: code
    :return: escape sequence
    """
    return f"\033[{code}m"


LatitudeDec = float
LongitudeDec = float
CoordinatesDec = Tuple[LatitudeDec, LongitudeDec]

DegMinSec = Tuple[int, int, float]
LatitudeDMS = Tuple[DegMinSec, str]
LongitudeDMS = Tuple[DegMinSec, str]
CoordinatesDMS = Tuple[LatitudeDMS, LongitudeDMS]


def coords_dms2dec(coords: CoordinatesDMS) -> CoordinatesDec:
    lat = coords[0][0][0] + (coords[0][0][1] / 60) + (coords[0][0][2] / 3600)
    lat *= 1 if coords[0][1] == "N" else -1
    lon = coords[1][0][0] + (coords[1][0][1] / 60) + (coords[1][0][2] / 3600)
    lon *= 1 if coords[1][1] == "E" else -1

    return lat, lon


def coords_dec2dms(coords: CoordinatesDec) -> CoordinatesDMS:
    lat_o = "N" if coords[0] >= 0 else "S"
    lat_d = int(abs(coords[0]))
    lat_m = int((abs(coords[0]) - lat_d) * 60)
    lat_s = ((abs(coords[0]) - lat_d) * 60 - lat_m) * 60

    lon_o = "E" if coords[1] >= 0 else "W"
    lon_d = int(abs(coords[1]))
    lon_m = int((abs(coords[1]) - lon_d) * 60)
    lon_s = ((abs(coords[1]) - lon_d) * 60 - lon_m) * 60

    return ((lat_d, lat_m, lat_s), lat_o), ((lon_d, lon_m, lon_s), lon_o)


def get_info_from_exif(
    image: Image,
) -> Tuple[Optional[datetime], Optional[CoordinatesDMS]]:
    date: Optional[datetime] = None
    location: Optional[CoordinatesDMS] = None

    if image.has_exif:
        try:
            date = datetime.fromtimestamp(int(image.datetime) / 1000)
        except ValueError:
            try:
                date = datetime.strptime(image.datetime, DATETIME_STR_FORMAT)
            except AttributeError or ValueError:
                pass
        except AttributeError:
            pass

        try:
            if (
                type(image.gps_latitude) is not tuple
                or type(image.gps_longitude) is not tuple
            ):
                return date, None

            location = (
                (image.gps_latitude, image.gps_latitude_ref),
                (image.gps_longitude, image.gps_longitude_ref),
            )

        except AttributeError:
            pass

    return date, location


def get_info_from_json(
    file: Path,
) -> Tuple[Optional[datetime], Optional[CoordinatesDMS]]:
    json_path = Path(str(file) + ".json")
    if not json_path.exists():
        return None, None

    with json_path.open("rb") as fo:
        json_dict = json.load(fo)

    date: Optional[datetime] = datetime.fromtimestamp(
        int(json_dict["photoTakenTime"]["timestamp"]), timezone.utc
    )

    location: Optional[CoordinatesDec] = (
        json_dict["geoData"]["latitude"],
        json_dict["geoData"]["longitude"],
    )

    return date, (coords_dec2dms(location) if location != (0, 0) else None)


def get_info_from_filename(
    file: Path, formats: list[str]
) -> tuple[Optional[datetime], Optional[CoordinatesDMS]]:
    date: Optional[datetime] = None

    for fstr in formats:
        try:
            file_stem_short = file.stem[: len(datetime.today().strftime(fstr))]
            date = datetime.strptime(file_stem_short, fstr)
            break
        except ValueError:
            continue

    return date, None


def process_one_file(
    in_file: Path, out_file: Path, strategies: List[str], formats: List[str]
):
    if not in_file.is_file():
        return

    if in_file.name.startswith("."):
        return

    if in_file.suffix == ".json":
        return

    print(f"{esc(1)}{esc(96)}{in_file.name}{esc(0)} =>\t", end="")

    date: Optional[datetime] = None
    location: Optional[CoordinatesDMS] = None
    image: Optional[Image] = None

    for strategy in reversed(strategies):
        strategy = strategy.lower()

        if strategy == "exif":
            try:
                with in_file.open("rb") as fo:
                    image = Image(fo)
            except Exception:
                image = None
                continue

            e_date, e_location = get_info_from_exif(image)
            date = e_date or date
            location = e_location or location

        elif strategy == "json":
            j_date, j_location = get_info_from_json(in_file)
            date = j_date or date
            location = j_location or location

        elif strategy == "filename":
            f_date, f_location = get_info_from_filename(in_file, formats)
            date = f_date or date
            location = f_location or location

    if date is None:
        print(f"{esc(91)}no date{esc(0)}, ", end="")
    else:
        print(f"{esc(92)}{date.isoformat()}{esc(0)}, ", end="")
        if image is not None:
            image.datetime = date.strftime(DATETIME_STR_FORMAT)

    if location is None:
        print(f"{esc(91)}no location{esc(0)}")
    else:
        print(f"{esc(92)}{coords_dms2dec(location)}{esc(0)}")
        if image is not None:
            try:
                (
                    (image.gps_latitude, image.gps_latitude_ref),
                    (image.gps_longitude, image.gps_longitude_ref),
                ) = location
            except TypeError:
                pass

    if image is not None:
        out_file.write_bytes(image.get_file())
    else:
        out_file.write_bytes(in_file.read_bytes())

    if date is not None:
        os.utime(out_file, (date.timestamp(), date.timestamp()))


def process_files(
    in_dir: Path, out_dir: Path, strategies: list[str], formats: list[str]
):
    if not in_dir.exists():
        raise FileNotFoundError("Input directory does not exist")

    if not in_dir.is_dir():
        raise ValueError("Input is not a directory")

    if out_dir.exists() and not out_dir.is_dir():
        raise ValueError("Output is not a directory")

    out_dir.mkdir(parents=True, exist_ok=True)

    for file in in_dir.iterdir():
        process_one_file(file, out_dir / file.name, strategies, formats)


parser = argparse.ArgumentParser(
    prog="metadater", description="Photo metadata parser and applier"
)
parser.add_argument("ind", type=Path, metavar="IN", help="input directory")
parser.add_argument("outd", type=Path, metavar="OUT", help="output directory")
parser.add_argument(
    "-s",
    type=lambda s: s.split(","),
    metavar="STRATEGIES",
    default="exif,json,filename",
    help="comma-separated search strategies (exif, json, filename)",
    dest="strategies",
)
parser.add_argument(
    "-n",
    type=lambda s: s.split(","),
    metavar="FORMAT",
    default="IMG_%Y%m%d_%H%M%S",
    help="comma-separated search file name formats for 'filename' strategy",
    dest="nameformat",
)

if __name__ == "__main__":
    args = parser.parse_args()
    process_files(args.ind, args.outd, args.strategies, args.nameformat)
