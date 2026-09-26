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


def test_pinned_offline_cli_info_and_generation(trained, capsys):
    from rawrphos.inference.cli import main
    from rawrphos.training.checkpoint import load_checkpoint
    sha = load_checkpoint(trained, load_training_state=False)["metadata"]["checkpoint_sha256"]
    main(["--checkpoint", str(trained), "--expected-sha256", sha, "info"])
    info = __import__("json").loads(capsys.readouterr().out)
    assert info["model_id"] == "rawrphos-native"
    assert info["checkpoint_sha256"] == sha
    main(["--checkpoint", str(trained), "--expected-sha256", sha,
          "prompt", "The cat", "--max-tokens", "4", "--temperature", "0"])
    printed = capsys.readouterr()
    metrics = __import__("json").loads(printed.err)
    assert 1 <= metrics["generated_tokens"] <= 4
    assert metrics["prefill_and_first_token_seconds"] >= 0


def test_benchmark_repetition_and_invalid_budget():
    from rawrphos.evaluation.benchmark import repetition_fraction, evaluate
    assert repetition_fraction("a a a") == 1.0
    assert repetition_fraction("a b c") == 0.0
    with pytest.raises(ValueError, match="budget"):
        evaluate("/does-not-exist", max_tokens=65)


def test_actual_cns_control_changes_frozen_model_logits_without_zero_control_regression(trained):
    from rawrphos.inference.server import create_app
    app=create_app(trained,'test-key-'+'x'*32,max_new_tokens=32)
    client=TestClient(app)
    headers={'Authorization':'Bearer '+'test-key-'+'x'*32}
    info=client.get('/model/info',headers=headers).json()
    request={'model':'rawrphos-native','prompt':'The cat','max_tokens':8,'seed':67,
             'control_vector':[0.75 if i % 2 else -0.5 for i in range(12)]}
    assert client.post('/v1/condition-probe',json=request).status_code==401
    response=client.post('/v1/condition-probe',headers=headers,json=request)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['checkpoint_sha256']==info['checkpoint_sha256']
    assert result['training_steps']==1
    assert result['model_weights_changed'] is False
    assert result['performance_gain_proven'] is False
    assert result['logit_l2']['zero_vs_reference'] < 1e-6
    assert result['logit_l2']['conditioned_vs_reference'] > 1e-9
    assert result['logit_l2']['conditioned_vs_rotated'] > 1e-9
    assert len(result['gate_by_layer'])==2
    assert isinstance(result['response_reference'],str)
    assert isinstance(result['response_conditioned'],str)
    # Repeat the same fixed seed to guarantee reproducible responses.
    second=client.post('/v1/condition-probe',headers=headers,json=request)
    assert second.status_code==200
    assert second.json()['response_conditioned']==result['response_conditioned']
    assert second.json()['response_reference']==result['response_reference']
    assert client.post('/v1/condition-probe',headers=headers,
                       json=dict(request,control_vector=[False]*12)).status_code==400
    assert client.post('/v1/condition-probe',headers=headers,
                       json=dict(request,control_vector=[2.0]*12)).status_code==400
    assert client.post('/v1/condition-probe',headers=headers,
                       json=dict(request,unexpected='tools')).status_code==400
    assert client.get('/model/info',headers=headers).json()['checkpoint_sha256']==info['checkpoint_sha256']


def test_multi_arm_condition_probe_v2_reports_full_native_telemetry_and_cache_parity(trained):
    from rawrphos.inference.server import create_app
    app=create_app(trained,'test-key-'+'x'*32,max_new_tokens=32)
    client=TestClient(app)
    headers={'Authorization':'Bearer '+'test-key-'+'x'*32}
    control=[0.7,-0.2,0.5,-0.4,0.3,-0.6,0.1,-0.8,0.9,-0.1,0.25,-0.35]
    classical=[control[(i*5+3)%12]*(1 if i%2==0 else -1) for i in range(12)]
    arms={
        'reference':{'control_vector':None,'attention_mode':'dyn12'},
        'zero':{'control_vector':[0.0]*12,'attention_mode':'dyn12'},
        'conditioned':{'control_vector':control,'attention_mode':'dyn12'},
        'classical_matched':{'control_vector':classical,'attention_mode':'dyn12'},
        'zero_gate':{'control_vector':control,'attention_mode':'zero_gate'},
        'frozen_state':{'control_vector':control,'attention_mode':'frozen_state'},
        'shuffled_state':{'control_vector':control,'attention_mode':'shuffled_state'},
    }
    request={'model':'rawrphos-native','prompt':'The cat','arms':arms,'max_tokens':6,'seed':67}
    assert client.post('/v1/condition-probe-v2',json=request).status_code==401
    response=client.post('/v1/condition-probe-v2',headers=headers,json=request)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['schema']=='rawrphos-condition-probe-v2'
    assert result['checkpoint_sha256']==client.get('/model/info',headers=headers).json()['checkpoint_sha256']
    assert result['model_weights_changed'] is False
    assert result['persistent_memory_updated'] is False
    assert result['performance_gain_proven'] is False
    assert result['logit_l2_vs_reference']['zero'] < 1e-6
    assert result['logit_l2_vs_reference']['conditioned'] > 1e-9
    assert result['arms']['conditioned']['control_vector']==control
    assert len(result['arms']['conditioned']['control_sha256'])==64
    assert len(result['arms']['conditioned']['telemetry_by_layer'])==2
    for layer in result['arms']['conditioned']['telemetry_by_layer']:
        assert set(layer)=={'gate','sigma','state_norm','omega_mean'}
        assert all(isinstance(value,float) for value in layer.values())
        assert layer['sigma'] > 0
    assert result['conditioned_cache_parity'] is True
    assert result['conditioned_cache_token_parity'] is True
    assert result['generation_metrics']['conditioned_cache']['token_sequence_sha256']==result['generation_metrics']['conditioned_no_cache']['token_sequence_sha256']
    assert result['generation_metrics']['conditioned_cache']['cache_enabled'] is True
    assert result['generation_metrics']['conditioned_no_cache']['cache_enabled'] is False
    assert result['resource_metrics']['process_cpu_ms'] >= 0
    assert app.state.engine.model.config.attention_mode=='dyn12'
    bad=dict(request,arms={**arms,'bad':{'control_vector':[2.0]*12,'attention_mode':'dyn12'}})
    assert client.post('/v1/condition-probe-v2',headers=headers,json=bad).status_code==503
