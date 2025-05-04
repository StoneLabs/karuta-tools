import argparse
import csv
import os
import random
import time
import chime
import sys
import tty

from typing import Any
from pynput import keyboard

from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
pygame.init()  # Initialize pygame mixer
pygame.mixer.init()

from rich.traceback import install
install(show_locals=True)

from rich.text import Text
from rich.console import Console
console = Console()
print = console.print
input = console.input

import signal
def signal_handler(sig, frame):
    print('[bold red]\n\nQuitting![/bold red]')
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

### Enf of imports

args: Any = None #type: ignore

lock_pause = True
paused = False
def toggle_pause():
    global lock_pause
    global paused
    
    if lock_pause:
        return

    paused = not paused
    if (paused):
        pygame.mixer.music.pause()
    else:
        pygame.mixer.music.unpause()
    print(f'{"[bright_black] ‹Paused› [/bright_black]" if paused else "[bright_black]‹Unpaused›[/bright_black]"}', end="\b"*10)

def push_skip():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()

def push_reset():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.rewind()

listener = keyboard.GlobalHotKeys({
        '<space>': toggle_pause,
        's': push_skip,
        'r': push_reset})
listener.start()
tty.setcbreak(sys.stdin.fileno())

def wait_until_enter():
    global lock_pause
    
    lock_pause = True
    input()
    lock_pause = False

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

def load_poem_ids_by_color(csv_file, color, id=None):
    """Load poem IDs with the specified color from the CSV file."""
    poem_ids = []
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Skip the headers
            for row in reader:
                if len(row) < 2:
                    continue  # Skip invalid rows
                if row[1].strip() == color or int(row[0].strip()) == id:
                    poem_ids.append(dotdict({ \
                        "id": row[0].strip(), \
                        "upper": row[6].strip(), \
                        "lower": row[7].strip(), \
                        "first": row[13].strip()+row[14].strip()+row[15].strip(), \
                        "second": row[16].strip()+row[17].strip() \
                    }))
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found.")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return poem_ids

def remove_duplicate_poems_by_id(poems):
    """Remove duplicate poems based on the 'id' field."""
    seen_ids = set()
    unique_poems = []
    for poem in poems:
        if poem.id not in seen_ids:
            seen_ids.add(poem.id)
            unique_poems.append(poem)
    return unique_poems

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
    global lock_pause
    lock_pause = False

    random.shuffle(poems)
    retake_list = []

    for poem in poems:
        first_half = os.path.join(audio_dir, reader_id, f"{int(poem.id):03d}_1.mp3")
        second_half = os.path.join(audio_dir, reader_id, f"{int(poem.id):03d}_2.mp3")

        if args.reverse:
            # swap order of audio files
            first_half, second_half = second_half, first_half

        print(f" [bright_black]🞂 Waiting...[bright_black]", end="\r")
        time.sleep(args.pause)  # Pause before the next poem
        
        text_upper = f"[yellow]{poem.upper}[/yellow][grey30]{poem.first[len(poem.upper):8]}[/grey30]"                                                              
        text_lower = f"[yellow]{poem.lower}[/yellow][grey30]{poem.second[len(poem.lower):8]}[/grey30]"                                                              
        
        speed_study = args.study_mode and args.speed_check
        retake = None

        if args.reverse:
            text_upper, text_lower = text_lower, text_upper

        if not args.hide_number:
            print(f" 🞂 Playing #{poem.id:3} ", end="")
        else:
            print(f" 🞂 Playing #[cyan]???[/cyan] ", end="")

        if args.reverse:
            print("下ｰ>上", end="")
        else:
            print("上->下", end="")

        if not args.text:
            play_audio_file(first_half)
        if args.beep and not args.text:
            chime.info()
        if not args.text and not args.no_second_half and not speed_study:
            time.sleep(args.middle_pause)  # Pause between first and second halves
            play_audio_file(second_half)
        if args.log or args.text:
            print(f"【", end="")
            print(f"[yellow]{text_upper}[/yellow]", end="")
            print(f"／", end="")
            if speed_study:
                print(f"[bright_black]press n/m[/bright_black]", end="\b"*9)
            else:
                print(f"[bright_black]waiting...[/bright_black]", end="\b"*10)
            time_taken = None
            forgotten_ovr = False
            if speed_study:
                start_time = int(time.time()*1000.0)
                while True:
                    with keyboard.Events() as events:
                        event = events.get(1e6)
                        if event.key == keyboard.KeyCode.from_char('m') and isinstance(event, keyboard.Events.Press):
                            break
                        if event.key == keyboard.KeyCode.from_char('n') and isinstance(event, keyboard.Events.Press):
                            forgotten_ovr = True
                            break
                end_time = int(time.time()*1000.0)
                time_taken = end_time - start_time
                if forgotten_ovr == True or time_taken > args.speed_check_threshhold:
                    retake = True
                else:
                    retake = False
            if args.text and not speed_study:
                time.sleep(args.middle_pause)
                if args.beep:
                    chime.info()
            print(f"[yellow]{text_lower}[/yellow]", end="")
            print(f"】", end="")
            if time_taken is not None:
                if forgotten_ovr == True:
                    print(f"forgotten...")
                    time.sleep(1)
                else:
                    print(f"{time_taken}ms")
            else:
                print("")
        else:
            print(" "*14)
        if args.study_mode:
            lock_pause = True
            while retake is None:
                print(" [bright_black]🞂 Press 'm' if memorized, 'n' if not. [/bright_black]", end="\r")
                with keyboard.Events() as events:
                    # Block for as much as possible
                    event = events.get(1e6)
                    if event.key == keyboard.KeyCode.from_char('m') and isinstance(event, keyboard.Events.Press): #type: ignore
                        retake = False
                    if event.key == keyboard.KeyCode.from_char('n') and isinstance(event, keyboard.Events.Press): #type: ignore
                        retake = True
            
            if retake:
                print("", end="\033[F\r")
                print("[red] 🞂[/red]")
                retake_list = retake_list + [poem]
            else:
                print("", end="\033[F\r")
                print("[green] 🞂[/green]")
            print(" "*50, end="\r")
            lock_pause = False

        if args.confirm and not args.study_mode:
            print(" [bright_black]🞂 Press enter to continue[/bright_black]", end="\r")
            wait_until_enter()
            print(" "*30, end="\r")
                    
    lock_pause = True
    return retake_list

