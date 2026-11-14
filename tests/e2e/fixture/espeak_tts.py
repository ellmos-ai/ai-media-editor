"""Write a mono 16-bit WAV with eSpeak NG (formant synthesis, no recorded voice).

Usage: python espeak_tts.py <out.wav> "<text>"   (needs: pip install espeakng-loader==0.2.4)
"""
import ctypes
import sys
import wave

import espeakng_loader

lib = ctypes.CDLL(espeakng_loader.get_library_path())
chunks: list[bytes] = []
CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)


@CALLBACK
def collect(wav, samples, _events):
    if wav and samples > 0:
        chunks.append(ctypes.string_at(wav, samples * 2))
    return 0


rate = lib.espeak_Initialize(2, 0, espeakng_loader.get_data_path().encode(), 0)  # 2 = synchronous
lib.espeak_SetSynthCallback(collect)
lib.espeak_SetVoiceByName(b"en-us")
lib.espeak_SetParameter(1, 145, 0)  # 1 = espeakRATE, words per minute
text = sys.argv[2].encode("utf-8")
lib.espeak_Synth(text, len(text) + 1, 0, 1, 0, 1, None, None)  # POS_CHARACTER, espeakCHARS_UTF8
lib.espeak_Synchronize()
with wave.open(sys.argv[1], "wb") as out:
    out.setnchannels(1)
    out.setsampwidth(2)
    out.setframerate(rate)
    out.writeframes(b"".join(chunks))
