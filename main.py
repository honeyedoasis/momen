import csv
import json
import os
import requests
import mimetypes

from time import sleep

my_token = None
my_username = None

known_types = ['FULL', 'ORIGIN', 'CARD_BACK', 'AUTOGRAPH', 'VOICE_MESSAGE', 'AUTOGRAPH_SPECIAL_NOTE', 'SPECIAL_NOTE']

edition_data = None


def download_file(url, file_path, timeout=10, skip_exists=True):
    with requests.Session() as session:
        try:
            print(f"Downloading {file_path} {url}")
            response = session.get(url)

            content_type = response.headers['content-type']
            ext = mimetypes.guess_extension(content_type)

            full_path = f'{file_path}{ext}'
            if skip_exists and os.path.exists(full_path):
                print('FILE EXISTS', full_path)
                return 0

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
            return None
        except Exception as e:
            print(f"exception: {e}")
            return None

    return -1


def request_auth():
    global my_token
    global my_username

    while True:
        my_token = input('Enter your token:')
        if len(my_token) > 0 and len(my_token.split('.')) == 3:
            print('Token expires in 1 day!')
            break
        else:
            print('ERROR: Invalid token')

    while True:
        my_username = input('Enter your username:')
        if len(my_username) > 0:
            break
        else:
            print('ERROR: Invalid username')


def has_take(base_path, take_id):
    for f in os.listdir(base_path):
        if f.startswith(str(take_id)):
            return True
    return False


def download_board(data):
    print(data)
    board = data['collectBoard']
    board_name = board['name']
    board_thumb = board['thumbnail']['url']

    board_api = f'https://momentica.com/api/v1/collect-board?name={board_name}&username={my_username}'
    takes_data = send_request(board_api)
    all_takes = takes_data['takes']

    base_dir = f'momentica/{board_name}'

    for take in all_takes:
        take_path = f'{base_dir}/{take['takeId']}'
        if take['isOwned'] and not has_take(base_dir, take['takeId']):
            os.makedirs(base_dir, exist_ok=True)

            # download_take(take, take_path)


# def download_take(take, take_path):
#     print(f'Downloading take {take['takeId']}')
#     print(take['thumbnail']['url'])
#     download_file(take['thumbnail']['url'], take_path)

def download_take2(take_id):
    take = f'https://momentica.com/api/v1/takes/{take_id}'
    contents = take['contents']

    card_back_url = contents['cardBackImage']['url']

    assets = contents['assets']
    for asset in assets:
        asset_id = asset['original']['uuid']
        if asset['original']['type'] == 'VIDEO':
            video_url = asset['original']['url']
            thumb_url = asset['thumbnail']['url']
        elif asset['original']['type'] == 'IMAGE':
            image_url = asset['original']['url']
        else:
            print('UNKNOWN ASSET TYPE ', asset['original']['type'])
            breakpoint()


def send_request(api_url, use_post=False):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'language': 'en',
        'sec-ch-ua-platform': '"Android"',
    }

    url = api_url

    with requests.Session() as session:
        session.headers.update(headers)
        session.headers.update({
            'Authorization': f'Bearer {my_token}'
        })

        print(session.headers)
        try:
            print(url)
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


