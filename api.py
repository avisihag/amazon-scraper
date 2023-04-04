import aiohttp
import pathlib

import aiohttp_jinja2
import jinja2
from aiohttp import web

import selectorlib
from selectorlib.formatter import Formatter

TEMPLATES_ROOT = pathlib.Path(__file__).parent / 'templates'


class Price(Formatter):
    def format(self, text):
        price = text.replace('$','').strip()
        return float(price)


class Details(Formatter):
    def format(self, text):
        print("#######format######")
        details = text.replace(':', '').replace(' ', '_').strip()
        return details


class AdditionalValues(Formatter):
    def format(self, text):
        string_encode = text.encode("ascii", "ignore")
        info = string_encode.decode()
        return info.replace('\n', '').strip()


class TechnicalDetails(Formatter):
    def format(self, text):
        data = text.strip().replace(' ', '_')
        return data


class AdditionalInfo(Formatter):
    def format(self, text):
        data = text.strip().replace(' ', '_')
        return data


product_page_extractor = selectorlib.Extractor.from_yaml_file(
    'food.yml',
    formatters=[Price, Details, AdditionalValues, TechnicalDetails, AdditionalInfo]
)

app = web.Application()
loader = jinja2.FileSystemLoader(str(TEMPLATES_ROOT))
jinja_env = aiohttp_jinja2.setup(app, loader=loader)


@aiohttp_jinja2.template('index.html')
async def index(request):
    return {}


def modify_product_details(info_details):
    data = {}
    for info in info_details:
        string_encode = info.encode("ascii", "ignore")
        info = string_encode.decode()
        key, value = info.replace('\n', '').strip().split(':', maxsplit=1)
        data[key.strip()] = value.strip()
    return data


async def get_product_page(request):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        product_url = await request.json()
        data = {'error': 'Please provide a URL'}
        if product_url:
            html = await fetch(session, product_url.get('url'))
            category = product_url.get('category')
            print(category)
            if category == 'food':
                data = product_page_extractor.extract(html)
                tech_details = dict(zip(data.get('Technical_details', []), data.get('Technical_values', [])))
                extra_info = dict(zip(data.get('Additional_info', []), data.get('Additional_values', [])))
                if tech_details and extra_info:
                    tech_details.update(extra_info)
                elif extra_info:
                    tech_details = extra_info
                data.pop('Technical_details', None)
                data.pop('Additional_info', None)
                data.pop('Technical_values', None)
                data.pop('Additional_values', None)
                tech_details.pop('Customer_Reviews', None)
                data['Additional_info'] = tech_details
            elif category == 'electronics':
                page_extractor = selectorlib.Extractor.from_yaml_file('selectors.yml', formatters=[Price, Details])
                data = page_extractor.extract(html)
            elif category == 'books':
                page_extractor = selectorlib.Extractor.from_yaml_file('books.yml', formatters=[Price, Details])
                data = page_extractor.extract(html)
                info_details = data.get('Product_details', [])
                data.pop('Product_details', None)
                if info_details:
                    data['Product_details'] = modify_product_details(info_details)
            elif category == 'beauty':
                page_extractor = selectorlib.Extractor.from_yaml_file('beauty.yml', formatters=[Price, Details])
                data = page_extractor.extract(html)
                info_details = data.get('Product_details', [])
                data.pop('Product_details', None)
                if info_details:
                    data['Product_details'] = modify_product_details(info_details)

        details = data.get('Details', [])
        values = data.get('Product_info', [])

        if details:
            for i in range(len(details)):
                data[details[i]] = values[i]

        data.pop('Details', None)
        data.pop('Product_info', None)
        print(data)

    return web.json_response({"res": data})
    # return web.json_response(data)
# app.add_routes([web.get('/', get_product_page, name='index')])
router = app.router
router.add_get('/', index, name='index')
router.add_post('/scrape', get_product_page, name='scrape')


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


if __name__ == '__main__':
    aiohttp.web.run_app(app, port=8090)
