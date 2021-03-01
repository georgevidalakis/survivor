# See:
# https://github.com/Zulko/moviepy/issues/876 and
# https://github.com/biojet1/moviepy/commit/071297e14a17d60132fee23f846af5437596c68c

import os
import time
import shutil
import urllib.request
import moviepy.editor
from base64 import b64encode
from typing import List, Optional
from IPython.display import HTML, display


def progress(value, max_value):
    return HTML("""
        <progress
            value='{value}'
            max='{max_value}',
            style='width: 100px'
        >
            {value}
        </progress>
    """.format(value=value, max_value=max_value))


class Config(object):

    __slots__ = [
        'downloads_dir_path', 'tmp_dir_path', 'connection_timeout',
        'approx_secs_per_video_segment', 'delay_between_requests_in_secs'
    ]

    def __init__(self):
        self.downloads_dir_path = 'downloads'
        self.tmp_dir_path = 'tmp'
        self.connection_timeout = 5
        self.approx_secs_per_video_segment = 10.0
        self.delay_between_requests_in_secs = 0.2  # ethical


config = Config()


class Date(object):

    __slots__ = ['year', 'month', 'day']

    def __init__(self, year: int, month: int, day: int):
        self.year = f'{year:02d}'
        self.month = f'{month:02d}'
        self.day = f'{day:02d}'


class Duration(object):

    __slots__ = ['hours', 'minutes', 'seconds']

    def __init__(self, seconds: float):
        seconds = int(seconds)
        self.hours = seconds // 3600
        seconds -= 3600 * self.hours
        self.minutes = seconds // 60
        seconds -= 60 * self.minutes
        self.seconds = seconds

    def __str__(self) -> str:
        result_list = []
        if self.hours > 0:
            if self.hours == 1:
                result_list.append('1 hour')
            else:
                result_list.append(f'{self.hours} hours')
        if self.minutes > 0:
            if self.minutes == 1:
                result_list.append('1 minute')
            else:
                result_list.append(f'{self.minutes} minutes')
        if self.seconds > 0:
            if self.seconds == 1:
                result_list.append('1 second')
            else:
                result_list.append(f'{self.seconds} seconds')
        if len(result_list) == 3:
            return f'{result_list[0]}, {result_list[1]} and {result_list[2]}'
        if len(result_list) == 2:
            return f'{result_list[0]} and {result_list[1]}'
        if len(result_list) == 1:
            return result_list[0]
        return '0 seconds'


def read_integer() -> int:
    result_str = input()
    try:
        return int(result_str)
    except ValueError:
        print('ERROR: Expected integer input.')
        exit(1)


def read_date() -> Date:
    print('Input download year (e.g. 2021):', end=' ')
    year = read_integer()
    print('Input download month (e.g. 2):', end=' ')
    month = read_integer()
    print('Input download day (e.g. 24):', end=' ')
    day = read_integer()
    return Date(year, month, day)


def is_downloaded_check(date: Date) -> bool:
    video_file_path = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}/video.mp4'
    return os.path.isfile(video_file_path)


def get_base_url(date: Date) -> str:
    return f'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/GrCyTargeting/Gr/Survivor/survivor{date.year}{date.month}{date.day}xxxx.mp4/media_'


def download_video_segment(base_url: str, video_segment_id: int) -> Optional[bytes]:
    time.sleep(config.delay_between_requests_in_secs)
    url = f'{base_url}{video_segment_id}.ts'
    try:
        response = urllib.request.urlopen(url, timeout=config.connection_timeout)
    except urllib.request.socket.timeout:
        return None
    except urllib.error.URLError:
        return None
    video_segment_data = response.read()
    return video_segment_data


def does_video_segment_exist_check(base_url: str, video_segment_id: int) -> bool:
    video_segment_data = download_video_segment(base_url, video_segment_id)
    return (video_segment_data is not None)


def does_video_exist_check(base_url: str) -> bool:
    return does_video_segment_exist_check(base_url, 1)


def get_num_video_segments(base_url: str) -> int:
    lower_limit = 1
    # Binary search for upper limit
    upper_limit = 1
    while does_video_segment_exist_check(base_url, 2 * upper_limit):
        upper_limit *= 2
    upper_limit *= 2
    # Binary search for result
    while lower_limit < upper_limit:
        mid_video_segment_id = lower_limit + (upper_limit - lower_limit + 1) // 2
        if does_video_segment_exist_check(base_url, mid_video_segment_id):
            lower_limit = mid_video_segment_id
        else:
            upper_limit = mid_video_segment_id - 1
    num_video_segments = lower_limit  # == upper_limit
    return num_video_segments


def get_approx_secs_by_num_video_segments(num_video_segments: int) -> float:
    return num_video_segments * config.approx_secs_per_video_segment


def is_video_segment_downloaded_check(date: Date, video_segment_id: int) -> bool:
    video_ts_file_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts/{video_segment_id}.ts'
    video_mp4_file_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/mp4/{video_segment_id}.mp4'
    return (os.path.isfile(video_ts_file_path) or os.path.isfile(video_mp4_file_path))


def is_video_segment_converted_check(date: Date, video_segment_id: int) -> bool:
    video_mp4_file_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/mp4/{video_segment_id}.mp4'
    return os.path.isfile(video_mp4_file_path)


