import flet as ft
import asyncio
from shazamio import Shazam
import json
import requests
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOauthError
import os
from pathlib import Path
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.mp3 import EasyMP3
import tempfile
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("flet_core").setLevel(logging.INFO)

temp = tempfile.gettempdir()
# Defining the Track class
class Track():
    def __init__(self, artist="Unknown", title="Unknown", album="Unknown", path="Unknown", desc="Unknown"):
        self.artist = artist
        self.album = album
        self.title = title
        self.path = path
        self.desc = desc

async def main(page: ft.Page):
    page.title = "Cover Art Retriever"  # タイトル
    page.window.width = 800  # ウィンドウの幅
    page.window.height = 900 # ウィンドウの高さ

    def collect_files(folder_path, tracks_list):
        if folder_path.is_file():
            if folder_path.suffix in (".mp3", ".flac"):
                print(folder_path)
                tracks_list.append(Track(path=folder_path))
            else:
                return
        else:
            for target_path in Path(folder_path).iterdir():
                if target_path.is_file():
                    if target_path.suffix in (".mp3", ".flac"):
                        print(target_path)
                        tracks_list.append(Track(path=target_path))
                    else:
                        continue
                else:
                    collect_files(target_path, tracks_list)
            return tracks_list
            
    async def metadata():
        try:
            global tracks_list
            print("Starting...")
            print(tracks_list)
            # Let it Shazam 🔥🔥🔥🔥
            for track in tracks_list:
                target_file.content = ft.Text(f"Processing {track.path.name}...", size=15, color="white")
                page.update()
                track_path = track.path
                shazam = Shazam()
                out = await shazam.recognize(str(track_path))
                try:
                    url = out['track']['share']['href'].replace("https://www.shazam.com/", "https://www.shazam.com/ja-jp/")
                    print(url)
                    req = requests.get(url)
                    soup = BeautifulSoup(req.text, "html.parser")
                    track_name = soup.select_one("h1.Text-module_text-black-200__8cY0O").text
                    tracks_list[tracks_list.index(track)].title = track_name
                    artist = soup.select_one(".TrackPageHeader_link__q0Id5").text
                    tracks_list[tracks_list.index(track)].artist = artist
                    Path(f"{temp}/CoverGen/data/{track_name}").mkdir(parents=True, exist_ok=True)
                    with open(f"{temp}/CoverGen/data/{track_name}/Shazam.json", "w", encoding="utf-8") as f:
                        json.dump(out, f, indent=4)
                    if out['track']['share']['image'] != "":
                        req = requests.get(out['track']['share']['image'])
                        with open(f"{temp}/CoverGen/data/{track_name}/thumbnail.jpg", "wb") as f:
                            f.write(req.content)
                    else:
                        print("No coverart found!")
                except Exception as e:
                    print(f"No results found! Skipping this track... \n Error: {e}")
                    continue

                # Contacting Spotify for additional information
                global sp
                results = sp.search(q=f"{track_name} {artist}", limit=1)
                if results:
                    with open(f"{temp}/CoverGen/data/{track_name}/search_result.json", "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=4)
                    track_info = sp.track(results['tracks']['items'][0]['id'])
                    with open(f"{temp}/CoverGen/data/{track_name}/track_info.json", "w", encoding="utf-8") as f:
                        json.dump(track_info, f, indent=4)
                    tracks_list[tracks_list.index(track)].album = track_info['album']['name']
                    req = requests.get(track_info["album"]["images"][0]["url"])
                    with open(f"{temp}/CoverGen/data/{track_name}/thumbnail.jpg", "wb") as f:
                        f.write(req.content)
                    cover.content = ft.Image(f"{temp}/CoverGen/data/{track_name}/thumbnail.jpg", width=400, height=400)
                    info.content = ft.Text(f"{track_name} in {track_info['album']['name']} by {artist}", size=20, color="white")
                    page.update()
                    print(f"Found {track_name} in {track_info['album']['name']} by {artist}!")
                else:
                    print("No results found on Spotify!")
                    print(f"Found {track_name} by {artist}!")
                
                # Adding Metadata to the file
                if track_path.suffix == ".mp3":
                    tag = EasyMP3(track.path)
                    tag["title"] = track.title
                    tag["artist"] = track.artist
                    tag["album"] = track.album
                    tag.save()
                    audio = MP3(track.path, ID3=ID3)
                    togs = ID3(track.path)
                    togs.delall("APIC")
                    togs.save()
                    if audio.tags is None:
                        audio.add_tags()
                    with open(f"{temp}/CoverGen/data/{track_name}/thumbnail.jpg" if os.path.exists(f"{temp}/CoverGen/data/{track_name}/thumbnail.jpg") else "CoverGen/src/assets/Cover.jpg", "rb") as f:
                        audio.tags.add(APIC(encoding=0,mime="image/jpeg",type=3, desc=u"Cover", data=f.read()))
                        
                elif track_path.suffix == ".flac":
                    audio = FLAC(track.path)
                    audio["title"] = track.title
                    audio["artist"] = track.artist
                    audio["album"] = track.album

                    with open(f"{temp}/CoverGen/data/{track_name}/thumbnail.jpg" if os.path.exists(f"{temp}/CoverGen/data/{track_name}/thumbnail.jpg") else "CoverGen/src/assets/Cover.jpg", "rb") as f:
                        picture = Picture()
                        picture.data = f.read()
                        picture.type = 3  # 3 is for the cover image
                        picture.mime = "image/jpeg"  # image/jpeg or image/png
                        audio.add_picture(picture)

                audio.save()
        except Exception as e:
            error.content = ft.Text(f"An error occured: {e}", size=15, color="ERROR")
            error.visible = True
            page.update()
    
    text = ft.Text("Please select a file or a folder to start the process.", size=15, color="white")
    # I copied this part from a website
    def pick_files_result(e: ft.FilePickerResultEvent):
        selected_files.value = (", ".join(map(lambda f: f.name, e.files)) if e.files else "Canceled.")
        selected_directry.value = ""
        page.update()
        if e:
            global tracks_list
            tracks_list = []
            for file in e.files:
                if Path(file.path).suffix in (".mp3", ".flac"):
                    print(str(Path(file.path)))
                    tracks_list.append(Track(path=Path(file.path)))
                else:
                    continue
            return tracks_list

    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    selected_files = ft.Text()

    def get_directry_result(e: ft.FilePickerResultEvent):
        selected_directry.value = e.path if e.path else "Canceled."
        selected_files.value = ""
        print(e.path)
        page.update()
        if e:
            print("Collecting files...")
            global tracks_list
            tracks_list = []
            for target_path in Path(e.path).iterdir():
                if target_path.is_file():
                    if target_path.suffix in (".mp3", ".flac"):
                        print(target_path)
                        tracks_list.append(Track(path=target_path))
                    else:
                        continue
                else:
                    collect_files(target_path, tracks_list)
            return tracks_list
        
    def spotify_creds(e):
        # credentials for Spotify
        if spotify_id.value and spotify_secret.value:
            try:
                client_credentials_manager = SpotifyClientCredentials(client_id=spotify_id.value, client_secret=spotify_secret.value)
                global sp
                sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                ping = sp.search(q="Never Gonna Give You Up", limit=1)
                print(ping)
                response.content = ft.Text("☑ Spotify credentials are valid!", size=15, color="GREEN_ACCENT_200")
                spotify_id.disabled = True
                spotify_id.icon = ft.Icon(name=ft.Icons.CHECK_BOX_ROUNDED, color=ft.Colors.GREEN_ACCENT_200)
                spotify_secret.disabled = True
                spotify_secret.icon = ft.Icon(name=ft.Icons.CHECK_BOX_ROUNDED, color=ft.Colors.GREEN_ACCENT_200)
                page.update()
                Path(f"{temp}/CoverGen").mkdir(parents=True, exist_ok=True)
                with open(f"{temp}/CoverGen/creds.json", "w", encoding="utf-8") as f:
                    json.dump({"client_id": spotify_id.value, "client_secret": spotify_secret.value}, f, indent=4)
                return True
            except SpotifyOauthError as e:
                print(e)
                response.content = ft.Text("Spotify credentials are invalid!", size=15, color="ERROR")
                page.update()
                return
        else:
            response.content = ft.Text("Please enter both your Spotify Client ID and Client Secret to start the process.", size=15, color="ORANGE_100")
        page.update()
    
    get_directry_dialog = ft.FilePicker(on_result=get_directry_result)
    selected_directry = ft.Text()

    page.overlay.extend([pick_files_dialog,get_directry_dialog])
    cover = ft.Container(content=ft.Image("CoverGen/src/assets/Cover.jpg", width=400, height=400), 
                             padding=5, alignment=ft.alignment.center)
    info = ft.Container(content=ft.Text("No information available yet.", size=20, color="white"), padding=5)
    spotify_id = ft.TextField(label="Spotify Client ID", password=True, can_reveal_password=True, on_change=spotify_creds, icon="PERSON_ROUNDED")
    spotify_secret = ft.TextField(label="Spotify Client Secret", password=True, can_reveal_password=True, on_change=spotify_creds, icon="KEY_ROUNDED")
    response = ft.Container(ft.Text("Please enter your Spotify Client ID and Client Secret to start the process.", size=15, color="white"))
    if os.path.exists(f"{temp}/CoverGen/creds.json"):
        with open(f"{temp}/CoverGen/creds.json", "r", encoding="utf-8") as f:
            creds = json.load(f)
        print("Spotify credentials loaded!")
        spotify_id.value = creds["client_id"]
        spotify_secret.value = creds["client_secret"]
        spotify_creds(None)
    target_file = ft.Container(content=ft.Text("", size=15, color="white"), padding=5)
    error = ft.Container(content=ft.Text("", size=15, color="ERROR"), padding=5, visible=False)
    page.add(
        ft.Row([text]),
        ft.Column([spotify_id, spotify_secret]),
        ft.Row([response]),
        ft.Row([ft.ElevatedButton("Pick Files",icon="AUDIO_FILE",
                                  on_click=lambda _: pick_files_dialog.pick_files(allow_multiple=True)),
                selected_files]),
        ft.Row([ft.ElevatedButton("Pick Directry",
                                  icon="FOLDER",
                                  on_click=lambda _: get_directry_dialog.get_directory_path(),
                                  disabled=page.web),
                selected_directry]),
        ft.Row([ft.ElevatedButton("Start",
                                  icon="PLAY_ARROW_ROUNDED",
                                  on_click=lambda _: asyncio.run(metadata())),
                target_file]),
        ft.Row([info]),
        ft.Row([cover]),
        ft.Row([error]))

ft.app(target=main, assets_dir="assets")