def main():
    global args
    
    parser = argparse.ArgumentParser(description="Karuta Random Player")
    parser.add_argument("-f", "--filter", default='all', help="ID or Color of the poems to practice (e.g., 1, 100, 'pink', 'blue', ... or 'all'). Default is all. Plus can be used to combine multiple.")
    parser.add_argument("-r", "--reader", default="B", help="Reader ID (default: 'B')")
    parser.add_argument("--no-second-half", default=False, action='store_true', help="Don't play second half")
    parser.add_argument("--middle-pause", default=1, type=int, help="Pause between first and second half")
    parser.add_argument("-p", "--pause", default=5, type=int, help="Pause between poems in seconds.")
    parser.add_argument("-l", "--log", default=False, action='store_true', help="Print poem kimariji after playback")
    parser.add_argument("-b", "--beep", default=False, action='store_true', help="Plays beep sound after first half")
    parser.add_argument("-s", "--study-mode", default=False, action='store_true', help="After each poem, review is required. After all have been played, the program will restart with the ones that received a bad review.")
    parser.add_argument("--speed-check", default=False, action='store_true', help="Automatically answers memorized/not memorized based on reaction speed. (In study mode)")
    parser.add_argument("--speed-check-threshhold", default=2000, type=int, help="Threashold for speed check mode. Default is 2000 (in ms)")
    parser.add_argument("-c", "--confirm", default=False, action='store_true', help="Pause after each poem until confirmation from user (no effect with --study-mode)")
    parser.add_argument("-t", "--text", default=False, action='store_true', help="No audio playback. Only upper kimariji is printed.")
    parser.add_argument("--reverse", default=False, action='store_true', help="Poems are asked 下→上 instead of the the normal way")
    parser.add_argument("--hide-number", default=False, action="store_true", help="Hides ID of Poem")
    parser.add_argument("--allow-duplicates", default=False, action="store_true", help="Disables the automatic removal of duplicate cards in the input filter")

    args = parser.parse_args()
    csv_file = "hyakuninissyu-csv/data.csv"

    poems = []

    if args.filter.lower().strip() == "all":
        args.filter = '+'.join(COLOR_MAPPING.keys())

    for filter in args.filter.split("+"):
        if filter.isdigit():
            id = int(filter)
            poems = poems + load_poem_ids_by_color(csv_file, None, id=id)
            continue
        
        rangeFilter = filter.split("-")
        if len(rangeFilter) == 2:
            if rangeFilter[0].isdigit() and rangeFilter[1].isdigit():
                rangeLower = int(rangeFilter[0])
                rangeUpper = int(rangeFilter[1])
                if rangeUpper < rangeLower:
                    print(f"Error: Invalid range order '{filter}'")
                    return
                for id in range(rangeLower, rangeUpper + 1):
                    poems = poems + load_poem_ids_by_color(csv_file, None, id=id)
                continue
            else:
                print(f"Error Invalid non-digit range parts '{filter}'")
                return
            

        # Convert English color name to Japanese kanji
        color_jp = COLOR_MAPPING.get(filter.lower().strip())
        if not color_jp:
            print(f"Error: Invalid color '{filter}'. Valid options are: {', '.join(COLOR_MAPPING.keys())}")
            return

        poems = poems + load_poem_ids_by_color(csv_file, color_jp)

    prefilter_poems = poems
    if args.allow_duplicates:
        poems = poems
    else:
        poems = remove_duplicate_poems_by_id(poems)

    # Load poem IDs
    if not poems:
        print(f"No poems found for filter '{args.filter}'.")
        return

    if len(prefilter_poems) != len(poems):
        print(f"[bold]\nLoaded {len(poems)} poems with filter '{args.filter}'. (overlaps removed)[/bold]")
    else:
        print(f"[bold]\nLoaded {len(poems)} poems with filter '{args.filter}'.[/bold]")
    if args.text:
        print(f"[bold]Starting practice text mode.[/bold]")
    else:
        print(f"[bold]Starting practice with reader '{args.reader}'.[/bold]")
    print(f"[bright_black]Space = Pause | S = Skip | R = Reset[/bright_black]")
    
    print("")
    while poems != []:
        input(f"Setup cards and confirm with enter to start.")
        print()

        poems = play_audio_files(poems, args.reader)
        if len(poems) > 0:
            print(f"\nRestarting with {len(poems)} bad ones.")

    pygame.quit()  # Quit pygame mixer

if __name__ == "__main__":
    main()

