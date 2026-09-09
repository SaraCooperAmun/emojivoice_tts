import torch
import sounddevice as sd

from matcha.hifigan.config import v1
from matcha.hifigan.denoiser import Denoiser
from matcha.hifigan.env import AttrDict
from matcha.hifigan.models import Generator as HiFiGAN
from matcha.models.matcha_tts import MatchaTTS
from matcha.text import sequence_to_text, text_to_sequence
from matcha.utils.utils import get_user_data_dir, intersperse, assert_model_downloaded
import soundfile as sf

import emoji
import torch.serialization
from omegaconf import DictConfig, ListConfig
from omegaconf.base import ContainerMetadata

torch.serialization.add_safe_globals([
    DictConfig,
    ListConfig,
    ContainerMetadata,
])
torch.set_default_device("cpu")
torch.cuda.is_available = lambda : False

# -----------------------------
# CONFIG
# -----------------------------
TTS_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TTS_MODEL_PATH = "./Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
VOCODER_NAME = "hifigan_univ_v1"
VOCODER_URLS = {
    "hifigan_T2_v1": "https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/generator_v1",  # Old url: https://drive.google.com/file/d/14NENd4equCBLyyCSke114Mv6YR_j_uFs/view?usp=drive_link
    "hifigan_univ_v1": "https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/g_02500000",  # Old url: https://drive.google.com/file/d/1qpgI41wNXFcH-iKq1Y42JlBC9j0je8PW/view?usp=drive_link
}
LANGUAGE = "en"
STEPS = 10
SPEAKING_RATE = 0.8
TTS_TEMPERATURE = 0.667

emoji_mapping = {
    '😍' : 107,
    '😡' : 58,
    '😎' : 79,
    '😭' : 103,
    '🙄' : 66,
    '😁' : 18,
    '🙂' : 12,
    '🤣' : 15,
    '😮' : 54,
    '😅' : 22,
    '🤔' : 17
}
emoji_menu = {
    "1": "😍",
    "2": "😡",
    "3": "😎",
    "4": "😭",
    "5": "🙄",
    "6": "😁",
    "7": "🙂",
    "8": "🤣",
    "9": "😮",
    "10": "😅",
    "11": "🤔"
}

# -----------------------------
# LOAD MODELS
# -----------------------------
def load_matcha(path, device):
    model = MatchaTTS.load_from_checkpoint(
        TTS_MODEL_PATH,
        map_location=torch.device("cpu"),
        weights_only=False
    )
    model.eval()
    return model

def load_hifigan(path, device):
    h = AttrDict(v1)
    hifigan = HiFiGAN(h).to(device)
    hifigan.load_state_dict(torch.load(path, map_location=device)["generator"])
    hifigan.eval()
    hifigan.remove_weight_norm()
    return hifigan

def assert_required_models_available():
    save_dir = get_user_data_dir()
    model_path = TTS_MODEL_PATH

    vocoder_path = save_dir / f"{VOCODER_NAME}"
    assert_model_downloaded(vocoder_path, VOCODER_URLS[VOCODER_NAME])
    return {"matcha": model_path, "vocoder": vocoder_path}

@torch.no_grad()
def to_waveform(mel, vocoder, denoiser=None):
    audio = vocoder(mel).clamp(-1, 1)
    if denoiser is not None:
        audio = denoiser(audio.squeeze(), strength=0.00025).cpu().squeeze()
    return audio.cpu().squeeze()


def load_vocoder(vocoder_name, checkpoint_path, device):
    vocoder = None
    if vocoder_name in ("hifigan_T2_v1", "hifigan_univ_v1"):
        vocoder = load_hifigan(checkpoint_path, device)
    else:
        raise NotImplementedError(
            f"Vocoder not implemented! define a load_<<vocoder_name>> method for it"
        )

    denoiser = Denoiser(vocoder, mode="zeros")
    return vocoder, denoiser

def process_text(text, device):
    cleaners = {"en": "english_cleaners2"}
    x = torch.tensor(
        intersperse(text_to_sequence(text, [cleaners[LANGUAGE]])[0], 0),
        dtype=torch.long,
        device=device,
    )[None]
    phonemes = sequence_to_text(x.squeeze(0).tolist())
    phoneme_to_vizij = {
        "P":"PP", "B":"PP", "M":"PP",
        "T":"DD", "D":"DD",
        "K":"kk", "G":"kk",
        "CH":"CH", "JH":"CH",
        "SH":"SS", "ZH":"SS", "S":"SS", "Z":"SS",
        "F":"FF", "V":"FF",
        "TH":"TH", "DH":"TH",
        "N":"nn", "NG":"nn",
        "R":"RR",
        "L":"E",
        "AA":"aa", "AE":"aa", "AH":"aa",
        "IH":"ih", "IY":"ih",
        "AO":"oh", "OW":"oh",
        "UW":"ou", "UH":"ou",
        "ER":"E",
        "SIL":"sil", "SP":"sil"
    }
    visemes = []
    for ph in phonemes.split():
        vis = phoneme_to_vizij.get(ph, "sil")
        visemes.append(vis)

    x_lengths = torch.tensor([x.shape[-1]], dtype=torch.long, device=device)
    return {"x": x, "x_lengths": x_lengths}

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    device = torch.device(TTS_DEVICE)

    print("Loading Matcha‑TTS…")
    paths = assert_required_models_available()
    tts = load_matcha(paths["matcha"], device)

    print("Loading HiFiGAN…")
    vocoder, denoiser = load_vocoder(VOCODER_NAME, paths["vocoder"], device)


    print("\nTTS ready! Type text and choose an emoji.\n")

    while True:
        text = input("Enter text (or 'quit'): ").strip()
        if text.lower() == "quit":
            break

        print("\nChoose a voice:")
        for num, emo in emoji_menu.items():
            print(f"{num}. {emo}")

        choice = input("Select a number: ").strip()

        if choice not in emoji_menu:
            print("Invalid choice, using 🙂")
            em = "🙂"
        else:
            em = emoji_menu[choice]

        spk = torch.tensor([emoji_mapping[em]], device=device)
        processed = process_text(text, device)
        with torch.no_grad():
            out = tts.synthesise(
                processed["x"],
                processed["x_lengths"],
                n_timesteps=STEPS,
                temperature=TTS_TEMPERATURE,
                spks=spk,
                length_scale=SPEAKING_RATE,
            )

        audio = to_waveform(out["mel"], vocoder, denoiser)
        sf.write("tts_output.wav", audio.numpy(), 22050)
        print("Saved to tts_output.wav")
        sd.play(audio, 22050)
        sd.wait()