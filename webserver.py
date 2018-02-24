import aiohttp
import json
import os
import asyncio
from bs4 import BeautifulSoup
from sanic import Sanic, response
from motor.motor_asyncio import AsyncIOMotorClient

app = Sanic(__name__)
app.mongo = AsyncIOMotorClient(os.environ.get('mongo'))
app.session = None
app.cr_constants = None

async def update_constants():
    '''Updates constants for /cr/constants'''
    while not app.session.closed:
        output = {'info':'This data is updated hourly.', 'source':'https://cr-api.github.io/cr-api-data'}
        async with app.session.get('https://www.github.com/cr-api/cr-api-data/tree/master/json') as resp:
            soup = BeautifulSoup(await resp.text(), 'html.parser')

        urls = [
            i.find('td', attrs={'class':'content'})\
                .find('span')\
                .find('a')['title']
            for i in
            soup.find('div', attrs={'class':'application-main '})\
                .find('div', attrs={'class':'', 'itemtype':'http://schema.org/SoftwareSourceCode'})\
                .find('div')\
                .find('div', attrs={'class':'container new-discussion-timeline experiment-repo-nav '})\
                .find('div', attrs={'class':'repository-content '})\
                .find('div', attrs={'class':'file-wrap'})\
                .find('table', attrs={'class':'files js-navigation-container js-active-navigation-container'})\
                .find('tbody')\
                .find_all('tr', attrs={'class':'js-navigation-item'})
        ]

        for i in urls:
            async with app.session.get('https://cr-api.github.io/cr-api-data/json/' + i) as z:
                output[i.replace('.json', '')] = await z.json()

        app.constants = output

        await asyncio.sleep(3600)

@app.listener('before_server_start')
async def create_session(app, loop):
    '''Creates an aiohttp.ClientSession upon app connect'''
    app.session = aiohttp.ClientSession(loop=loop)
    app.loop.create_task(update_constants())

@app.listener('after_server_stop')
async def close_session(app, loop):
    '''Closes session upon app disconnect'''
    await app.session.close()

@app.route('/')
async def startup(request):
    '''A / page, much like a ping'''
    return response.json({'hello':'world'})

@app.route('/cr/constants')
async def cr_constants(request):
    '''Retrieve constants from cr-api-data'''
    return response.json(app.constants)

@app.route('/debug', methods=['GET', 'PUT', 'POST', 'GET', 'DELETE', 'PATCH'])
async def debug(request):
    '''Returns and prints to stdout a JSON object about the request'''
    debug_json = {
        'method':request.method,
        'url':request.url,
        'json':request.json,
        'params':request.raw_args,
        'form':request.form,
        'body':request.body,
        'headers':request.headers,
        'ip':request.ip,
        'port':request.port
    }
    print(debug_json)
    return response.json(debug_json)

# @app.route('/bots', methods=['POST'])
# async def post_bot(request):
#     '''For DBL support'''
#     if request.headers.get('user_agent') != 'DBL':
#         return response.json({'message':"You aren't DBL!"}, status=400)

#     bot_id = request.json.get('bot')
#     collection = app.mongo.bots.bot_info
#     bot_info = await collection.find_one({'bot_id':bot_id})

#     if bot_info is None:
#         return response.json({'message':'Unregistered Bot'}, status=404)

#     if request.json.get('type') == 'upvote':
#         await collection.find_one_and_update({'$set':{request.json.get('user'):True}})
#     else:
#         await collection.find_one_and_delete({request.json.get('user'):True})

app.run(host="0.0.0.0", port=os.getenv('PORT'))