def send_request_next(api_url, use_post=False):
    out_data = []
    next = None
    while True:
        next_api = api_url
        if next:
            next_api = f'{api_url}&next={next}'

        response = send_request(next_api, use_post)
        print(response['data'])
        out_data += response['data']
        print('Loaded data', len(response['data']), len(out_data))

        next = response['cursor'].get('next')
        if not next:
            print(out_data)
            return out_data

        sleep(5)


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
    book_path = 'take_book.json'
    if os.path.exists(book_path):
        print(f'Loaded book {book_path}')
        with open(book_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    api = 'https://momentica.com/api/v1/marketplace/artists/2/take-books/_search'
    data = send_request_next(api, True)
    with open(book_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def write_takes_list():
    api = 'https://momentica.com/api/v1/artist-pages/2/takes?pageSize=100&sortType=RELEASED_AT_DESC'
    all_takes = send_request_next(api)
    with open('all_takes.json', 'w', encoding='utf-8') as f:
        json.dump(all_takes, f)


def write_detailed_takes():
    out = []
    with open('all_takes.json', 'r', encoding='utf-8') as f:
        all_takes = json.load(f)

    for i, t in enumerate(all_takes):
        api = f'https://momentica.com/api/v2/takes/{t['uuid']}'
        out.append(send_request(api))  # if i > 2:  #     break

    with open('takes_data.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=4)


def get_owned_editions():
    owned_path = 'owned_takes.json'
    if os.path.exists(owned_path):
        print(f'Loaded editions {owned_path}')
        with open(owned_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    take_url = f'https://momentica.com/api/v2/users/editions?username={my_username}&artistId=2&sortType=OWNED_AT_DESC&pageSize=100'
    owned_data = send_request_next(take_url)

    with open(owned_path, 'w', encoding='utf-8') as f:
        json.dump(owned_data, f)
        print(f'Saved {len(owned_data)} takes to {owned_path}')


def make_mapping(book):
    folder_map = dict()
    for collection in book:
        print(collection['name'])
        for category in collection['categories']:
            print('\t', category['name'])
            for take in category['takes']:
                folder = f'{collection['name']}/{category['name']}'
                folder_map[take['takeId']] = folder
    return folder_map


def download_owned():
    book = get_take_book()
    mapping = make_mapping(book)
    # for id, folder in mapping.items():
    #     print(id, folder)

    editions = get_owned_editions()
    for edition in editions:
        take = edition['take']
        download_edition_take(take, mapping)  # break


def download_edition_take(take, folder_map):
    take_id = take['id']
    folder = folder_map.get(take_id, 'unknown')
    dest_folder = f'momentica/{folder}'
    os.makedirs(dest_folder, exist_ok=True)

    if os.path.exists(dest_folder):
        if has_take(dest_folder, take_id):
            return

    download_real_take(take_id, dest_folder)


def download_real_take(take_id, folder):
    url = f'https://momentica.com/api/v1/takes/{take_id}'
    full_data = send_request(url)

    member_name = full_data['artistMembers'][0]['name']

    print(full_data)
    contents = full_data['contents']

    assets = contents['assets']
    for asset in assets:
        type = asset['type']
        asset_url = asset['original']['url']

        if type not in known_types:
            print('UNKNOWN TYPE ', type)
            print(full_data)
            breakpoint()

        elif type == 'CARD_BACK':
            card_path = f'{folder}/{member_name}-CARD_BACK'
            download_file(asset_url, card_path)
        elif type == 'AUTOGRAPH':
            autograph_path = f'{folder}/{member_name}-AUTOGRAPH'
            download_file(asset_url, autograph_path)
        elif type == 'AUTOGRAPH_SPECIAL_NOTE':
            autograph_note_path = f'{folder}/{member_name}-AUTOGRAPH_SPECIAL_NOTE'
            download_file(asset_url, autograph_note_path)
        elif type == 'VOICE_MESSAGE':
            voice_path = f'{folder}/{take_id}-VOICE_MESSAGE'
            download_file(asset_url, voice_path)
        elif type == 'SPECIAL_NOTE':
            special_note = f'{folder}/{take_id}-SPECIAL_NOTE'
            download_file(asset_url, special_note)

    origin_asset = contents['originAsset']
    origin_url = origin_asset['url']
    origin_path = f'{folder}/{take_id}'
    download_file(origin_url, origin_path)


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
                    'Url': ''
                }
                out_rows.append(row)  # break
    with open("drive_book.csv", mode="w", newline="\n", encoding='utf-8') as file:
        fieldnames = ["TakeId", "Collection", "Category", "Url"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)


if __name__ == '__main__':

    if os.path.exists('test_auth'):
        with open('test_auth') as f:
            my_token, my_username = f.read().splitlines()
    else:
        request_auth()

    if my_token is None:
        input('ERROR: invalid token. Press any key to exit.')
    if my_username is None:
        input('ERROR: invalid username. Press any key to exit.')

    download_owned()  # input('🍀Download finished🍀 Press any key to exit.')
