import m3u8
import requests
import os
import urllib.request
import ffmpeg
from requests import Response
from playwright.sync_api import sync_playwright
import time
from seleniumbase import sb_cdp

#Please be nice, I'm a huge amateur
#Replace with your Domestika Session cookie (Shift + Ctrl + C > Application > Cookies > www.domestika.org > _domestika_session)
domestika_session = ''
cookie = {'name': '_domestika_session', 'value': domestika_session, 'domain': 'www.domestika.org', 'path': '/'}

#BE SURE TO CHECK THE LANGUAGE ABBREVIATION UNDER NETWORK IN 'INSPECT ELEMENT'!!!
#BE SURE TO ALSO CLICK THE VIDEO WITH YOUR PREFERRED SUBTITLES ON AND SEARCH FOR 'playlist.m3u8?(random numbers)' AND BE SURE IT HAS A LANGUAGE ON IT!!!
#EX: 'subtitles/de/playlist.m3u8?1661182028' IS GERMAN!!!
#CAN YOU TELL HOW IMPORTANT THIS FROM THE AMOUNT OF EXCLAMATION MARKS!?
subtitle_lang = 'en'
resoultion = '1920x1080'

titles = []
links = []
video_links = []

def check_url(response: Response):
    global video_links
    link = response.url
    look_for = "master.m3u8?"
    if look_for in link:
        print(link)
        video_links.append(link)

def download_videos(video_path: str, video_list: list, video_names: list):
    global video_uri
    global subtitle_uri
    global video_links

    print("Downloading")
    for i, link in enumerate(video_list):
        video_name = video_names[i]

        video_file = f'{video_path}\\{i + 1} {video_name}.mp4'
        subtitle_file = f'{video_path}\\{i + 1} {video_name}.vtt'

        r = requests.get(link)
        master = m3u8.loads(r.text)
        for i in master.data['playlists']:
            res = i['stream_info']
            if res['resolution'] == resoultion:
                video_uri = i['uri']

        for i in master.data['media']:
            media_type = i['type']
            if subtitle_lang in i['language'] and media_type == "SUBTITLES":
                subtitle_uri = i['uri']
        try:
            os.path.exists(video_file)
        except FileExistsError:
            print()

        response = str(requests.get(subtitle_uri).content).split('\\n')
        for x in response:
            if x.startswith("h"):
                print(f">>> Subtitles: ({video_name}) Appending {x}")
                with urllib.request.urlopen(x) as response, open(subtitle_file, 'ab') as out_file:
                    data = response.read()
                    out_file.write(data)
                    out_file.write(bytes('\n', encoding="utf-8"))
        
        try:
            print(f">>> Video: Attempting to download: {video_uri} as {video_file}")
            stream = ffmpeg.input(video_uri)
            stream = ffmpeg.output(stream, video_file)
            ffmpeg.run(stream)
        except Exception as e:
            print(e)

    video_links = []

def make_valid_name(file_name: str):
    avoid_symbols_list = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*"]
    for symbol in avoid_symbols_list:
        letter_len = len(file_name)
        if file_name.find(symbol, 0, letter_len) != -1:
            file_name = file_name.replace(symbol, "-", -1)
    return file_name

def create_folders(course_name: str, unit_names: list[str]):
    file_folder = os.path.dirname(os.path.abspath(__file__))
    course_folder = os.path.join(file_folder, course_name)
    
    try:
        os.makedirs(course_folder)
        print(f"Creating: {course_folder}")
    except FileExistsError:
        print(f"{course_folder} exists; skipping")

    for i, name in enumerate(unit_names):
        unit_folder = os.path.join(course_folder, f'Unit {i + 1} {name}')
        try:
            os.makedirs(unit_folder)
            print(f"Creating: {unit_folder}")
        except FileExistsError:
                print("Folder exists; skipping")

def get_folder(course_name: str, lesson_name: str):
    file_folder = os.path.dirname(os.path.abspath(__file__))
    course_folder = os.path.join(file_folder, course_name)

    for root, dirs, files in os.walk(course_folder):
        for folder in dirs:
            folder_path = os.path.join(root, folder)
            if lesson_name in folder:
                return folder_path

def download_page(url:str):
    sb = sb_cdp.Chrome()
    endpoint_url = sb.get_endpoint_url()
    with sync_playwright() as p:    
        print(f"Opening {url}...")
        browser = p.chromium.connect_over_cdp(endpoint_url)
        context = browser.contexts[0]
        page = context.pages[0]
        context.clear_cookies(name="_domestika_session")
        context.add_cookies([cookie])

        page.on("response", check_url)
        page.goto(url, wait_until="domcontentloaded")

        course_name = make_valid_name(page.locator(".course-header-new__title > a").text_content())
        print(f"Course: {course_name}\n")

        unit_names = []
        unit_name = page.locator(".nav--lateral-new .media-body")
        for name in unit_name.all():
            name = make_valid_name(name.text_content().strip())
            unit_names.append(name)

        create_folders(course_name, unit_names)

        for name in unit_names:
            video_names = []
            video_name = page.locator(".lesson-title > a")
            for named in video_name.all():
                named = make_valid_name(named.text_content())
                video_names.append(named)
                
            container = page.locator(".course--lessons-list__item")
            for i in range(container.count()):
                lesson = container.nth(i)
                lesson_button = lesson.locator(".CoverVideo-playButton.bgc-neutral-100").first
                lesson_button.click()
                page.clock.run_for("05")
                time.sleep(5)
                

            video_path = get_folder(course_name, name)
            print(video_path)
            download_videos(video_path, video_links, video_names)

            next_button = page.locator(".a-button.a-button--small.a-button--text")
            next_button.click()
        

choice_url = input("Enter the link (Be sure the click 'Unit 1' and copy the link from that) ")
download_page(choice_url)
