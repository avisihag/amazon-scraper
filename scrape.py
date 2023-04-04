import os
import re
import json
import pathlib
import argparse
import threading

from requests_html import HTMLSession
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selectorlib import Extractor, selectorlib
from selectorlib.formatter import Formatter
import concurrent.futures

from tqdm import tqdm

from mapping import mapping

# Create an Extractor by reading from the YAML file
e = Extractor.from_yaml_file('food.yml')

TEMPLATES_ROOT = pathlib.Path(__file__).parent / 'templates'
SAVE_FILE = 'save1.txt'
SAVE_FOLDER = 'save'
DATA_FOLDER = 'data'

options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

# create a threading.local object to store progress for each thread separately
thread_local = threading.local()


class Price(Formatter):
    def format(self, text):
        return float(text.replace('$', '').strip())


class Details(Formatter):
    def format(self, text):
        return text.replace(':', '').replace(' ', '_').strip()


class AdditionalValues(Formatter):
    def format(self, text):
        return text.encode("ascii", "ignore").decode().replace('\n', '').strip()


class TechnicalDetails(Formatter):
    def format(self, text):
        return text.strip().replace(' ', '_')


class AdditionalInfo(Formatter):
    def format(self, text):
        return text.strip().replace(' ', '_')


def modify_product_details(info_details):
    data = {}
    if not info_details:
        return data
    for info in info_details:
        string_encode = info.encode("ascii", "ignore")
        info = string_encode.decode()
        key, value = info.replace('\n', '').strip().split(':', maxsplit=1)
        data[key.strip()] = value.strip()
    return data


def cleanup_list_data(info_details):
    data = []
    if not info_details:
        return data
    for info in info_details:
        string_encode = info.encode("ascii", "ignore")
        info = string_encode.decode()
        data.append(info.replace('\n', '').strip())
    return data


def save_progress(url):
    thread_local.progress = url

    # write progress for each thread in a separate file to avoid conflicts
    with open(f'{SAVE_FOLDER}/{SAVE_FILE}_{threading.get_ident()}', 'w') as f:
        f.write(url)


def load_progress():
    # check if progress is available for current thread
    if hasattr(thread_local, 'progress'):
        return thread_local.progress

    # load progress from file specific to current thread
    try:
        with open(f'{SAVE_FILE}_{threading.get_ident()}', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


product_page_extractor = Extractor.from_yaml_file(
    'food.yml',
    formatters=[Price, Details, AdditionalValues, TechnicalDetails, AdditionalInfo]
)

session = HTMLSession()

parser = argparse.ArgumentParser(
    prog='ProgramName',
    description='What the program does',
    epilog='Text at the bottom of help'
)
parser.add_argument('-c', '--category')
parser.add_argument('-p', '--urls_file')
parser.add_argument('-q', '--output_file')
parser.add_argument('-r', '--empty_file')
parser.add_argument('-l', '--links')
parser.add_argument('-s', '--start')
parser.add_argument('-e', '--end')
args = parser.parse_args()
category = args.category
urls_file = args.urls_file
output_file = args.output_file
empty_file = args.empty_file
start = int(args.start)
end = int(args.end)
links = args.links
# print(category)


def write_to_file(_id, _data):
    folder = DATA_FOLDER + "/" + category
    if not os.path.exists(folder):
        os.makedirs(folder)
    f = open(f"{folder}/{_id}", "a")
    json.dump(_data, f)
    f.write("\n")
    f.close()


def scrape(product_url):
    driver.get(product_url)
    html = driver.page_source

    data = {'error': 'Please provide a URL'}
    if product_url:
        if category == 'food':
            data = product_page_extractor.extract(html)
            data['Technical_details'] = cleanup_list_data(data.get('Technical_details', []))
            data['Additional_info'] = cleanup_list_data(data.get('Additional_info', []))
            data['Technical_values'] = cleanup_list_data(data.get('Technical_values', []))
            data['Additional_values'] = cleanup_list_data(data.get('Additional_values', []))
            tech_details = dict(zip(data.get('Technical_details', []), data.get('Technical_values', [])))
            extra_info = dict(zip(data.get('Additional_info', []), data.get('Additional_values', [])))
            tech_details.update(extra_info)
            tech_details.pop('Customer_Reviews', None)
            data['Additional_info'] = tech_details
        elif category in ['electronics', 'books', 'beauty']:
            page_extractor = selectorlib.Extractor.from_yaml_file(f"{category}.yml", formatters=[Price, Details])
            data = page_extractor.extract(html)
            info_details = data.get('Product_details', [])
            data.pop('Product_details', None)
            if info_details:
                data['Product_details'] = modify_product_details(info_details)

    details = data.get('Details', [])
    values = data.get('Product_info', [])

    if details and values:
        try:
            for i, detail in enumerate(details[:-1]):
                data[detail] = values[i]
        except IndexError:
            print("INDEX ERROR")

    data.pop('Details', None)
    data.pop('Product_info', None)

    return data


host = "https://www.amazon.in"


def scrape_urls(url, outfile, emptyfile, pbar):
    data = scrape(host + url)
    match = re.search(r"dp/([A-Z0-9]+)", url)
    if not data.get("Title"):
        # print("####Title Not Matched####")
    if data.get("Title") and match:
        print(match)
        id = match.group(1)
        print(id)
        data["id"] = id
        # print(data)
        json.dump(data, outfile)
        outfile.write("\n")
        write_to_file(id, data)
    else:
        # json.dump(data, outfile)
        # outfile.write("\n")
        # print(data)
        # print("no match")
        emptyfile.write(url)
        emptyfile.write("\n")
    save_progress(url)
    pbar.update(1)


if __name__ == '__main__':
    processed = 0
    processed_url = load_progress()
    i = 0
    with open(urls_file, 'r') as urllist, \
            open(f"{DATA_FOLDER}/{output_file}", 'a') as outfile, \
            open(empty_file, 'a') as emptyfile, \
            open("logs.txt", 'a') as logfile:
        urls = urllist.read().splitlines()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            pbar = tqdm(total=end-start)
            for url in urls[start:end]:
                url = url.strip('"')
                processed += 1
                if url == processed_url:
                    print(f"Skipping {url} as it was already processed", end="\r")
                    continue
                else:
                    # pbar.update(1)
                    pass
                print("Downloading %s" % url, end="\r")
                # scrape_urls(url, outfile, emptyfile, pbar)
                futures.append(executor.submit(scrape_urls, url, outfile, emptyfile, pbar))
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    print(future, f'generated an exception: {exc}')
            pbar.close()


# if __name__ == '__main__':
#     if not os.path.exists(DATA_FOLDER):
#         os.makedirs(DATA_FOLDER)
#     urls = mapping.get(category)
#     # Start the browser and perform scraping
#     for url in urls:
#         if url == load_progress():
#             continue
#         try:
#             data = scrape(url)
#             print(data)
#             if data and data.get('name'):
#                 with open(f"{DATA_FOLDER}/{data['name']}.json", 'w') as f:
#                     json.dump(data, f, indent=2)
#             save_progress(url)
#         except Exception as e:
#             print(f"Failed to scrape {url}: {str(e)}")
#         finally:
#             # sleep(3)
#             pass
#     driver.quit()
