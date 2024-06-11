from joblib import Parallel, delayed
from tqdm import tqdm
import os
import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from bisect import bisect_left
import turbojpeg
import warnings
import numpy as np
from collections import defaultdict
import hashlib
import pickle
import inspect
import os


def memoize(func):
    is_method = "self" in inspect.getfullargspec(func).args

    def wrapper(*args, **kwargs):
        fn = os.path.join("cache", func.__name__)
        args_to_hash = ""
        if len(args) > 0:
            args_to_hash += str(args[1:] if is_method else args)
        if len(kwargs) > 0:
            args_to_hash += str(kwargs)
        if len(args_to_hash) > 0:
            fn += "_" + hashlib.md5(str(args_to_hash).encode()).hexdigest()
        fn += ".pkl"
        try:
            os.makedirs("cache", exist_ok=True)
            with open(fn, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            result = func(*args, **kwargs)
            with open(fn, "wb") as f:
                pickle.dump(result, f)
            return result

    return wrapper


def parallel(job, tasks):
    try:
        results = Parallel(n_jobs=-1)(delayed(job)(task) for task in tqdm(tasks))
        return results
    except KeyboardInterrupt:
        pass


@memoize
def build_image_list():
    images = []
    for root, dirs, files in os.walk("images"):
        for file in files:
            image_path = os.path.join(root, file)
            if file.startswith("."):
                continue
            if not image_path.endswith("jpg"):
                continue
            date_str = image_path.split("/")[1]
            time_str = image_path.split("/")[2].split(".")[0]
            date_time_str = date_str + " " + time_str
            date_time_obj = datetime.datetime.strptime(
                date_time_str, "%m-%d-%Y %H-%M-%S"
            )
            images.append((date_time_obj, image_path))
    images.sort()
    return images


def get_dms_from_gps(dms, ref):
    """Formats DMS (degrees, minutes, seconds) GPS data for printing"""
    degrees = dms[0]
    minutes = dms[1]
    seconds = dms[2]
    direction = ref
    return f"{degrees} deg {minutes}' {seconds}\" {direction}"


def get_gps_coordinates_in_dms(img_path):
    """Extracts GPS coordinates in DMS format from an image file."""
    img = Image.open(img_path)
    if hasattr(img, "_getexif"):
        exif_data = img._getexif()
        if exif_data is not None:
            # Extract GPS data
            gps_data = {}
            for tag, value in exif_data.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]

            # Retrieve latitude and longitude in DMS format
            lat = lon = None
            if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
                lat_ref = gps_data["GPSLatitudeRef"]
                lat = get_dms_from_gps(gps_data["GPSLatitude"], lat_ref)
            if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
                lon_ref = gps_data["GPSLongitudeRef"]
                lon = get_dms_from_gps(gps_data["GPSLongitude"], lon_ref)

            return lat, lon

    return None, None


def get_original_dt(dt):
    mod_dt = dt

    # make leap days a repeat of the previous day
    if mod_dt.month == 2 and mod_dt.day == 29:
        mod_dt = mod_dt.replace(day=28)

    # replace year with 2011
    mod_dt = mod_dt.replace(year=2011)

    # unless it's the end of the year, then we use 2010
    if mod_dt.month == 12 and mod_dt.day >= 18:
        mod_dt = mod_dt.replace(year=2010)

    return mod_dt


def get_image_path(by_time_of_day, dt):
    time_of_day = f"{dt.hour:02d}:{dt.minute:02d}"
    options = by_time_of_day[time_of_day]
    month_and_day = int(f"{dt.month:02d}{dt.day:02d}")
    idx = bisect_left(options, (month_and_day, dt, ""))
    idx = min(idx, len(options) - 1)
    _, timestamp, fn = options[idx]
    return timestamp, fn


def get_brightness(fn):
    tj = turbojpeg.TurboJPEG()
    warnings.filterwarnings("error")
    try:
        with open(fn, "rb") as f:
            img = tj.decode(f.read())
        mean = np.median(img)
        return mean
    except:
        return None


@memoize
def build_brightness_list():
    image_list = build_image_list()
    filenames = [e[1] for e in image_list]
    brightness_list = parallel(get_brightness, filenames)
    return brightness_list


@memoize
def build_by_time_of_day():
    threshold = 5
    image_list = build_image_list()
    brightness_list = build_brightness_list()
    by_time_of_day = defaultdict(list)
    for pair, brightness in zip(image_list, brightness_list):
        if brightness is None:
            # almost 60 images are "broken"
            continue
        if brightness < threshold:
            continue
        timestamp, fn = pair
        time_of_day = f"{timestamp.hour:02d}:{timestamp.minute:02d}"
        month_and_day = int(f"{timestamp.month:02d}{timestamp.day:02d}")
        by_time_of_day[time_of_day].append((month_and_day, timestamp, fn))

    for k, v in by_time_of_day.items():
        by_time_of_day[k] = sorted(v)

    return by_time_of_day
