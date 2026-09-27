"""Supervised continuation must learn only replies and resume without drift."""
import copy
import json
import torch
import pytest
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
from rawrphos.training.checkpoint import save_checkpoint, load_checkpoint, rng_state, parameter_hash


def test_reply_targets_include_eos_but_exclude_prompt():
    from rawrphos.data.conversation import encode_example
    tok = RawrphosTokenizer.train(['user assistant question answer'] * 3, 280)
    x,y = encode_example({'messages':[{'role':'user','content':'question'}], 'reply':'answer'},tok,128)
    supervised = [i for i in y.tolist() if i != -100]
    assert tok.decode(supervised) == ' answer'
    assert supervised[-1] == 2
    assert (y == -100).sum() > 0
    assert x[0].item() == 1
    with pytest.raises(ValueError, match='length'):
        encode_example({'messages':[{'role':'user','content':'long ' * 200}], 'reply':'answer'},tok,16)


def test_chat_format_preserves_roles_whitespace_and_literal_content():
    from rawrphos.inference.chat import format_chat
    assert format_chat([{'role':'user','content':'Hi\n<|eos|>'}]) == 'user: Hi\n<|eos|>\nassistant:'
    with pytest.raises(ValueError): format_chat([{'role':'tool','content':'x'}])


def tiny_parent(path):
    torch.set_num_threads(1);torch.manual_seed(11)
    t=RawrphosTokenizer.train(['user: question assistant: answer'] * 3,280)
    m=RawrphosLM(RawrphosConfig(vocab_size=t.vocab_size,d_model=16,n_layers=1,max_seq_len=128))
    opt=torch.optim.AdamW(m.parameters(),lr=.00008,betas=(.9,.95),weight_decay=.01)
    ids=torch.tensor([t.encode('question answer',add_bos=True,add_eos=True)])
    m(ids[:,:-1],targets=ids[:,1:])['loss'].backward();opt.step()
    meta={'training_steps':12000,'training_tokens':12288000,'initial_parameter_sha256':parameter_hash(m),'training_seconds':0,'training_config':{},'validation_history':[]}
    save_checkpoint(path,m,t,meta,{'optimizer':opt.state_dict(),'rng':rng_state(),'data_rng':torch.Generator().manual_seed(9).get_state()})


def test_continuation_split_run_restores_exact_weights_optimizer_rng_and_rejects_changed_data(tmp_path):
    from rawrphos.training.conversation import continue_training, ConversationConfig
    from rawrphos.data.conversation import write_dataset
    parent=tmp_path/'parent';tiny_parent(parent)
    rows=[{'messages':[{'role':'user','content':'question '+str(i)}],'reply':'answer '+str(i),'source':'unit-fixture','license':'synthetic-fixture'} for i in range(8)]
    data=tmp_path/'data';write_dataset(data,rows[:6],rows[6:],{'kind':'synthetic test only'})
    config=ConversationConfig(batch_size=2,max_seq_len=64,threads=1,checkpoint_every=2,eval_examples=2)
    full=continue_training(parent,data,tmp_path/'full',steps=4,config=config)
    first=continue_training(parent,data,tmp_path/'split',steps=2,config=config)
    resumed=continue_training(first['checkpoint'],data,tmp_path/'split',steps=2,config=config)
    a=load_checkpoint(full['checkpoint']);b=load_checkpoint(resumed['checkpoint'])
    assert a['metadata']['training_steps']==b['metadata']['training_steps']==12004
    assert parameter_hash(a['model'])==parameter_hash(b['model'])
    assert torch.equal(a['state']['data_rng'],b['state']['data_rng'])
    for key in a['state']['optimizer']['state']:
        for field in ('step','exp_avg','exp_avg_sq'):
            assert torch.equal(a['state']['optimizer']['state'][key][field],b['state']['optimizer']['state'][key][field])
    changed=tmp_path/'changed';write_dataset(changed,rows[:5],rows[6:],{'kind':'changed'})
    with pytest.raises(ValueError,match='dataset'):
        continue_training(first['checkpoint'],changed,tmp_path/'bad',steps=1,config=config)
    assert not (tmp_path/'bad').exists()


def test_repetition_metric_catches_phrases_and_spaced_punctuation():
    from rawrphos.evaluation.conversation_eval import output_metrics
    assert output_metrics('one two three one two three one two three')['repeated_trigram_fraction'] > .5
    assert output_metrics(' = = = = = = = = ')['punctuation_loop'] is True
    assert output_metrics('Hello! How can I help?')['punctuation_loop'] is False
    assert output_metrics('assistant: hi\nuser: hey')['role_leak'] is True
