import asyncio
import json
import os
import random
import datetime

import aiohttp
from sanic import Sanic, response

try:
    with open('config.json') as f:
        os.environ = json.load(f)
        os.environ['data']
except (FileNotFoundError, KeyError):
    pass

app = Sanic(__name__)
app.session = None
app.voted = []
app.constants = {'clashroyale': {}, 'brawlstars': {}}
app.storage = {
    'help': [
        'This system is implemented for endpoints that is system intensive',
        'You can use this by going to https://fourjr-webserver.herokuapp.com/status/<status_number>',
        'Endpoints like /cr/cr-arena-meta will use this system',
        'Typically there will be a link to this endpoint (/status) so you will not need to memorise any of this'
    ]
}


async def update_constants(mode, once=False):
    '''Updates constants for /*/constants'''
    # print(__import__('json').dumps(__import__('os').listdir('../bs-data/json'), indent=4))
    if mode == 'brawlstars':
        url = [
            'fourjr',
            'bs-data',
            [
                "animations.json",
                "billing_packages.json",
                "client_globals.json",
                "credits.json",
                "effects.json",
                "faces.json",
                "health_bars.json",
                "hints.json",
                "music.json",
                "particle_emitters.json",
                "sounds.json",
                "tutorial.json",
                "cards.json",
                "characters.json",
                "globals.json",
                "items.json",
                "locales.json",
                "locations.json",
                "map_blocks.json",
                "maps.json",
                "pins.json",
                "player_thumbnails.json",
                "projectiles.json",
                "regions.json",
                "resources.json",
                "skills.json",
                "skins.json",
                "tiles.json",
                "alliance_badges.json",
                "alliance_roles.json",
                "area_effects.json",
                "bosses.json",
                "campaign.json",
                "skinsrarity.json",
                "texts.json",
                "player_badges.json"
            ]
        ]
    elif mode == 'clashroyale':
        url = [
            'fourjr',
            'cr-data',
            [
                "achievements.json",
                "alliance_badges.json",
                "alliance_roles.json",
                "area_effect_objects.json",
                "arenas.json",
                "buildings.json",
                "characters.json",
                "character_buffs.json",
                "chest_order.json",
                "clan_leagues.json",
                "clan_war_globals.json",
                "configuration_definitions.json",
                "content_bundle_definitions.json",
                "content_tests.json",
                "decos.json",
                "draft_deck.json",
                "event_categories.json",
                "event_category_definitions.json",
                "event_category_enums.json",
                "event_category_object_definitions.json",
                "event_targeting_definitions.json",
                "exp_levels.json",
                "fortune.json",
                "game_modes.json",
                "globals.json",
                "heroes.json",
                "locations.json",
                "npcs.json",
                "predefined_decks.json",
                "projectiles.json",
                "pve_gamemodes.json",
                "quest_main_rewards.json",
                "quest_order.json",
                "rarities.json",
                "regions.json",
                "resources.json",
                "resource_packs.json",
                "shop.json",
                "shop_chests.json",
                "shop_cycle.json",
                "skins.json",
                "skin_sets.json",
                "spells_buildings.json",
                "spells_characters.json",
                "spells_heroes.json",
                "spells_hero_abilities.json",
                "spells_other.json",
                "spell_sets.json",
                "survival_modes.json",
                "taunts.json",
                "tournament_tiers.json",
                "treasure_chests.json",
                "tutorials_home.json",
                "tutorials_npc.json",
                "tutorial_chest_order.json",
                "tve_gamemodes.json",
                "quests.attack.json",
                "quests.cast.json",
                "quests.collect.json",
                "quests.daily.json",
                "quests.donate.json",
                "quests.play.json",
                "quests.pve.json",
                "animations.json",
                "background_decos.json",
                "billing_packages.json",
                "client_globals.json",
                "credits.json",
                "effects.json",
                "event_output.json",
                "health_bars.json",
                "helpshift.json",
                "hints.json",
                "locales.json",
                "music.json",
                "news.json",
                "particle_emitters.json",
                "sounds.json",
                "sorted_regions.CNT_regions.json",
                "sorted_regions.CN_regions.json",
                "sorted_regions.JP_regions.json",
                "sorted_regions.KR_regions.json",
                "texts.json"
            ]
        ]
    else:
        raise NotImplementedError('Mode not implemented: ' + mode)

    if app.session:
        closed = app.session.closed
    else:
        closed = False

    while not closed:
        output = {
            'info': 'This data is updated hourly.',
            'source': f'https://www.github.com/{url[0]}/{url[1]}'
        }

        for i in url[2]:
            async with app.session.get(f'https://raw.githubusercontent.com/{url[0]}/{url[1]}/master/json/{i}') as z:
                output[i.replace('.json', '')] = await z.json(content_type='text/plain')

        app.constants[mode] = output

        if once:
            return
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


