import asyncio
import httpx
import pytest
from app.source import ElexonClient

@pytest.mark.parametrize('verified',[True,False])
def test_schema_gate(verified):
    params=[{'name':'publishDateTimeFrom'},{'name':'publishDateTimeTo'}] if verified else [{'name':'from'}]
    spec={'paths':{f'/datasets/{ds}/stream':{'get':{'parameters':params}} for ds in ['FUELHH','WINDFOR']}}
    async def run():
        c=ElexonClient(httpx.MockTransport(lambda r:httpx.Response(200,json=spec)))
        try:
            if verified:assert await c.verify_schema()==spec
            else:
                with pytest.raises(ValueError,match='Could not verify'):await c.verify_schema()
        finally:await c.close()
    asyncio.run(run())
