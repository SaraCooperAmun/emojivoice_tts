#!/home/emorobcare/.local/share/mamba/envs/emojivoice/bin/python

import sys
import json

import torch
import torch.serialization
import numpy as np

from omegaconf import DictConfig, ListConfig
from omegaconf.base import ContainerMetadata

from matcha.hifigan.config import v1
from matcha.hifigan.denoiser import Denoiser
from matcha.hifigan.env import AttrDict
from matcha.hifigan.models import Generator as HiFiGAN
from matcha.models.matcha_tts import MatchaTTS
from matcha.text import text_to_sequence
from matcha.utils.utils import (
    get_user_data_dir,
    intersperse,
    assert_model_downloaded,
)

#robot
#TTS_MODEL_PATH = (
#    "/home/nvidia/sara_vizij/do_you_feel_me/"
#    "Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
#)

#sara's computer

#robot
TTS_MODEL_PATH = (
    "/home/emorobcare/vizij_project/do_you_feel_me/"
    "Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
)

VOCODER_NAME = "hifigan_univ_v1"

VOCODER_URLS = {
    "hifigan_univ_v1": (
        "https://github.com/shivammehta25/Matcha-TTS-checkpoints/"
        "releases/download/v1.0/g_02500000"
    )
}

LANGUAGE = "en"

STEPS = 10
SPEAKING_RATE = 0.8
TTS_TEMPERATURE = 0.667

SAMPLE_RATE = 22050

EMOTION_TO_SPEAKER = {
    "love": 107,
    "angry": 58,
    "cool": 79,
    "sad": 103,
    "annoyed": 66,
    "happy": 18,
    "neutral": 12,
    "laughing": 15,
    "surprised": 54,
    "embarrassed": 22,
    "thinking": 17,
}


torch.serialization.add_safe_globals([
    DictConfig,
    ListConfig,
    ContainerMetadata,
])

torch.set_default_device("cpu")
torch.cuda.is_available = lambda: False

DEVICE = "cpu"


def load_matcha():
    model = MatchaTTS.load_from_checkpoint(
        TTS_MODEL_PATH,
        map_location=torch.device("cpu"),
        weights_only=False,
    )
    model.eval()
    return model


def load_hifigan(path):
    h = AttrDict(v1)

    vocoder = HiFiGAN(h).to(DEVICE)

    vocoder.load_state_dict(
        torch.load(
            path,
            map_location=DEVICE,
        )["generator"]
    )

    vocoder.eval()
    vocoder.remove_weight_norm()

    return vocoder


def load_models():

    print("Loading Matcha-TTS...", flush=True)

    tts = load_matcha()

    print("Checking HiFiGAN...", flush=True)

    save_dir = get_user_data_dir()
    vocoder_path = save_dir / VOCODER_NAME

    assert_model_downloaded(
        vocoder_path,
        VOCODER_URLS[VOCODER_NAME],
    )

    print("Loading HiFiGAN...", flush=True)

    vocoder = load_hifigan(
        str(vocoder_path)
    )

    denoiser = Denoiser(
        vocoder,
        mode="zeros",
    )

    print("EmojiVoice models loaded.", flush=True)

    return tts, vocoder, denoiser


def process_text(text):

    cleaners = {
        "en": "english_cleaners2"
    }

    x = torch.tensor(
        intersperse(
            text_to_sequence(
                text,
                [cleaners[LANGUAGE]],
            )[0],
            0,
        ),
        dtype=torch.long,
        device=DEVICE,
    )[None]

    x_lengths = torch.tensor(
        [x.shape[-1]],
        dtype=torch.long,
        device=DEVICE,
    )

    return x, x_lengths


@torch.no_grad()
def synthesize(
    tts,
    vocoder,
    denoiser,
    text,
    emotion,
):

    speaker_id = EMOTION_TO_SPEAKER.get(
        emotion.lower(),
        EMOTION_TO_SPEAKER["neutral"],
    )

    x, x_lengths = process_text(text)

    speaker = torch.tensor(
        [speaker_id],
        dtype=torch.long,
        device=DEVICE,
    )

    output = tts.synthesise(
        x,
        x_lengths,
        n_timesteps=STEPS,
        temperature=TTS_TEMPERATURE,
        spks=speaker,
        length_scale=SPEAKING_RATE,
    )

    audio = vocoder(
        output["mel"]
    ).clamp(-1, 1)

    audio = denoiser(
        audio.squeeze(),
        strength=0.00025,
    ).cpu().squeeze()

    audio = audio.cpu().numpy().astype(np.float32)

    duration = len(audio) / SAMPLE_RATE

    return audio, duration


def main():

    tts, vocoder, denoiser = load_models()

    for line in sys.stdin:

        line = line.strip()

        if not line:
            continue

        try:

            request = json.loads(line)

            text = request["text"]
            emotion = request.get(
                "emotion",
                "neutral",
            )

            audio, duration = synthesize(
                tts,
                vocoder,
                denoiser,
                text,
                emotion,
            )

            # Send binary audio through stdout is inconvenient,
            # so encode float32 samples as base64.
            import base64

            audio_bytes = audio.tobytes()

            response = {
                "ok": True,
                "duration": duration,
                "sample_rate": SAMPLE_RATE,
                "audio": base64.b64encode(
                    audio_bytes
                ).decode("ascii"),
            }

            print(
                json.dumps(response),
                flush=True,
            )

        except Exception as exc:

            print(
                json.dumps({
                    "ok": False,
                    "error": str(exc),
                }),
                flush=True,
            )


if __name__ == "__main__":
    main()
