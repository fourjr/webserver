import aiohttp
import json
import os
from sanic import Sanic, response
from motor.motor_asyncio import AsyncIOMotorClient

app = Sanic(__name__)
app.mongo = AsyncIOMotorClient(os.environ.get('mongo'))
app.session = None
.
@app.listener('before_server_start')
async def create_session(app, loop):
    '''Creates an aiohttp.ClientSession upon app connect'''
    app.session = aiohttp.ClientSession(loop=loop)

@app.listener('after_server_stop')
async def close_session(app, loop):
    '''Closes session upon app disconnect'''
    await app.session.close()

@app.route('/')
async def startup(request):
    '''A / page, much like a ping'''
    return response.json({'hello':'hell'})

@app.route('/cr/constants')
async def cr_constants(request):
    '''Retrieve constants from cr-api-data'''
    output = {'source':'https://cr-api.github.io/cr-api-data'}
    urls = [
        'alliance_badges',
        'arenas',
        'cards',
        'cards_stats',
        'challenges',
        'chest_order',
        'clan_chest',
        'game_modes',
        'rarities',
        'regions',
        'tournaments',
        'treasure_chests'
    ]

    for i in urls:
        async with app.session.get('https://cr-api.github.io/cr-api-data/json/' + i + '.json') as z:
            try:
                output[i] = await z.json()
            except aiohttp.client_exceptions.ContentTypeError:
                pass

    return response.json(output)

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