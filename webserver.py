import asyncio
import json
import os
import copy
import time
import random
import datetime
from collections import Counter

import aiohttp
import clashroyale
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient
from sanic import Sanic, response

try:
    with open('config.json') as f:
        os.environ = json.load(f)
        os.environ['data']
except (FileNotFoundError, KeyError):
    pass

app = Sanic(__name__)
app.mongo = None
app.cr_meta_mongo = None
app.cr_client = None
app.session = None
app.voted = []
app.tags = {}
app.constants = {'clashroyale':{}, 'brawlstars':{}}
app.storage = {
    'help': [
        'This system is implemented for endpoints that is system intensive',
        'You can use this by going to https://fourjr-webserver.herokuapp.com/status/<status_number>',
        'Endpoints like /cr/cr-arena-meta will use this system',
        'Typically there will be a link to this endpoint (/status) so you will not need to memorise any of this'
    ]
}

async def update_constants(mode):
    '''Updates constants for /*/constants'''
    if mode == 'brawlstars':
        url = [
            'fourjr',
            'bs-data',
            [
                'alliance_badges.json',
                'alliance_roles.json',
                'area_effects.json',
                'bosses.json',
                'campaign.json',
                'cards.json',
                'characters.json',
                'globals.json',
                'items.json',
                'locations.json',
                'maps.json',
                'pins.json',
                'player_thumbnails.json',
                'projectiles.json',
                'regions.json',
                'resources.json',
                'skills.json',
                'skins.json',
                'tiles.json',
            ]
        ]
    elif mode == 'clashroyale':
        url = [
            'cr-api',
            'cr-api-data',
            [
                'alliance_badges.json',
                'arenas.json',
                'cards.json',
                'cards_stats.json',
                'challenges.json',
                'chest_order.json',
                'clan_chest.json',
                'game_modes.json',
                'rarities.json',
                'regions.json',
                'tournaments.json',
                'treasure_chests.json',
            ]
        ]
    else:
        raise NotImplementedError('Mode not implemented: ' + mode)

    while not app.session.closed:
        output = {
            'info':'This data is updated hourly.',
            'source':f'https://www.github.com/{url[0]}/{url[1]}'
        }

        for i in url[2]:
            async with app.session.get(f'https://raw.githubusercontent.com/{url[0]}/{url[1]}/master/json/{i}') as z:
                output[i.replace('.json', '')] = await z.json(content_type='text/plain')

        app.constants[mode] = output

        await asyncio.sleep(3600)

async def update_tags(once=False):
    while not app.session.closed:
        app.tags = await app.cr_meta_mongo.config.find({'name':'tags'}).to_list(None)
        print('Server tags reloaded')
        if once:
            break
        await asyncio.sleep(3600)

def get_current_time(utc=True):
    if utc:
        current = datetime.datetime.utcnow()
    else:
        current = datetime.datetime.now()
    return current.strftime('%Y-%m-%dT%H:%M:%S/%f')

def get_random_status():
    status = 'help'
    while status in app.storage:
        status = random.randint(1, 99999)
    return status

def authentication(func):
    def decorator(request, **kwargs):
        if request.headers.get('Authorization') != 'Bearer ' + os.environ.get('auth'):
            pass#return response.json({'error':True, 'message':'Unauthorised'}, status=401)
    return decorator

@app.listener('before_server_start')
async def create_session(app, loop):
    '''Creates an aiohttp.ClientSession upon app connect'''
    app.session = aiohttp.ClientSession(loop=loop)

    app.cr_client = clashroyale.Client(
        os.environ.get('clashroyale'),
        is_async=True,
        timeout=10,
        session=app.session
    )

    app.mongo = AsyncIOMotorClient(os.environ.get('mongo'), io_loop=loop)
    app.cr_meta_mongo = AsyncIOMotorClient(os.environ.get('mongo2'), io_loop=loop).cr_arena_meta
    loop.create_task(update_constants('clashroyale'))
    loop.create_task(update_constants('brawlstars'))
    loop.create_task(update_tags())

@app.listener('after_server_stop')
async def close_session(app, loop):
    '''Closes session upon app disconnect'''
    await app.session.close()

@app.route('/')
async def startup(request):
    '''A / page, much like a ping'''
    return response.json({'hello':'world'})

@app.route('/status')
async def show_help_status(requst):
    return response.json({'error':False, 'status':'help', 'data':app.storage['help']})

@app.route('/status/<status>')
async def get_status(request, status):
    '''Makes use of app.storage to get status'''
    try:
        status = int(status)
        entry = app.storage[status]
    except (ValueError, KeyError):
        return response.json({'error':True, 'status':status, 'message':'Invalid status'})

    return response.json({'error':False, 'status':status, 'data':entry})


@app.route('/cr/constants')
async def cr_constants(request):
    '''Retrieve constants from cr-api-data'''
    return response.json(app.constants['clashroyale'])