async def set_session():
    app.session = aiohttp.ClientSession(loop=asyncio.get_event_loop())


@app.listener('before_server_start')
async def create_session(app, loop):
    '''Creates an aiohttp.ClientSession upon app connect'''
    await app.session.close()
    app.session = aiohttp.ClientSession(loop=asyncio.get_event_loop())
    loop.create_task(update_constants('clashroyale'))
    loop.create_task(update_constants('brawlstars'))


@app.listener('after_server_stop')
async def close_session(app, loop):
    '''Closes session upon app disconnect'''
    await app.session.close()


@app.route('/')
async def startup(request):
    '''A / page, much like a ping'''
    return response.json({'hello': 'world'})


@app.route('/status')
async def show_help_status(requst):
    return response.json({'error': False, 'status': 'help', 'data': app.storage['help']})


@app.route('/status/<status>')
async def get_status(request, status):
    '''Makes use of app.storage to get status'''
    try:
        status = int(status)
        entry = app.storage[status]
    except (ValueError, KeyError):
        return response.json({'error': True, 'status': status, 'message': 'Invalid status'})

    return response.json({'error': False, 'status': status, 'data': entry})


@app.route('/cr/constants')
async def cr_constants(request):
    '''Retrieve constants from cr-data'''
    return response.json(app.constants['clashroyale'])


@app.route('/bs/constants')
async def bs_constants(request):
    '''Retrieve constants from bs-data'''
    return response.json(app.constants['brawlstars'])


@app.route('/debug', methods=['GET', 'PUT', 'POST', 'GET', 'DELETE', 'PATCH'])
async def debug(request):
    '''Returns and prints to stdout a JSON object about the request'''
    debug_json = {
        'method': request.method,
        'url': request.url,
        'json': request.json,
        'params': request.raw_args,
        'form': request.form,
        'body': request.body,
        'headers': request.headers,
        'ip': request.ip,
        'port': request.port
    }
    print(debug_json)
    return response.json(debug_json)


@app.route('/statsy/dbl', methods=['POST'])
async def statsy_dbl(request):
    if request.headers.get('Authorization') == os.getenv('statsydblauth'):
        if request.json.get('user') not in app.voted:
            app.voted.append(request.json.get('user'))
            async with app.session.post(
                os.getenv('statsydblhook'), json={'content': request.json.get('user')}
            ) as resp:
                return response.json({'status': resp.status}, status=resp.status)
        else:
            return response.json({'status': 'you already did this'}, status=400)
    else:
        return response.json({'message': 'stop trying'}, status=400)


@app.route('/statsy/tournament', methods=['POST'])
async def statsy_tournament(request):
    if request.headers.get('Authorization') == os.getenv('statsytournamentauth'):
        async with app.session.post(
            os.getenv('statsytournamenthook'), json={'content': f"{request.json['tag']} {json.dumps(request.json['filters'])}"}
        ) as resp:
            return response.json({'status': resp.status}, status=resp.status)
    else:
        return response.json({'message': 'stop trying'}, status=400)


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


@app.route('/statuscode', methods=['GET', 'PUT', 'POST', 'GET', 'DELETE', 'PATCH'])
async def status(request):
    return response.text(None, status=int(request.raw_args['status']))


@app.route('/zanata', methods=['POST'])
async def zanata(request):
    if request.json['type'] == 'DocumentMilestoneEvent':
        embed = {
            'title': request.json['milestone'],
            'type': 'rich',
            'description': 'Language: ' + request.json['locale'] + '\n' + 'Version: ' + request.json['version'],
            'color': 0x22ee5b
        }
    elif request.json['type'] == 'DocumentStatsEvent':
        embed = {
            'title': f'{request.json["username"]} updated {request.json["locale"]}',
            'type': 'rich',
            'description': 'Version: ' + request.json['version'],
            'color': 0xd990e9
        }
    elif request.json['type'] == 'SourceDocumentChangedEvent':
        embed = {
            'title': 'Documents added',
            'type': 'rich',
            'description': 'Version: ' + request.json['version'],
            'color': 0x56beee
        }
    else:
        return response.json({'status': 'invalid type'}, status=400)
    await app.session.post(os.getenv('zanatahook'), json=embed)
    return response.json(None, status=204)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_session())
    loop.run_until_complete(update_constants('brawlstars', once=True))
    loop.run_until_complete(update_constants('clashroyale', once=True))
    app.run(host="0.0.0.0", port=os.getenv('PORT'))
