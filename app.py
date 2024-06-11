import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from pygame import gfxdraw
import numpy as np
import pygame
import sys
import os
import time
import datetime
from thirdi_utils import build_by_time_of_day, get_original_dt, get_gps_coordinates_in_dms, get_image_path

pygame.init()
pygame.mouse.set_visible(False)
screen_info = pygame.display.Info()

fullscreen = True

if fullscreen:
    screen_width, screen_height = screen_info.current_w, screen_info.current_h
    print(screen_width, 'x', screen_height)
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
else:
    screen_width, screen_height = 1920//2, 1080//2
    screen = pygame.display.set_mode((screen_width, screen_height))
    
image = None
by_time_of_day = build_by_time_of_day()

def quit():
    pygame.quit()
    sys.exit()
    
main_font_size = 20
main_font_name = "assets/FiraMono-Regular.ttf"
main_font = pygame.font.Font(main_font_name, main_font_size)

clock_font_size = 40
clock_font_name = "assets/KodeMono-Regular.ttf"
clock_font = pygame.font.Font(clock_font_name, clock_font_size)


frame_rate = 30
text_color = (255, 255, 255)
text_bg_color = (0, 0, 0)
characters_per_second = 30
line_height = main_font_size * 1.3
reveal_duration = 5
quantization = 16

last_dt = None
latitude, longitude = None, None


def load_image(image_path, cover=True):
    print("loading", image_path)
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


def text_with_bg(font, text, x, y, padding):
    text = font.render(text, True, text_color)
    text_rect = text.get_rect()
    text_rect.topleft = (x, y)
    text_rect.width += 2 * padding[0]
    text_rect.height += 2 * padding[1]
    pygame.draw.rect(screen, text_bg_color, text_rect)
    screen.blit(text, (x + padding[0], y + padding[1]))


def draw_aa_circle(surface, center, radius, color):
    x, y = center
    gfxdraw.filled_circle(surface, x, y, radius, color)
    gfxdraw.aacircle(surface, x, y, radius, color)


def draw_filled_pie(
    surface, center, radius, start_angle, end_angle, color, resolution=64
):
    points = []
    x, y = center
    angles = start_angle + np.linspace(0, 2 * np.pi, resolution)
    range = end_angle - start_angle
    n_angles = int(range / (2 * np.pi) * resolution)
    angles = angles[:n_angles].tolist()
    angles.extend([end_angle])
    xs = x + radius * np.cos(angles)
    ys = y + radius * np.sin(angles)
    points = list(zip(xs, ys))
    points.append(center)
    if len(points) > 2:
        gfxdraw.filled_polygon(surface, points, color)
        gfxdraw.aapolygon(surface, points, color)


def draw_second_hand_circle(
    center,
    inner_radius=25,
    outer_radius=30,
    inner_color=(0, 0, 0),
    outer_color=(255, 255, 255),
):
    x, y = center
    draw_aa_circle(screen, center, outer_radius, outer_color)
    now = datetime.datetime.now()
    seconds = now.second + now.microsecond / 1e6
    pie_angle = 2 * np.pi * (seconds / 60)
    pie_offset = -np.pi / 2
    draw_filled_pie(
        screen, center, inner_radius, pie_offset, pie_angle + pie_offset, inner_color
    )


start_time = time.time()
frame_count = 1
try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    quit()

        cur_dt = datetime.datetime.now()
        if last_dt is None or last_dt.minute != cur_dt.minute:
            original_dt = get_original_dt(cur_dt)
            image_dt, image_path = get_image_path(by_time_of_day, original_dt)
            latitude, longitude = get_gps_coordinates_in_dms(image_path)
            image = load_image(image_path)
        # if last_dt is not None and last_dt.second != cur_dt.second:
        #     print(cur_dt)
        last_dt = cur_dt

        screen.fill((0, 0, 0))
        draw_image(image)

        columns = screen_width // quantization
        total_steps = columns * (screen_height // quantization)
        if cur_dt.second < reveal_duration:
            seconds = cur_dt.second + cur_dt.microsecond / 1e6
            steps = int(total_steps * (seconds / reveal_duration))
            rect_top = quantization * (steps // columns)
            pygame.draw.rect(
                screen, (0, 0, 0), (0, rect_top, screen_width, screen_height - rect_top)
            )
            rect_left = quantization * (steps % columns)
            pygame.draw.rect(
                screen,
                (0, 0, 0),
                (
                    rect_left,
                    rect_top - quantization,
                    screen_width - rect_left,
                    quantization,
                ),
            )

        time_str = cur_dt.strftime("%Y-%m-%d")
        text = f"{time_str}\n"
        if latitude is None:
            latitude = "N/A"
            longitude = "N/A"
        text += f"Latitude: {latitude}\nLongitude: {longitude}"

        modified_dt = cur_dt.replace(second=0, microsecond=0)
        seconds_into_minute = (cur_dt - modified_dt).total_seconds()
        text_count = int(min(len(text), seconds_into_minute * characters_per_second))
        text = text[:text_count]

        clock_str = cur_dt.strftime("%H:%M:%S")
        text_with_bg(clock_font, clock_str, 10, 10, (8, 1))

        x = 10
        y = 70
        for i, line in enumerate(text.split("\n")):
            line_y = y + i * line_height
            text_with_bg(main_font, line, x, line_y, (5, 1))

        draw_second_hand_circle(
            (50, screen_height - 50), inner_radius=25, outer_radius=30
        )

        pygame.display.flip()
        next_time = start_time + frame_count / frame_rate
        sleep_time = next_time - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
        frame_count += 1

except KeyboardInterrupt:
    pass