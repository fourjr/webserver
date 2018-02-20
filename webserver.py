import aiohttp
import json
import os
from sanic import Sanic, response
from motor.motor_asyncio import AsyncIOMotorClient

app = Sanic(__name__)
app.mongo = AsyncIOMotorClient(os.environ.get('mongo'))

@app.listener('before_server_start')
async def create_session(app, loop):
    app.session = aiohttp.ClientSession(loop=loop)

@app.listener('after_server_stop')
async def close_session(app, loop):
    app.session.close()

@app.route('/')
async def startup(request):
    return response.text('Check this out here!')

# @app.route('/cr-api-data', methods=['PUT'])
# async def crapidata():
#     await asyncio.sleep(240)
#     urls = ['alliance_badges', 'arenas', 'cards', 'cards_stats', 'chest_order', 'clan_chest', 'game_modes', 'rarities', 'regions', 'tournaments', 'treasure_chests'] 
#     fmt = {}
#     fails = []
#     for i in urls:
#         async with app.session.get('https://cr-api.github.io/cr-api-data/json/' + i + '.json') as z:
#             try:
#                 fmt[i] = (await z.json(content_type='text/plain'))
#             except:
#                 fails.append(i)

#     with open('backup/clashroyale/constants.json', 'w+') as fp:
#         json.dump(obj=fmt, fp=fp, indent=4)
#     return response.json({'complete': True, 'fails': fails, 'JSON file':})

@app.route('/debug', methods=['PUT', 'POST', 'GET', 'DELETE', 'PATCH'])
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

@app.route('/bots', methods=['POST'])
async def post_bot(request):
    '''For DBL support'''
    if request.headers.get('user_agent') != 'DBL':
        return response.json({'message':"You aren't DBL!"}, status=400)

    bot_id = request.json.get('bot')
    collection = app.mongo.bots.bot_info
    bot_info = await collection.find_one({'bot_id':bot_id})

    if bot_info is None:
        return response.json({'message':'Unregistered Bot'}, status=404)

    if request.json.get('type') == 'upvote':
        await collection.find_one_and_update({'$set':{request.json.get('user'):True}})
    else:
        await collection.find_one_and_delete({request.json.get('user'):True})


app.run(host="0.0.0.0", port=os.getenv('PORT'))