import argparse
import csv
import os
import random
import time
import pygame
import chime

from typing import Any
from pynput import keyboard

args: Any = None #type: ignore

paused = False
def toggle_pause():
    global paused
    paused = not paused
    if (paused):
        pygame.mixer.music.pause()
    else:
        pygame.mixer.music.unpause()
    print(f'{"\r -- Paused! --\r" if paused else "\r --Unpaused!--\r"}', end="")

listener = keyboard.GlobalHotKeys({
        '<space>': toggle_pause})
listener.start()

# Map English color names to Japanese kanji
COLOR_MAPPING = {
    "pink": "桃",
    "yellow": "黄",
    "blue": "青",
    "green": "緑",
    "orange": "橙"
}

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def load_poem_ids_by_color(csv_file, color):
    """Load poem IDs with the specified color from the CSV file."""
    poem_ids = []
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Skip the headers
            for row in reader:
                if len(row) < 2:
                    continue  # Skip invalid rows
                if row[1].strip() == color:
                    poem_ids.append(dotdict({"id": row[0].strip(), "upper": row[6].strip(), "lower": row[7].strip()}))
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found.")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return poem_ids

def play_audio_file(file_path):
    """Play a single audio file using pygame.mixer with pause functionality."""
    if os.path.exists(file_path):
        try:
            while (paused):
                time.sleep(0.016)
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy() or paused:
                time.sleep(0.016)  # Prevent busy-waiting
                #print(pygame.mixer.music.get_pos())
            #print("Audio loop ended")
        except Exception as e:
            print(f"Error playing audio file '{file_path}': {e}")
    else:
        print(f"File not found: {file_path}")

def play_audio_files(poems, reader_id, audio_dir="./audio_files"):
    """Play the audio files for the given poem IDs in random order."""
    random.shuffle(poems)
    retake_list = []

    for poem in poems:
        first_half = os.path.join(audio_dir, reader_id, f"{int(poem.id):03d}_1.mp3")
        second_half = os.path.join(audio_dir, reader_id, f"{int(poem.id):03d}_2.mp3")

        print(f"\r -> Playing #{poem.id}")
        play_audio_file(first_half)
        if not args.no_second_half:
            time.sleep(args.middle_pause)  # Pause between first and second halves
            play_audio_file(second_half)
        if args.log:
            print(f"\r --> {poem.upper} / {poem.lower} ")
        if args.beep:
            chime.info()
        if args.study_mode:
            retake = None
            while retake is None:
                print("\r --> Press 'm' if memorized, any other if not: ", end="", flush=True)
                with keyboard.Events() as events:
                    # Block for as much as possible
                    event = events.get(1e6)
                    if event.key == keyboard.KeyCode.from_char('m'): #type: ignore
                        retake = False
                    else:
                        retake = True
            
            if retake:
                print("\n\r --> Reusing")
                retake_list = retake_list + [poem]
            else:
                print("\n\r --> Not reusing")

        if args.confirm and not args.study_mode:
            input("\r --> Press enter to continue. ")
            
        time.sleep(args.pause)  # Pause before the next poem
        
    return retake_list

def main():
    global args
    
    pygame.init()  # Initialize pygame mixer
    pygame.mixer.init()

    parser = argparse.ArgumentParser(description="Karuta Random Player")
    parser.add_argument("-c", "--color", default='all', help="Color of the poems to practice (e.g., 'pink', 'blue', ... or 'all'). Default is all. Plus can be used to combine multiple.")
    parser.add_argument("-r", "--reader", default="B", help="Reader ID (default: 'B')")
    parser.add_argument("--no-second-half", default=False, action='store_true', help="Don't play second half")
    parser.add_argument("--middle-pause", default=1, type=int, help="Pause between first and second half")
    parser.add_argument("-p", "--pause", default=5, type=int, help="Pause between poems in seconds.")
    parser.add_argument("-l", "--log", default=False, action='store_true', help="Print poem kimariji after playback")
    parser.add_argument("-b", "--beep", default=False, action='store_true', help="Plays beep sound after first half")
    parser.add_argument("-s", "--study-mode", default=False, action='store_true', help="After each poem, review is required. After all have been played, the program will restart with the ones that received a bad review.")
    parser.add_argument("--confirm", default=False, action='store_true', help="Pause after each poem until confirmation from user (no effect with --study-mode)")

    args = parser.parse_args()
    csv_file = "hyakuninissyu-csv/data.csv"

    poems = []

    if args.color.lower().strip() == "all":
        args.color = '+'.join(COLOR_MAPPING.keys())

    for color in args.color.split("+"):
        # Convert English color name to Japanese kanji
        color_jp = COLOR_MAPPING.get(color.lower().strip())
        if not color_jp:
            print(f"Error: Invalid color '{color}'. Valid options are: {', '.join(COLOR_MAPPING.keys())}")
            return

        poems = poems + load_poem_ids_by_color(csv_file, color_jp)


    # Load poem IDs
    if not poems:
        print(f"No poems found for color '{args.color}'.")
        return

    print(f"\nLoaded {len(poems)} poems with color(s) '{args.color}'")
    print(f"Starting practice with reader '{args.reader}'.")
    
    print("")
    while poems != []:
        input(f"Setup cards and confirm with enter to start.")
        poems = play_audio_files(poems, args.reader)
        if len(poems) > 0:
            print(f"\nRestarting with {len(poems)} bad ones.")

    pygame.quit()  # Quit pygame mixer

if __name__ == "__main__":
    main()

