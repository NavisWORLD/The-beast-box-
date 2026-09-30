"""Native original RAWRPHOS BYTE-level BPE transport Unicode contract.

This validates tokenizer reversibility, NOT that a frozen 18K generator has
been trained to reason correctly in every language at its fixed context.
"""
import pytest

from rawrphos.tokenizer.tokenizer import RawrphosTokenizer


MULTISCRIPT = (
    "π ℌ 👩🏽‍🚀 🧠 🌌",
    "東京駅 中文 हिन्दी العربية مرحبا",
    "café cafe\u0301 Zażółć Ελληνικά русский",
    "👨‍👩‍👧‍👦 ❤️ 🇺🇳 ✨",
    "数学∑ 𝕏 🪐 Ω",
)


def test_original_native_byte_bpe_roundtrips_full_multiscript_utf8(tmp_path):
    tokenizer=RawrphosTokenizer.train(MULTISCRIPT,vocab_size=512)
    for sample in MULTISCRIPT:
        assert tokenizer.decode(tokenizer.encode(sample))==sample
        ids=tokenizer.encode(sample,add_bos=True)
        assert ids[0]==tokenizer.bos_id
        assert tokenizer.decode(ids[1:])==sample
    tokenizer.save(tmp_path)
    reopened=RawrphosTokenizer.load(tmp_path)
    assert reopened.sha256==tokenizer.sha256
    for sample in MULTISCRIPT:
        assert reopened.decode(reopened.encode(sample))==sample
    with pytest.raises(UnicodeEncodeError):
        reopened.encode("lone\ud800")


def test_native_tokenizer_preserves_mathematical_compatibility_code_points():
    sample="ℌ and H are distinct source glyphs; 𝕏 ≠ X"
    tok=RawrphosTokenizer.train(MULTISCRIPT+(sample,),vocab_size=512)
    assert tok.decode(tok.encode(sample))==sample
    assert tok.decode(tok.encode("ℌ"))!="H"
