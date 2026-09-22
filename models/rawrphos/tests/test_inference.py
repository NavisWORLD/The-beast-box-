import pytest
import torch
from fastapi.testclient import TestClient

@pytest.fixture
def trained(tmp_path):
    from rawrphos.architecture.model import RawrphosConfig,RawrphosLM
    from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
    from rawrphos.training.checkpoint import save_checkpoint,rng_state
    t=RawrphosTokenizer.train(['The little cat sat on a warm mat.']*10,300)
    torch.manual_seed(8); m=RawrphosLM(RawrphosConfig(vocab_size=t.vocab_size,d_model=32,n_heads=4,n_layers=2,max_seq_len=512))
    ids=torch.tensor([t.encode('The little cat sat on a warm mat.')]); opt=torch.optim.AdamW(m.parameters(),lr=.001)
    loss=m(ids[:,:-1],targets=ids[:,1:])['loss']; loss.backward(); opt.step()
    p=tmp_path/'trained'; save_checkpoint(p,m,t,{'training_steps':1,'training_tokens':ids.shape[1]-1,'training_seq_len':ids.shape[1]-1,
        'release_status':'test-fixture-trained','hardware':{'device':'cpu'}},{'rng':rng_state()})
    return p

def test_authenticated_real_generation_and_rejection(trained):
    from rawrphos.inference.server import create_app
    client=TestClient(create_app(trained,'test-key-'+'x'*32,max_new_tokens=32))
    assert client.get('/health').status_code==200
    assert client.get('/model/info').status_code==401
    auth={'Authorization':'Bearer '+'test-key-'+'x'*32}
    info=client.get('/model/info',headers=auth).json()
    assert info['model_id']=='rawrphos-native' and len(info['checkpoint_sha256'])==64
    request={'model':'rawrphos-native','prompt':'The cat','max_tokens':8,'temperature':0}
    response=client.post('/v1/completions',headers=auth,json=request)
    assert response.status_code==200,response.text
    assert response.json()['usage']['completion_tokens']>0
    assert response.json()['checkpoint_sha256']==info['checkpoint_sha256']
    assert client.post('/v1/completions',headers=auth,json=dict(request,model='other')).status_code==400
    assert client.post('/v1/completions',headers=auth,json=dict(request,max_tokens=10000)).status_code==400
    assert client.post('/v1/completions',headers=auth,json=dict(request,stream=True)).status_code==200
    assert client.post('/v1/completions',json=request).status_code==401

def test_real_provider_uses_existing_durable_runtime(trained,tmp_path):
    from rawrphos.adapters.beastbox_provider import NativeProvider
    from beastbox.durable import DurableRuntime
    p=NativeProvider(trained,max_new_tokens=4)
    runtime=DurableRuntime(tmp_path/'memory',p)
    out=runtime.respond('The cat is named Moss.')
    assert out['response']==p.last_response
    checkpoint=runtime.inspect()['checkpoint_sha256']; runtime.close()
    restarted=DurableRuntime(tmp_path/'memory',p)
    assert restarted.inspect()['checkpoint_sha256']==checkpoint
    assert restarted.memory.search('Moss')
    restarted.close()
