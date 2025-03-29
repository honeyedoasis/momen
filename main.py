import csv
import json
import os
import requests
import mimetypes

from time import sleep

my_token = ""
my_username = ""
artist_id = "2"

known_types = ['FULL', 'ORIGIN', 'CARD_BACK', 'AUTOGRAPH', 'VOICE_MESSAGE', 'AUTOGRAPH_SPECIAL_NOTE', 'SPECIAL_NOTE']

edition_data = None

downloaded_path = 'temp/downloaded.txt'

def sanitize_filename(filename, replacement=''):
    invalid_chars = r'<>:"/\\|?*'
    for c in invalid_chars:
        filename = filename.replace(c, '')
    return filename

def download_file(url, file_path, timeout=10, skip_exists=True):
    with requests.Session() as session:
        try:
            response = session.get(url, timeout=timeout)

            content_type = response.headers['content-type']
            ext = mimetypes.guess_extension(content_type)

            full_path = f'{file_path}{ext}'
            if skip_exists and os.path.exists(full_path):
                # print('FILE EXISTS', full_path)
                return 0

            # print(f"\tDownloading {file_path} {url}")

            # Check if the request was successful
            if response.status_code == 200:
                # Open a file in binary write mode to save the image
                with open(f'{file_path}{ext}', "wb") as file:
                    file.write(response.content)
                return 1
            else:
                print(f"Failed to download file. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return -1
        except Exception as e:
            print(f"exception: {e}")
            return -1

    return -1


def request_auth():
    global my_token
    global my_username

    if len(my_token) == 0:
        while True:
            my_token = input('Enter your token: ')
            if len(my_token) > 0 and len(my_token.split('.')) == 3:
                print('Token expires in 1 day!')
                break
            else:
                print('ERROR: Invalid token')

    if len(my_username) == 0:
        while True:
            my_username = input('Enter your username: ')
            if len(my_username) > 0:
                break
            else:
                print('ERROR: Invalid username')


def send_request(api_url, use_post=False):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'language': 'en',
        'sec-ch-ua-platform': '"Android"',
        'Authorization': my_token
    }

    url = api_url

    with requests.Session() as session:
        session.headers.update(headers)

        try:
            # print(url)
            if use_post:
                data = {
                    "sortType": "OWNED_EDITION_COUNT_DESC",
                    "isOnSale": False,
                    "size": 10
                }

                response = session.post(url, json=data)  # print('POST', response)
            else:
                response = session.get(url)  # print('GET', response)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Exception: {e}")


def send_request_next(api_url, use_post=False, msg='Loading data'):
    out_data = []
    next = None
    while True:
        next_api = api_url
        if next:
            next_api = f'{api_url}&next={next}'

        response = send_request(next_api, use_post)
        out_data += response['data']
        print(msg, len(out_data))

        next = response['cursor'].get('next')
        if not next:
            return out_data

        sleep(1)


def get_take_id(take):
    return take['takeId']


def get_board_id(board):
    return board['collectBoardId']


def get_boards():
    with open('boards_data.json', 'r') as f:
        boards = json.load(f)

    take_map = dict()
    for b in boards:
        for t in b['takes']:
            if t['takeId'] not in take_map:
                take_map[t['takeId']] = []
            take_map[t['takeId']].append(b['collectBoardId'])

    dupe_boards = set()
    for b in boards:
        valid_board = False
        for t in b['takes']:
            if len(take_map[t['takeId']]) == 1:
                valid_board = True
                break

        if not valid_board:
            dupe_boards.add(b['collectBoardId'])  # print(b)

    mapping = dict()
    for r in boards:
        id = r['collectBoardId']
        if id in dupe_boards:
            continue

        mapping[id] = r

    return sorted(mapping.values(), key=get_board_id)


