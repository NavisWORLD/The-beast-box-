"""Training-only byte BPE with a hash-bound vocabulary and UTF-8 validation."""
import hashlib
import json
from pathlib import Path
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders


class RawrphosTokenizer:
    pad_id=0; bos_id=1; eos_id=2
    def __init__(self,backend):
        self.backend=backend
        # Literal user/corpus text is never a control-token transport. This is
        # a runtime encoding option, not a vocabulary/merge/serialized change.
        # BOS/EOS are inserted explicitly below, identically in train and serve.
        self.backend.encode_special_tokens=True
    @classmethod
    def train(cls,texts,vocab_size=4096):
        if type(vocab_size) is not int or vocab_size<260: raise ValueError('byte BPE needs at least 260 entries')
        backend=Tokenizer(models.BPE(unk_token='<|unk|>'))
        backend.pre_tokenizer=pre_tokenizers.ByteLevel(add_prefix_space=False,use_regex=True)
        backend.decoder=decoders.ByteLevel()
        trainer=trainers.BpeTrainer(vocab_size=vocab_size,min_frequency=2,
            special_tokens=['<|pad|>','<|bos|>','<|eos|>','<|unk|>'],
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),show_progress=False)
        backend.train_from_iterator(texts,trainer)
        return cls(backend)
    @property
    def vocab_size(self): return self.backend.get_vocab_size()
    @property
    def sha256(self): return hashlib.sha256(self.backend.to_str().encode()).hexdigest()
    def encode(self,text,add_bos=False,add_eos=False):
        if not isinstance(text,str): raise ValueError('tokenizer input must be text')
        text.encode('utf-8',errors='strict')
        return ([self.bos_id] if add_bos else [])+self.backend.encode(text,add_special_tokens=False).ids+([self.eos_id] if add_eos else [])
    def decode(self,ids):
        ids=list(ids)
        if any(type(i) is not int or not 0<=i<self.vocab_size for i in ids): raise ValueError('invalid token id')
        return self.backend.decode(ids,skip_special_tokens=True)
    def save(self,directory):
        p=Path(directory); p.mkdir(parents=True,exist_ok=True)
        (p/'tokenizer.json').write_text(self.backend.to_str(),encoding='utf-8')
        (p/'metadata.json').write_text(json.dumps({'schema':'rawrphos-byte-bpe-v1','sha256':self.sha256,
            'vocab_size':self.vocab_size,'pad_id':0,'bos_id':1,'eos_id':2,'trained_on':'training split only'},sort_keys=True))
    @classmethod
    def load(cls,directory):
        p=Path(directory); metadata=json.loads((p/'metadata.json').read_text())
        t=cls(Tokenizer.from_file(str(p/'tokenizer.json')))
        if t.sha256!=metadata['sha256'] or t.vocab_size!=metadata['vocab_size']: raise ValueError('tokenizer hash mismatch')
        for token,idx in [('<|pad|>',0),('<|bos|>',1),('<|eos|>',2)]:
            if t.backend.token_to_id(token)!=idx: raise ValueError('special-token mismatch')
        return t
