from joblib import Parallel, delayed
from tqdm import tqdm
import os
import datetime
import pickle
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from bisect import bisect_left


def parallel(job, tasks):
    try:
        results = Parallel(n_jobs=-1)(delayed(job)(task) for task in tqdm(tasks))
        return results
    except KeyboardInterrupt:
        pass


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


def load_image_list():
    cache_fn = "image_list.pkl"
    if os.path.exists(cache_fn):
        with open(cache_fn, "rb") as f:
            return pickle.load(f)
    else:
        image_list = build_image_list()
        with open(cache_fn, "wb") as f:
            pickle.dump(image_list, f)
        return image_list

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

def get_image_path(image_list, dt):
    idx = bisect_left(image_list, (dt, "")) - 1
    if idx < 0:
        idx = 0
    if idx >= len(image_list):
        idx = len(image_list) - 1
    return image_list[idx]
