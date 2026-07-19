import asyncio
from g4f.client import AsyncClient
import g4f.Provider as P

async def test_providers():
    client = AsyncClient()
    working = []
    
    providers = []
    for name in dir(P):
        if not name.startswith('_'):
            prov = getattr(P, name)
            if hasattr(prov, 'create_async_generator'):
                providers.append(prov)

    for p in providers[:15]: # test first 15
        try:
            r = await asyncio.wait_for(
                client.chat.completions.create(
                    model='gpt-4o-mini', 
                    messages=[{'role':'user','content':'hi'}], 
                    provider=p
                ), 
                timeout=8
            )
            print(f'[+] {p.__name__} works: {r.choices[0].message.content[:30]}')
            working.append(p.__name__)
        except Exception as e:
            print(f'[-] {p.__name__} failed: {type(e).__name__}')
            
    print('Working:', working)

asyncio.run(test_providers())
