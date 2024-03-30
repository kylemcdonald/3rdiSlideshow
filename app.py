import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import sys
import os
import time
import datetime
import pickle
from bisect import bisect_left
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

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
    if hasattr(img, '_getexif'):
        exif_data = img._getexif()
        if exif_data is not None:
            # Extract GPS data
            gps_data = {}
            for tag, value in exif_data.items():
                decoded = TAGS.get(tag, tag)
                if decoded == 'GPSInfo':
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]

            # Retrieve latitude and longitude in DMS format
            lat = lon = None
            if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                lat_ref = gps_data['GPSLatitudeRef']
                lat = get_dms_from_gps(gps_data['GPSLatitude'], lat_ref)
            if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                lon_ref = gps_data['GPSLongitudeRef']
                lon = get_dms_from_gps(gps_data['GPSLongitude'], lon_ref)

            return lat, lon

    return None, None


def build_image_list():
    images = []
    for root, dirs, files in os.walk("images"):
        for file in files:
            image_path = os.path.join(root, file)
            if not image_path.endswith('jpg'):
                continue
            date_str = image_path.split("/")[1]
            time_str = image_path.split("/")[2].split(".")[0]
            date_time_str = date_str + " " + time_str
            date_time_obj = datetime.datetime.strptime(date_time_str, '%m-%d-%Y %H-%M-%S')
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

pygame.init()
pygame.mouse.set_visible(False)

screen_info = pygame.display.Info()

screen_width, screen_height = screen_info.current_w, screen_info.current_h
screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)

def get_image_path(image_list, dt):
    idx = bisect_left(image_list, (dt, "")) - 1
    if idx < 0:
        idx = 0
    if idx >= len(image_list):
        idx = len(image_list) - 1
    return image_list[idx]

def load_image(image_path, cover=False):
    image = pygame.image.load(image_path)
    image_width, image_height = image.get_size()
    aspect_ratio = image_width / image_height
    if cover:
        new_width = screen_width
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = screen_height
        new_width = int(new_height * aspect_ratio)
    image = pygame.transform.smoothscale(image, (new_width, new_height))
    return image
    
def draw_image(image):
    image_width, image_height = image.get_size()
    x = (screen_width - image_width) // 2
    y = (screen_height - image_height) // 2
    screen.blit(image, (x, y))

def quit():
    pygame.quit()
    sys.exit()

last_image_path = None
image = None
image_list = load_image_list()
font_size = 20
line_height = font_size * 1.2
font = pygame.font.Font("Roboto-Regular.ttf", font_size)
try:
    while True:
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    quit()
        
        cur_dt = datetime.datetime.now()
        original_dt = get_original_dt(cur_dt)
        image_dt, image_path = get_image_path(image_list, original_dt)
        # print(cur_dt, original_dt, image_dt, image_path)
        if image_path != last_image_path:
            image = load_image(image_path)
            last_image_path = image_path
        
        # clear screen
        screen.fill((0, 0, 0))
        
        # draw image
        draw_image(image)
        
        # draw cur_dt as text at top left, as YYYY-MM-DD HH:MM:SS
        time_str = cur_dt.strftime("%Y-%m-%d %H:%M:%S")
        # print(image_path)
        latitude, longitude = get_gps_coordinates_in_dms(image_path)
        text = f"{time_str}\n"
        if latitude is not None:
            text += f"Latitude: {latitude}\nLongitude: {longitude}"
        x = 10
        y = 10
        for i, line in enumerate(text.split("\n")):
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (x, y + i * line_height))
        
        pygame.display.flip()
        time.sleep(1)
                
except KeyboardInterrupt:
    pass