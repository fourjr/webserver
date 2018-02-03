import aiohttp
import json
import os
from sanic import Sanic, response

app = Sanic(__name__)

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

@app.route('/debug', methods=['PUT', 'POST', 'GET', 'DELETE'])
async def debug(request):
    debug_json = {
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

app.run(host="0.0.0.0", port=os.getenv('PORT'))