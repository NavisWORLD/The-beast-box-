import json
import pytest
import torch

def test_tokenizer_unicode_identity_and_bad_input(tmp_path):
    from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
    t=RawrphosTokenizer.train(['Hello world! RAWRPHØS 🌌\nこんにちは']*10,vocab_size=300)
    text='New unseen 🌋 é 漢字\n\t'; assert t.decode(t.encode(text))==text
    t.save(tmp_path); loaded=RawrphosTokenizer.load(tmp_path)
    assert t.sha256==loaded.sha256 and t.encode(text)==loaded.encode(text)
    with pytest.raises((UnicodeError,ValueError)): t.encode('\ud800')
    with pytest.raises(ValueError): t.decode([t.vocab_size])

def test_corpus_order_independent_exclusions_and_splits(tmp_path):
    from rawrphos.data.corpus import build_corpus,load_corpus
    records=[{'text':f'Unique story number {i}: '+word,'source':'public:test','license':'CC0-1.0','revision':'1'}
             for i,word in enumerate(['apple','moon','chair','boat','tree','lamp'])]
    records += [dict(records[0]),{'text':'api_key=abcdefghijklmnopqrstuvwxyz','source':'public:test','license':'CC0-1.0'},
                {'text':'private detail','source':'runtime-memory','license':'CC0-1.0'}]
    a=build_corpus(records,tmp_path/'a'); b=build_corpus(reversed(records),tmp_path/'b')
    assert a==b and a['rejected']['duplicate']==1 and a['rejected']['secret']==1
    data=load_corpus(tmp_path/'a')
    assert not {x['sha256'] for x in data['train']} & {x['sha256'] for x in data['validation']}

def test_near_duplicate_screen_retains_its_effect(tmp_path):
    from rawrphos.data.corpus import build_corpus
    text=' '.join('word'+str(i) for i in range(400))
    rows=[{'text':x,'source':'public-test','license':'CC0-1.0'} for x in [text,text+' extra','An independent document about a quiet pond.']]
    manifest=build_corpus(rows,tmp_path/'dedup')
    assert manifest['rejected']['near_duplicate']==1

def test_actual_updates_and_exact_resume(tmp_path):
    from rawrphos.data.corpus import build_corpus
    from rawrphos.architecture.model import RawrphosConfig
    from rawrphos.training.train import train,TrainingConfig
    from rawrphos.training.checkpoint import load_checkpoint
    records=[{'text':('The '+w+' is here. We can see it. ')*8,'source':'test-fixture','license':'CC0-1.0'} for w in ['sun','cat','moon','dog','sea','tree']]
    build_corpus(records,tmp_path/'corpus')
    tc=TrainingConfig(total_steps=4,batch_size=2,seq_len=16,vocab_size=300,eval_every=2,eval_batches=2,checkpoint_every=2,threads=1)
    mc=RawrphosConfig(vocab_size=300,d_model=32,n_heads=4,n_layers=2,max_seq_len=128)
    full=train(tmp_path/'corpus',tmp_path/'full',mc,tc,steps=4)
    split=train(tmp_path/'corpus',tmp_path/'split',mc,tc,steps=2)
    resumed=train(tmp_path/'corpus',tmp_path/'split',mc,tc,steps=2,resume=split['checkpoint'])
    a=load_checkpoint(full['checkpoint']); b=load_checkpoint(resumed['checkpoint'])
    assert a['metadata']['training_steps']==4
    assert a['metadata']['initial_parameter_sha256']!=a['metadata']['parameter_sha256']
    assert a['metadata']['parameter_sha256']==b['metadata']['parameter_sha256']
    for k,v in a['model'].state_dict().items(): assert torch.equal(v,b['model'].state_dict()[k]),k
    p=tmp_path/'split'/'step-00000004'/'model.safetensors'
    p.write_bytes(p.read_bytes()[:-4]+b'FAIL')
    with pytest.raises(ValueError,match='hash'): load_checkpoint(p.parent)
