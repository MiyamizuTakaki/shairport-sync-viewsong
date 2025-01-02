import os
import base64
import xml.etree.ElementTree as ET
import time
import board
import digitalio
import adafruit_rgb_display.st7735 as st7735
from PIL import Image, ImageDraw, ImageFont
from threading import Thread, Lock
from inotify_simple import INotify, flags

# SPI 屏幕配置
spi = board.SPI()
dc_pin = digitalio.DigitalInOut(board.D24)  # GPIO24
reset_pin = digitalio.DigitalInOut(board.D25)  # GPIO25
cs_pin = digitalio.DigitalInOut(board.CE0)  # CS 引脚 GPIO8 (CE0)

for pin in [dc_pin, reset_pin, cs_pin]:
    pin.direction = digitalio.Direction.OUTPUT

COVER_ART_DIR = "/tmp/shairport-sync/.cache/coverart"
PIPE_PATH = "/tmp/shairport-sync-metadata"
TEMP_COVER_PATH = "/tmp/current_cover.jpg"

# 显示相关
metadata = {"Title": "", "Artist": "", "Album": ""}
cover_art_memory = None
font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
font_size = 14
font = ImageFont.truetype(font_path, font_size)

# 滚动参数
scroll_position = 0
scroll_speed = 2  # 增加滚动速度
scroll_reset_delay = 5  # 减少延迟时间以更快滚动
scroll_counter = 0
loop_scroll = True
artist_scroll_position = 0
artist_scroll_counter = 0

# 线程锁，防止 SPI 访问冲突
display_lock = Lock()

# 屏幕初始化
def init_display():
    global disp
    if spi.try_lock():
        spi.configure(baudrate=16000000)
        spi.unlock()

    disp = st7735.ST7735R(
        spi, cs=cs_pin, dc=dc_pin, rst=reset_pin,
        width=128, height=160, rotation=0, bgr=True
    )

# 确保封面目录存在
def ensure_cover_art_dir():
    os.makedirs(COVER_ART_DIR, exist_ok=True)
    print(f"✅ 目录已就绪: {COVER_ART_DIR}")

# 解析元数据并更新
def parse_metadata():
    if not os.path.exists(PIPE_PATH):
        print(f"Pipe {PIPE_PATH} not found. Creating...")
        os.mkfifo(PIPE_PATH)

    print("Listening for metadata...")

    buffer = ""
    while True:
        try:
            with open(PIPE_PATH, "r") as f:
                while True:
                    xml_data = f.readline().strip()
                    buffer += xml_data
                    if xml_data.endswith("</item>"):
                        process_metadata(buffer)
                        buffer = ""
        except Exception as e:
            print(f"Error reading pipe: {e}")
            time.sleep(3)

# 解析 XML 数据
def process_metadata(xml_data):
    global metadata, scroll_position, scroll_counter, artist_scroll_position, artist_scroll_counter
    wrapped_xml = f"<root>{xml_data}</root>"
    try:
        root = ET.fromstring(wrapped_xml)
        new_metadata = {}
        for item in root.findall('item'):
            code = item.find('code').text
            data_element = item.find('data')

            if data_element is not None and data_element.text:
                decoded_data = base64.b64decode(data_element.text).decode('utf-8', 'ignore')
                if code == '6d696e6d':
                    new_metadata['Title'] = decoded_data
                    scroll_position = 0
                    scroll_counter = 0
                elif code == '61736172':
                    new_metadata['Artist'] = decoded_data
                    artist_scroll_position = 0
                    artist_scroll_counter = 0
                elif code == '6173616c':
                    new_metadata['Album'] = decoded_data
        
        metadata.update(new_metadata)

    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")

# 监听封面变化
def monitor_cover_art():
    global cover_art_memory
    ensure_cover_art_dir()

    inotify = INotify()
    watch_flags = flags.CREATE | flags.MODIFY
    inotify.add_watch(COVER_ART_DIR, watch_flags)

    print(f"监控封面目录: {COVER_ART_DIR}")

    while True:
        for event in inotify.read(timeout=1000):
            if event.name.startswith("cover-"):
                latest_cover = os.path.join(COVER_ART_DIR, event.name)
                try:
                    cover_art_memory = Image.open(latest_cover).convert("RGB").resize((128, 128))
                    cover_art_memory.save(TEMP_COVER_PATH, "JPEG", quality=20)
                except Exception as e:
                    print(f"封面加载失败: {e}")

# 滚动线程

def scroll_text():
    global scroll_position, scroll_counter, artist_scroll_position, artist_scroll_counter
    while True:
        with display_lock:
            image = Image.new("RGB", (128, 160), "black")
            draw = ImageDraw.Draw(image)

            if cover_art_memory:
                image.paste(cover_art_memory, (0, 0))

            title_text = f"{metadata['Title']}"
            artist_text = f"{metadata['Artist']}"
            max_title_width = draw.textlength(title_text, font=font)
            max_artist_width = draw.textlength(artist_text, font=font)

            if max_title_width > 128:
                scroll_counter += 1
                if scroll_counter > scroll_reset_delay:
                    scroll_position += scroll_speed
                    if scroll_position > max_title_width:
                        scroll_position = 0 if loop_scroll else -128
                        scroll_counter = 0

            if max_artist_width > 128:
                artist_scroll_counter += 1
                if artist_scroll_counter > scroll_reset_delay:
                    artist_scroll_position += scroll_speed
                    if artist_scroll_position > max_artist_width:
                        artist_scroll_position = 0 if loop_scroll else -128
                        artist_scroll_counter = 0

            draw.text((-scroll_position, 130), title_text, font=font, fill="white")
            draw.text((-artist_scroll_position, 145), artist_text, font=font, fill="cyan")

            disp.image(image)
        time.sleep(0.05)

if __name__ == "__main__":
    init_display()
    Thread(target=monitor_cover_art, daemon=True).start()
    Thread(target=scroll_text, daemon=True).start()
    parse_metadata()