@app.route('/cr/cr-arena-meta')
async def modify_tag(request):
    '''Modifes tag in the cr-arena-meta database'''
    params = request.raw_args
    if 'type' not in params and 'tag' not in params:
        return response.json({'error':True, 'message':'`type` and `tag` are to be included in querystrings.'}, status=400)

    # CHECK TAG
    params['tag'] = params['tag'].strip('#').upper().replace('O', '0')
    if any(i not in 'PYLQGRJCUV0289' for i in params['tag']):
        return response.json({'error':True, 'message':'Invalid tag'})

    if len(app.tags) == 0:
        return response.json({'error':True, 'message':'Server not ready yet. Give us a minute.'}, status=503)

    collection = app.cr_meta_mongo.config

    if params['type'] == 'player':
        for i in app.tags:
            if params['tag'] in i['data']:
                return response.json({'error':False, 'message':'Tag already exists'})

        if len(app.tags[-1]['data']) != 500000:
            app.tags[-1]['data'].append(params['tag'])
            await collection.find_one_and_replace({'id':app.tags[-1]['id']}, app.tags[-1])
        else:
            await collection.insert_one(
                {
                    'name':'tags',
                    'id':app.tags[-1]['id']+1,
                    'data':[
                        params['tag']
                    ]
                }
            )

        return response.json({'error':False, 'message':'Added tag.'})

    elif params['type'] == 'clan':
        try:
            clan = await app.cr_client.get_clan(params['tag'], keys='members')
        except clashroyale.RequestError:
            return response.json({'error':True, 'message':'RoyaleAPI is currently down.'}, status=504)

        input_tags = [i.tag for i in clan.members]

        for i in app.tags:
            input_tags = list((Counter(input_tags) - Counter(i['data'])).elements())

        a = copy.copy(app.tags[-1])
        if len(app.tags[-1]['data']) < 500000 - len(input_tags):
            app.tags[-1]['data'] += input_tags
            await collection.find_one_and_replace({'id':app.tags[-1]['id']}, app.tags[-1])

        else:
            await collection.insert_one(
                {
                    'name':'tags',
                    'id':app.tags[-1]['id'] + 1,
                    'data':input_tags
                }
            )

        return response.json({'error':False, 'message':f'Added {len(input_tags)} tags.'})

async def cr_clear_duplicates(status):
    try:
        collection = app.cr_meta_mongo.config
        async def add_to_db(index, i):
            await collection.insert_one({'name':'tags', 'id':index, 'data':data[i:i+500000]})

        start_time = time.time()

        # await update_tags(once=True)
        app.storage[status][get_current_time()] = 'Tags fully updated locally'
        data = []
        for i in app.tags:
            data += i['data']
        print(len(app.tags))
        initial_data = len(data)
        print(data[0])
        print(initial_data)
        data = list(set(data))
        print(len(data))
        app.storage[status][get_current_time()] = 'Duplicates cleared locally, database to pushing begin'

        await collection.delete_many({'name':'tags'})
        for index, i in enumerate(range(0, len(data), 500000)):
            app.loop.create_task(add_to_db(index, i))
        print(index)

        app.storage[status][get_current_time()] = 'Dupe clearing completed {} tags removed.'.format(str(initial_data - len(data)))
        await asyncio.sleep(0.3)
        app.storage[status][get_current_time()] = f'Operation took a total of {time.time() - start_time}s'
    except Exception as e:
        app.storage[status][get_current_time()] = 'ERROR! Operation terminated'
        app.storage[status]['error'] = e

@authentication
@app.route('/cr/duplicates')
async def cr_duplicates(request):
    '''Clear duplicates'''
    status = get_random_status()

    app.storage[status] = {
        get_current_time(): 'Clearing of duplicates begin'
    }

    app.loop.create_task(cr_clear_duplicates(status))

    return response.json(
        {
            'error': False,
            'message': 'Clearing, check your status with the following url',
            'status': f'http://{request.headers["host"]}/status/{status}'
        }
    )

@app.route('/bs/constants')
async def bs_constants(request):
    '''Retrieve constants from bs-data'''
    return response.json(app.constants['brawlstars'])

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

@app.route('/statsy', methods=['POST'])
async def statsy_dbl(request):
    if request.headers.get('Authorization') == os.getenv('statsyauth'):
        if request.json.get('user') not in app.voted:
            app.voted.append(request.json.get('user'))
            async with app.session.post(os.getenv('statsyhook'), json={'content': request.json.get('user')}) as resp:
                return response.json({'status': resp.status}, status=resp.status)
        else:
            return response.json({'status': 'you already did this'}, status=400)
    else:
        return response.json({'message': 'stop trying'}, statius=400)

@app.route('/redirect')
async def redirect(request):
    return response.redirect(request.raw_args['url'])

@app.route('/postman', methods=['GET', 'PUT', 'POST', 'GET', 'DELETE', 'PATCH'])
async def postman(request):
    try:
        headers = {h.split(':')[0].strip(): h.split(':')[1].strip() for h in request.raw_args['headers'].split('|')}
    except KeyError:
       headers = {}

    async with app.session.request(request.method, request.raw_args['url'], headers=headers) as resp:
        try:
            return response.json(await resp.json())
        except aiohttp.client_exceptions.ContentTypeError:
            try:
                return response.text(await resp.text())
            except UnicodeDecodeError:
                return response.raw(await resp.read())
            

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