def get_take_book():
    book_path = f'temp/take_book-{artist_id}.json'
    if os.path.exists(book_path):
        print(f'Loaded book {book_path}')
        with open(book_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    api = f'https://momentica.com/api/v1/marketplace/artists/{artist_id}/take-books/_search'
    data = send_request_next(api, True)
    with open(book_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)

    return data


def get_all_takes():
    takes_path = f'temp/takes-{artist_id}.json'
    if os.path.exists(takes_path):
        print(f'Loaded takes {takes_path}')
        with open(takes_path, 'r', encoding='utf-8') as f:
            return json.load(f)


    take_url = f'https://momentica.com/api/v1/artist-pages/{artist_id}/takes?sortType=RELEASED_AT_DESC&pageSize=100'
    takes_data = send_request_next(take_url, msg='Loading takes')

    with open(takes_path, 'w', encoding='utf-8') as f:
        json.dump(takes_data, f)
        print('Saved takes to', takes_path)
    return takes_data


def make_mapping(book):
    folder_map = dict()
    for collection in book:
        # print(collection['name'])
        collection_name = sanitize_filename(collection['name'])
        for category in collection['categories']:
            category_name = sanitize_filename(category['name'])
            # print('\t', category['name'])
            for take in category['takes']:
                folder = f'{collection_name}/{category_name}'
                folder_map[take['takeId']] = folder

    return folder_map

LINKS_PATH = 'links.csv'
LINKS_HEADERS = ['TAKE_ID', 'ORIGIN', 'CARD_BACK', 'AUTOGRAPH', 'AUTOGRAPH_SPECIAL_NOTE', 'VOICE_MESSAGE', 'SPECIAL_NOTE']

def get_links_csv():
    if os.path.exists(LINKS_PATH):
        # with open(LINKS_PATH, 'r', encoding='utf-8') as f:
        #     return json.load(f)
        with open(LINKS_PATH, "r", newline="") as file:
            return list(csv.DictReader(file, delimiter=","))

    return []


def download_owned(all_takes):
    book = get_take_book()
    mapping = make_mapping(book)

    owned_takes = [t for t in all_takes if t['isOwned']]

    downloaded = []
    if os.path.exists(downloaded_path):
        with open(downloaded_path, 'r', encoding='utf-8') as f:
            downloaded = [int(x) for x in f.read().splitlines()]

    all_links = get_links_csv()
    with open(downloaded_path, 'a', encoding='utf-8') as archive_file:
        for i, take in enumerate(owned_takes):
            take_id = take['takeId']
            if take_id in downloaded:
                # print('Skipping already downloaded ', take_id)
                continue

            success, link_row = download_take(take, mapping)
            print(f'{i}/{len(owned_takes)}: {take_id} {take['name']}')

            if success:
                archive_file.write(f'{take_id}\n')
                all_links.append(link_row)
                # print(link_row)
                downloaded.append(take_id)
            else:
                print('\tFailed to download', take_id)
            # if i > 8:
            #     break

    # print(all_links)

    with open(LINKS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, delimiter=",", fieldnames=LINKS_HEADERS)
        writer.writeheader()
        writer.writerows(all_links)
        print("Wrote links to", LINKS_PATH)


def make_links_row(take_id):
    return {
        'TAKE_ID': take_id,
        'ORIGIN': '',
        'CARD_BACK': '',
        'AUTOGRAPH': '',
        'AUTOGRAPH_SPECIAL_NOTE': '',
        'VOICE_MESSAGE': '',
        'SPECIAL_NOTE': '',
    }


def get_take_folder(take, folder_map):
    take_id = take['takeId']
    folder = folder_map.get(take_id, None)

    if not folder:
        folder = sanitize_filename(take['name'].split(',')[1])

    folder = f'momentica/{folder}'
    os.makedirs(folder, exist_ok=True)
    return folder

def download_take(take, folder_map):
    # print(take)
    folder = get_take_folder(take, folder_map)
    member_name = take['name'].split(',')[0]
    take_id = take['takeId']
    links_row = make_links_row(take_id)

    contents = take['contents']
    assets = contents['assets']
    for asset in assets:
        asset_type = asset['type']
        asset_url = asset['original']['url']

        if asset_type in links_row:
            links_row[asset_type] = asset_url

        if asset_type not in known_types:
            print('UNKNOWN TYPE ', asset_type)
            print(take) # breakpoint()

        elif asset_type == 'CARD_BACK':
            card_path = f'{folder}/{member_name}-CARD_BACK'
            if download_file(asset_url, card_path) == -1:
                return False, None
        elif asset_type == 'AUTOGRAPH':
            autograph_path = f'{folder}/{member_name}-AUTOGRAPH'
            if download_file(asset_url, autograph_path) == -1:
                return False, None
        elif asset_type == 'AUTOGRAPH_SPECIAL_NOTE':
            autograph_note_path = f'{folder}/{member_name}-AUTOGRAPH_SPECIAL_NOTE'
            if download_file(asset_url, autograph_note_path) == -1:
                return False, None
        elif asset_type == 'VOICE_MESSAGE':
            voice_path = f'{folder}/{member_name}-VOICE_MESSAGE-{take_id}'
            if download_file(asset_url, voice_path) == -1:
                return False, None
        elif asset_type == 'SPECIAL_NOTE':
            special_note = f'{folder}/{member_name}-SPECIAL_NOTE-{take_id}'
            if download_file(asset_url, special_note) == -1:
                return False, None

    origin_asset = contents['originAsset']
    origin_url = origin_asset['url']
    links_row['ORIGIN'] = origin_url
    origin_path = f'{folder}/{member_name}-{origin_asset['type']}-{take_id}'
    if download_file(origin_url, origin_path) == -1:
        return False, None

    return True, links_row

def make_book_csv():
    book = get_take_book()

    out_rows = []
    for collection in book:
        print(collection['name'])
        for category in collection['categories']:
            print('\t', category['name'])
            for take in category['takes']:
                row = {
                    'TakeId': take['takeId'],
                    'Collection': collection['name'],
                    'Category': category['name'],
                    'Url': f'https://momentica.com/take/{take['takeUuid']}'
                }
                out_rows.append(row)  # break
    with open("temp/drive_book.csv", mode="w", newline="\n", encoding='utf-8') as file:
        fieldnames = ["TakeId", "Collection", "Category", "Url"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

def log_takes(all_takes, write_to_file):
    owned_takes = [t for t in all_takes if t['isOwned']]
    missing_takes = [t for t in all_takes if not t['isOwned']]

    if write_to_file:
        os.makedirs('log', exist_ok=True)
        write_takes(owned_takes, f'log/owned_takes-{artist_id}.csv')
        write_takes(missing_takes, f'log/missing_takes-{artist_id}.csv')

    print(f'Total takes: {len(all_takes)}, Owned: {len(owned_takes)}, Missing: {len(missing_takes)}')


def write_takes(take_list, file_path):
    lines = []
    for t in take_list:
        line = [str(t['takeId']), t['name'].replace(',', ''), f'https://momentica.com/take/{t['uuid']}']
        lines.append(', '.join(line))

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        print('Created', file_path)


def main():
    global my_token
    global my_username
    global artist_id

    # load from
    config_path = 'config.json'
    with open(config_path, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
        artist_id = config['artist']
        my_token = config['token']
        my_username = config['username']

    request_auth()

    print('Username:', my_username)
    print('Token:', my_token)
    print('Artist:', artist_id)

    test_command = f'https://momentica.com/api/v2/users/editions?username={my_username}&artistId={artist_id}&sortType=OWNED_AT_DESC&pageSize=1'
    if not send_request(test_command):
        input('ERROR: invalid username or token. You need to refresh your token once a day!!. Press ENTER to exit.')
        return

    # make_book_csv()
    os.makedirs('temp', exist_ok=True)

    all_takes = get_all_takes()
    download_owned(all_takes)

    write_to_file = input('Do you want to save your owned and missing takes? [y]/[n]: ').lower() == 'y'
    log_takes(all_takes, write_to_file)

    input('🍀Download finished🍀 Press ENTER to exit.')

'''
TODO
ALL_ARTIST_TAKES: https://momentica.com/api/v1/artist-pages/2/takes?sortType=RELEASED_AT_DESC&pageSize=100
'''
if __name__ == '__main__':
    main()
