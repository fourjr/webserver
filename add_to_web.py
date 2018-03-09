import os
import json
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    with open('config.json') as f:
        os.environ = json.load(f)
    db = AsyncIOMotorClient(os.environ.get('mongo2')).cr_arena_meta

    collection = db.config

    existing_tags = await collection.find({'name':'tags'}).to_list(None)

    smallest = existing_tags[-1]['id']

    tags = []

    with open('tags.json') as f:
        for i in f.read().splitlines():
            tags.append(json.loads(i))

    backup = open('backup', 'w')

    for n, tag in enumerate(tags):
        error = False

        if n % 100000 == 0:
            print('BACKUP')
            json.dump(existing_tags, backup)

        for i in existing_tags:
            if i['name'] != 'tags': continue
            if tag['_id'] in i['data']:
                print(f'{tag["_id"]} exists')
                error = True
                break
        if error:
            continue

        print(f'{tag["_id"]} adding')

        if len(existing_tags[-1]['data']) != 500000:
            existing_tags[-1]['data'].append(tag["_id"])
        else:
            existing_tags.append(
                {
                    'name':'tags',
                    'id':existing_tags[-1]['id']+1,
                    'data':[
                        tag['_id']
                    ]
                }
            )

    print('RIP')

    await collection.delete_one({'id':smallest})
    await collection.insert_many(existing_tags[i] for i in range(smallest, len(existing_tags) + 1))

    backup.close()

asyncio.get_event_loop().run_until_complete(main())
