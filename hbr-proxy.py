#!/usr/bin/env python3.6

# I wanted to learn more about async/await and asyncio, so this issue was chance to do it in this context

import asyncio
import aiohttp
from aiohttp import web
from urllib.parse import urljoin
import logging
import re
import bs4

logger = logging.getLogger(__name__)

BASE_URL = 'https://habrahabr.ru/'

change_rex = re.compile(r'(^|\s)([a-zA-ZА-Яа-я]{6})(\s|$)', re.IGNORECASE)


def do_replaces(soup):
    if soup.name and soup.name.lower() in {'script', 'style'}:
        return
    for node in soup.children:
        if isinstance(node, bs4.NavigableString):
            new_val, replaces_count = change_rex.subn(r'\1\2™\3', str(node))
            if replaces_count > 0:
                node.replace_with(bs4.NavigableString(new_val))
        else:
            do_replaces(node)
    return


async def handler(request):
    url = urljoin(BASE_URL, request.url.path_qs[1:])
    logger.debug('{}\t{}'.format(request.method, url))
    headers1 = request.headers
    if 'Host' in headers1:
        del headers1['Host']
    async with aiohttp.ClientSession() as session:
        async with session.request(
                request.method, url,
                data=request.content,
                encoding=request.charset,
                headers=request.headers,
                verify_ssl=False
        ) as resp:
            headers2 = resp.headers.copy()
            if resp.headers.get('content-type', '').lower().startswith('text/html'):
                payload = await resp.text()
                # payload = change_rex.sub(r'\1\2™\3', payload)
                payload = payload.replace('https://habrahabr.ru/', '/')
                soup = bs4.BeautifulSoup(payload, 'html.parser')
                do_replaces(soup)
                payload = str(soup).replace('&amp;plus;', '&plus;')
            else:
                payload = await resp.read()

            status = resp.status
            session.close()

            if 'Transfer-Encoding' in headers2:
                del headers2['Transfer-Encoding']
            if 'Content-Encoding' in headers2:
                del headers2['Content-Encoding']
            return web.Response(
                body=payload,
                status=status,
                headers=headers2
            )


def main(loop):
    server = web.Server(handler, loop=loop)
    logger.info("======= Serving on http://127.0.0.1:8232/ ======")
    srv = loop.run_until_complete(loop.create_server(server, "0.0.0.0", 8232))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("interrupted, exiting")
    finally:
        srv.close()
        loop.run_until_complete(srv.wait_closed())
        loop.run_until_complete(server.shutdown(60.0))


logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

loop = asyncio.get_event_loop()
if __name__ == '__main__':
    main(loop)
loop.close()
