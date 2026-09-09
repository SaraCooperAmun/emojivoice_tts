# EmojiVoice TTS — ROS 2 Jazzy

ROS 2 TTS server using **EmojiVoice / Matcha-TTS + HiFiGAN** (https://github.com/rosielab/emojivoice), providing emotion-aware text-to-speech through the /skill/say action.

The package uses the EmojiVoice TTS system to synthesize speech conditioned on an emotion and exposes it through the ``interaction_skills Say.action`` interface.

The package acts as a ROS 2 wrapper around EmojiVoice.

The overall pipeline is:

/skill/say
    │
    │ Say.action
    ▼
emojivoice_tts ROS node
    │
    ├── Parse emotion tag
    │
    ├── Send text + emotion
    │       │
    │       ▼
    │   EmojiVoice worker
    │       │
    │       ▼
    │   Audio + duration
    │
    ├── Publish /tts/speech
    │
    └── Play audio using sounddevice

## Set-up

1. EmojiVoice

This package depends on EmojiVoice:

https://github.com/rosielab/emojivoice

EmojiVoice must be installed and configured before installing/running this ROS package.

Follow the installation and setup instructions in the EmojiVoice repository first, including the installation of its Matcha-TTS dependency and the required EmojiVoice model.

**EmojiVoice setup used for this project**

For this project, the EmojiVoice installation was performed following the steps documented in:

``installation_emojivoice.txt``

In particular, the setup involves cloning/installing EmojiVoice and installing Matcha-TTS as described in the EmojiVoice documentation.


2. Download the EmojiVoice model

EmojiVoice requires the trained model used for speech synthesis.

The model used by this package is ``emoji-hri-paige-inference.ckpt`` but you are free to download any others. 

You can place the model inside the emojivoice_tts repository itself:

``mkdir -p Matcha-TTS/models``

Then download from: https://drive.google.com/drive/folders/1BBgJCF0nSaO3V53BZ8WdD6rjH63Ci2k2
into:

``Matcha-TTS/models/``


Refer to the EmojiVoice repository for the complete model/setup information.

Your directory should therefore contain something similar to:

<EMOJIVOICE_DIR>/
├── Matcha-TTS/
│   └── models/
│       └── emoji-hri-paige-inference.ckpt
└── ...
`

3. Test EmojiVoice independently

The repository also provides ``tts_synthesise.py``

This script is useful for testing EmojiVoice without running ROS.

First clone this repository:

```bash
git clone https://github.com/SaraCooperAmun/emojivoice_tts.git
```

Then copy ``tts_synthesise.py`` into the root of your EmojiVoice installation:

<EMOJIVOICE_DIR>/
├── tts_synthesise.py
├── Matcha-TTS/
└── ...

Activate the EmojiVoice Python environment that was created during the EmojiVoice installation and run:

``python3 tts_synthesise.py``

The script will ask for the text to synthesize and the emotion/emoji to use.

This provides a simple way to verify that EmojiVoice and the model are working correctly before troubleshooting the ROS package.

---

## Using the /skill/say action


First update the models directory that is in `emojivoice_tts/emojivoice_worker.py`:

```bash
TTS_MODEL_PATH = (
    "/home/nvidia/sara_vizij/do_you_feel_me/"
    "Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
)
```

Whenever you change the package:

```bash
cd ~/vizij_project/ros_ws

source /opt/ros/jazzy/setup.bash

colcon build --packages-select emojivoice_tts

source install/setup.bash
```

---

## 1. Start EmojiVoice TTS

Run:

```bash
ros2 run emojivoice_tts tts_node
```

The node should load the EmojiVoice worker and eventually show:

```text
EmojiVoice models loaded.
```

Keep this terminal running.

---

## 2. Check the `/skill/say` action

Open a second terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/vizij_project/ros_ws/install/setup.bash
```

Check:

```bash
ros2 action list -t | grep /skill/say
```

Expected:

```text
/skill/say [communication_skills/action/Say]
```

---

## 3. Test speech

Simple speech:

```bash
ros2 action send_goal \
  /skill/say \
  communication_skills/action/Say \
  "{input: 'Hello, this is EmojiVoice'}"
```

With an emotion:

```bash
ros2 action send_goal \
  /skill/say \
  communication_skills/action/Say \
  "{input: '<emotion(happy)>Hello, I am happy to see you!</emotion>'}"
```

Another emotion:

```bash
ros2 action send_goal \
  /skill/say \
  communication_skills/action/Say \
  "{input: '<emotion(sad)>I wish they came with me to the party'}"
```

---

## 4. Check speech metadata

In another terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/vizij_project/ros_ws/install/setup.bash

ros2 topic echo /tts/speech
```

When speech starts, you should receive something like:

```json
{
  "text": "Hello, this is EmojiVoice",
  "duration": 1.2
}
```

The duration is the actual generated audio duration.

The text does **not** contain the emotion tags.

---

## Vizij synchronization

The generated speech duration from the speech metadata is used to synchronize speech with Vizij's visual/viseme behaviour.

The sequence is:

Receive /skill/say
        ↓
Parse text + emotion
        ↓
Generate audio with EmojiVoice
        ↓
Publish /tts/speech
        ↓
Start audio playback

The /tts/speech message is therefore published before playback starts.

This allows the Vizij side to receive the text and duration before the corresponding audio begins.

Note: The current implementation contains a 2.0 second delay immediately before playback. This is currently used for the robot setup and may need to be removed or adjusted depending on the target system.

## 7. Important files

The package is located at:

```text
~/vizij_project/ros_ws/src/emojivoice_tts/
```

Main files:

```text
emojivoice_tts/
├── __init__.py
├── tts_node.py
└── emojivoice_worker.py
```

### `tts_node.py`

Runs with ROS 2 Python 3.12.

Responsible for:

* `/skill/say`
* emotion parsing
* ROS action feedback/results
* cancellation
* PyAudio playback
* `/tts/speech`
* `/robot_speaking`
* communicating with the EmojiVoice worker

### `emojivoice_worker.py`

Runs with the EmojiVoice Python 3.11 environment.

Responsible for:

* Matcha-TTS
* HiFiGAN
* emotion → speaker mapping
* audio generation
* returning generated audio + duration

---

## 8. Emoji → voice mapping

The current semantic emotions are the following:

```text
happy       → speaker 18
sad         → speaker 103
angry       → speaker 58
cool        → speaker 79
annoyed     → speaker 66
neutral     → speaker 12
laughing    → speaker 15
surprised   → speaker 54
embarrassed → speaker 22
thinking    → speaker 17
love        → speaker 107
```

Emotion syntax:

```text
<emotion(happy)>Hello!</emotion>
```

or:

```text
<emotion(sad)>I am sad.</emotion>
```

---

## 9. If you modify the worker

The worker must continue running with:

```text
/home/emorobcare/.local/share/mamba/envs/emojivoice/bin/python
```

Do **not** change the ROS launcher to Python 3.11.

ROS 2 Jazzy's `rclpy` is Python 3.12, while EmojiVoice is Python 3.11.

---