def get_video_segments_ids_to_download(date: Date, num_video_segments: int) -> List[int]:
    return [
        video_segment_id
        for video_segment_id in range(1, num_video_segments + 1)
        if not is_video_segment_downloaded_check(date, video_segment_id)
    ]


def get_video_segments_ids_to_convert(date: Date, num_video_segments: int) -> List[int]:
    return [
        video_segment_id
        for video_segment_id in range(1, num_video_segments + 1)
        if not is_video_segment_converted_check(date, video_segment_id)
    ]


def create_tmp_dirs(date: Date) -> None:
    video_ts_files_dir = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts'
    video_mp4_files_dir = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/mp4'
    os.makedirs(video_ts_files_dir, exist_ok=True)
    os.makedirs(video_mp4_files_dir, exist_ok=True)


def save_video_segment(date: Date, video_segment_id: int, video_segment_data: bytes) -> None:
    video_ts_file_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts/{video_segment_id}.ts'
    with open(video_ts_file_path, 'wb') as fp:
        fp.write(video_segment_data)


def convert_video_segment(date: Date, video_segment_id: int) -> None:
    video_ts_files_dir = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts'
    video_mp4_files_dir = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/mp4'
    video_ts_file_path = f'{video_ts_files_dir}/{video_segment_id}.ts'
    video_mp4_file_path = f'{video_mp4_files_dir}/{video_segment_id}.mp4'
    os.system(f'ffmpeg -i {video_ts_file_path} {video_mp4_file_path} >{config.tmp_dir_path}/cmd_out.txt 2>&1')


def create_download_dir(date: Date) -> None:
    video_file_dir = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}'
    os.makedirs(video_file_dir, exist_ok=True)


def merge_video_segments(date: Date, num_video_segments: int) -> None:
    video_mp4_files_dir = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/mp4'
    video_segments_as_clips = [
        moviepy.editor.VideoFileClip(f'{video_mp4_files_dir}/{video_segment_id}.mp4')
        for video_segment_id in range(1, num_video_segments + 1)
    ]
    video_as_clip = moviepy.editor.concatenate_videoclips(video_segments_as_clips)
    video_file_path = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}/video.mp4'
    video_as_clip.to_videofile(video_file_path, fps=24, remove_temp=False)


def delete_tmp_dir(date: Date) -> None:
    video_tmp_dir_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}'
    shutil.rmtree(video_tmp_dir_path)


def delete_tmp_audio_files() -> None:
    for file_name in os.listdir():
        if file_name.endswith('.mp3') and file_name.startswith('videoTEMP'):
            os.remove(file_name)


def download_video(date: Date) -> None:
    base_url = get_base_url(date)
    print('Searching for the requested video...')
    if not does_video_exist_check(base_url):
        print('The requested video could not be found. If you are sure that a video exists for the specified date, please contact the app developer.')
        exit(1)
    print('Video found!')
    print()
    print('Computing video\'s duration...')
    # num_video_segments = get_num_video_segments(base_url)
    num_video_segments = 10
    estimated_video_duration_secs = get_approx_secs_by_num_video_segments(num_video_segments)
    estimated_video_duration = Duration(estimated_video_duration_secs)
    print(f'Estimated video duration: {estimated_video_duration}')
    print()
    create_tmp_dirs(date)
    print('Downloading video\'s segments...')
    video_segments_ids_to_download = get_video_segments_ids_to_download(date, num_video_segments)
    download_progress_bar = display(progress(0, len(video_segments_ids_to_download) - 1), display_id=True)
    for progress_idx, video_segment_id in enumerate(video_segments_ids_to_download):
        video_segment_data = download_video_segment(base_url, video_segment_id)
        if video_segment_data is None:
            print('An error happened while downloading a video\' segment. Please try again in a few minutes. If this error persists please contact the app developer.')
            exit(1)
        save_video_segment(date, video_segment_id, video_segment_data)
        download_progress_bar.update(progress(progress_idx + 1, len(video_segments_ids_to_download) - 1))
    print('Video\'s segments downloaded.')
    print()
    print('Converting video\'s segments...')
    video_segments_ids_to_convert = get_video_segments_ids_to_convert(date, num_video_segments)
    conversion_progress_bar = display(progress(0, len(video_segments_ids_to_download) - 1), display_id=True)
    for progress_idx, video_segment_id in enumerate(video_segments_ids_to_convert):
        convert_video_segment(date, video_segment_id)
        conversion_progress_bar.update(progress(progress_idx + 1, len(video_segments_ids_to_download) - 1))
    print('Video\'s segments converted.')
    print()
    print('Merging video\'s segments...')
    create_download_dir(date)
    merge_video_segments(date, num_video_segments)
    print('Video\'s segments merged.')
    print()
    print('Deleting useless files...')
    # delete_tmp_dir(date)
    delete_tmp_audio_files()
    print('Useless files deleted.')
    # print()
    print('Video is ready to play!')
    #video_dir_path = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}'
    #video_dir_abs_path = os.path.abspath(video_dir_path)
    # os.startfile(video_dir_abs_path)


def interact():
    print()
    date = read_date()
    print()
    if is_downloaded_check(date):
        print(f'This video is already downloaded!')
        video_dir_path = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}'
        video_dir_abs_path = os.path.abspath(video_dir_path)
        # os.startfile(video_dir_abs_path)
    else:
        download_video(date)


if __name__ == '__main__':
    interact()
