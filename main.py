import pyautogui
import mss
import numpy as np
import time
import ctypes
import math
import threading
from PIL import Image
import tkinter as tk
 
# Disable PyAutoGUI fail-safe
pyautogui.FAILSAFE = False
 
# Constants for mouse movement simulation
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
VK_XBUTTON4 = 0x05  # Virtual key code for XBUTTON4 (usually the fourth mouse button)
 
def get_color_at_position(x, y):
    with mss.mss() as sct:
        bbox = {'left': x - 5, 'top': y - 5, 'width': 10, 'height': 10}
        screenshot = sct.grab(bbox)
        img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        return img.getpixel((5, 5))  # Sample the center of the bounding box
 
def is_color_in_range(color, target_colors, tolerance=10):
    return any(all(abs(color[i] - target_color[i]) <= tolerance for i in range(3)) for target_color in target_colors)
 
def find_color_in_screenshot(screenshot, target_colors, tolerance=10, search_radius=1):
    img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
    width, height = img.size
    pixels = img.load()
    
    positions = []
    center_x = width // 2
    center_y = height // 2
 
    for x in range(search_radius, width - search_radius):
        for y in range(search_radius, height - search_radius):
            if not is_color_in_range(pixels[x, y], target_colors, tolerance):
                continue
            
            distance_from_center = math.hypot(x - center_x, y - center_y)
            positions.append((x, y, distance_from_center))
 
    return positions
 
def calculate_weighted_average_position(positions, bbox):
    if not positions:
        return None
 
    total_weight = sum(1 / (distance + 1) for _, _, distance in positions)
    weighted_x = sum(x / (distance + 1) for x, _, distance in positions)
    weighted_y = sum(y / (distance + 1) for _, y, distance in positions)
 
    return (
        int(weighted_x / total_weight + bbox['left']),
        int(weighted_y / total_weight + bbox['top'])
    )
 
def move_mouse(dx, dy):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, dx, dy, 0, 0)
 
def move_cursor_to_position(target_x, target_y, current_x, current_y, simulation=True):
    if not simulation:
        pyautogui.moveTo(target_x, target_y, duration=0.1)
        return
 
    dx, dy = target_x - current_x, target_y - current_y
    distance = math.sqrt(dx**2 + dy**2)
 
    if distance == 0:
        return
 
    num_steps = int(distance / 5) + 1
    step_dx, step_dy = dx / num_steps, dy / num_steps
 
    for _ in range(num_steps):
        move_mouse(int(step_dx), int(step_dy))
        time.sleep(0.01)
 
def lock_cursor_position():
    screen_rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(ctypes.windll.user32.GetDesktopWindow(), ctypes.byref(screen_rect))
    ctypes.windll.user32.ClipCursor(ctypes.byref(screen_rect))
 
def unlock_cursor_position():
    ctypes.windll.user32.ClipCursor(None)
 
def get_key_state(key_code):
    return ctypes.windll.user32.GetAsyncKeyState(key_code)
 
def draw_circle_around_mouse(root, canvas, circle_radius=20):
    while True:
        x, y = pyautogui.position()
        canvas.coords("mouse_circle", x - circle_radius, y - circle_radius, x + circle_radius, y + circle_radius)
        root.update()
        time.sleep(0.01)
 
def start_circle_thread():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.overrideredirect(True)
    root.geometry("+0+0")
    root.configure(bg="black")
    root.wm_attributes("-transparentcolor", "black")
    
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    canvas = tk.Canvas(root, width=screen_width, height=screen_height, bg="black", highlightthickness=0)
    canvas.pack()
    
    circle_radius = 20
    canvas.create_oval(0, 0, circle_radius * 2, circle_radius * 2, outline="green", width=2, tags="mouse_circle")
    
    threading.Thread(target=draw_circle_around_mouse, args=(root, canvas, circle_radius), daemon=True).start()
    root.mainloop()
 
def main():
    # Start the green circle thread
    threading.Thread(target=start_circle_thread, daemon=True).start()
 
    # Accept as many target colors as the user wants to input
    target_colors = []
    print("Enter the RGB values of the colors you want to track.")
    print("You can enter as many colors as you want. Press Enter without typing anything to finish.")
    
    while True:
        color_input = input(f"Enter the RGB values of color {len(target_colors) + 1} (e.g., 255,0,0) or press Enter to finish: ")
        if not color_input:
            if len(target_colors) == 0:
                print("At least one color is required. Please enter a color.")
                continue
            break
        try:
            target_color = tuple(map(int, color_input.split(',')))
            if len(target_color) == 3 and all(0 <= c <= 255 for c in target_color):
                target_colors.append(target_color)
            else:
                print("Invalid color format. Please enter values in the format R,G,B where each value is between 0 and 255.")
        except ValueError:
            print("Invalid input. Please enter the RGB values in the format R,G,B.")
 
    if not target_colors:
        print("No target colors provided. Exiting.")
        return
 
    tracking = False
    is_paused = False  # Flag to track if mouse movement is paused
    frame_rate = 900
    interval = 1.0 / frame_rate
 
    search_radius = 1
    max_search_radius = 10
    search_step = 1
    tolerance = 30
 
    while True:
        if not (get_key_state(VK_XBUTTON4) & 0x8000):
            if tracking:
                print("Tracking deactivated.")
                tracking = False
                unlock_cursor_position()
                search_radius = 1  # Reset search radius when tracking is deactivated
            is_paused = False  # Ensure mouse movement is unpaused when button is released
            time.sleep(interval)
            continue
 
        if get_key_state(VK_XBUTTON4) & 0x8000:
            if not is_paused:
                if tracking:
                    print("Tracking paused.")
                    is_paused = True
            else:
                if not tracking:
                    print("Tracking activated.")
                    tracking = True
                    lock_cursor_position()
 
        if is_paused:
            time.sleep(interval)
            continue
 
        start_time = time.time()
 
        mouse_x, mouse_y = pyautogui.position()
        bbox = {'left': mouse_x - 11, 'top': mouse_y - 11, 'width': 22, 'height': 22}
        with mss.mss() as sct:
            screenshot = sct.grab(bbox)
            positions = find_color_in_screenshot(screenshot, target_colors, tolerance=tolerance, search_radius=search_radius)
 
        if positions:
            avg_position = calculate_weighted_average_position(positions, bbox)
            if avg_position:
                # Move cursor to the position of the target color
                move_cursor_to_position(*avg_position, *pyautogui.position())
                print(f"Target color found and tracking at average position: {avg_position}")
                
                # Click immediately when color is detected
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # Left button down
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # Left button up
                
                search_radius = 1  # Reset search radius after successful tracking
            else:
                print("Target color lost within the tracking area.")
                search_radius = min(search_radius + search_step, max_search_radius)  # Increase search radius carefully
        else:
            print("Target color not found. No movement.")
            search_radius = min(search_radius + search_step, max_search_radius)  # Gradually increase search radius
 
        # Prevent the radius from exceeding maximum bounds
        if search_radius > max_search_radius:
            search_radius = max_search_radius
        
        elapsed_time = time.time() - start_time
        time.sleep(max(0, interval - elapsed_time))
 
if __name__ == "__main__":
    main()
