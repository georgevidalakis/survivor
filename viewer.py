import os
import time
import shutil
import urllib.request
from progress.bar import Bar
from typing import List, Optional


class Config(object):

    __slots__ = [
        'downloads_dir_path', 'tmp_dir_path', 'segments_list_file_name',
        'connection_timeout', 'approx_secs_per_video_segment',
        'delay_between_requests_in_secs'
    ]

    def __init__(self):
        self.downloads_dir_path = 'downloads'
        self.tmp_dir_path = 'tmp'
        self.segments_list_file_name = 'segments_list.txt'
        self.connection_timeout = 5
        self.approx_secs_per_video_segment = 10.0
        self.delay_between_requests_in_secs = 1.1  # ethical


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
    print('Input download month (e.g. 3):', end=' ')
    month = read_integer()
    print('Input download day (e.g. 29):', end=' ')
    day = read_integer()
    return Date(year, month, day)


def is_downloaded_check(date: Date) -> bool:
    video_file_path = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}/video.mp4'
    return os.path.isfile(video_file_path)


def get_base_url(date: Date) -> str:
    return f'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/GrCyTargeting/Gr/Survivor/survivor{date.year}{date.month}{date.day}.mp4/media_'
    # return f'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/GrCyTargeting/Gr/Survivor/ntafy{date.year}{date.month}{date.day}.mp4/media_'


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
    return does_video_segment_exist_check(base_url, 0)


def get_num_video_segments(base_url: str) -> int:
    lower_limit = 0
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
    num_video_segments = lower_limit + 1  # == upper_limit + 1
    return num_video_segments


def get_approx_secs_by_num_video_segments(num_video_segments: int) -> float:
    return num_video_segments * config.approx_secs_per_video_segment


def is_video_segment_downloaded_check(date: Date, video_segment_id: int) -> bool:
    video_ts_file_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts/{video_segment_id}.ts'
    return os.path.isfile(video_ts_file_path)


def get_video_segments_ids_to_download(date: Date, num_video_segments: int) -> List[int]:
    return [
        video_segment_id
        for video_segment_id in range(num_video_segments)
        if not is_video_segment_downloaded_check(date, video_segment_id)
    ]


def create_tmp_dirs(date: Date) -> None:
    video_ts_files_dir = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts'
    os.makedirs(video_ts_files_dir, exist_ok=True)


def save_video_segment(date: Date, video_segment_id: int, video_segment_data: bytes) -> None:
    video_ts_file_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts/{video_segment_id}.ts'
    with open(video_ts_file_path, 'wb') as fp:
        fp.write(video_segment_data)


def create_download_dir(date: Date) -> None:
    video_file_dir = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}'
    os.makedirs(video_file_dir, exist_ok=True)


def merge_video_segments(date: Date, num_video_segments: int) -> None:
    video_ts_files_dir = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/ts'
    input_args = [
        f'file \'ts/{video_segment_id}.ts\''
        for video_segment_id in range(num_video_segments)
    ]
    segments_list_file_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}/{config.segments_list_file_name}'
    with open(segments_list_file_path, 'w') as fp:
        fp.write('\n'.join(input_args))
    video_file_path = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}/video.mp4'
    os.system(f'ffmpeg -safe 0 -f concat -i {segments_list_file_path} -c copy {video_file_path}')


# def delete_tmp_dir(date: Date) -> None:
#     video_tmp_dir_path = f'{config.tmp_dir_path}/{date.year}_{date.month}_{date.day}'
#     shutil.rmtree(video_tmp_dir_path)


def download_video(date: Date) -> None:
    base_url = get_base_url(date)
    print('Searching for the requested video...')
    if not does_video_exist_check(base_url):
        print('The requested video could not be found. If you are sure that a video exists for the specified date, please contact the app developer.')
        exit(1)
    print('Video found!')
    print()
    print('Computing video\'s duration...')
    num_video_segments = get_num_video_segments(base_url)
    # num_video_segments = 10
    estimated_video_duration_secs = get_approx_secs_by_num_video_segments(num_video_segments)
    estimated_video_duration = Duration(estimated_video_duration_secs)
    print(f'Estimated video duration: {estimated_video_duration}')
    print()
    create_tmp_dirs(date)
    print('Downloading video\'s segments...')
    video_segments_ids_to_download = get_video_segments_ids_to_download(date, num_video_segments)
    bar = Bar('Processing', max=len(video_segments_ids_to_download))
    for progress_idx, video_segment_id in enumerate(video_segments_ids_to_download):
        video_segment_data = download_video_segment(base_url, video_segment_id)
        if video_segment_data is None:
            print('An error happened while downloading a video\' segment. Please try again in a few minutes. If this error persists please contact the app developer.')
            exit(1)
        save_video_segment(date, video_segment_id, video_segment_data)
        bar.next()
    bar.finish()
    print('Video\'s segments downloaded.')
    print()
    print('Merging video\'s segments.')
    create_download_dir(date)
    merge_video_segments(date, num_video_segments)
    print('Video\'s segments merged.')
    print()
    # print('Deleting useless files...')
    # delete_tmp_dir(date)
    # print('Useless files deleted.')
    print()
    print('Video is ready to play!')
    video_dir_path = f'{config.downloads_dir_path}/{date.year}_{date.month}_{date.day}'
    video_dir_abs_path = os.path.abspath(video_dir_path)
    os.startfile(video_dir_abs_path)


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
