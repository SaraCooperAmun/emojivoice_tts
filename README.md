# EmojiVoice TTS — ROS 2 Jazzy

ROS 2 TTS backend using **EmojiVoice / Matcha-TTS + HiFiGAN** to provide emotion-aware text-to-speech through the `/tts/say` action.

The package acts as a ROS 2 wrapper around EmojiVoice.

The overall architecture is:

```text
Dialogue Manager
      │
      │ /tts/say
      │ Say.action
      ▼
emojivoice_tts ROS node
      │
      ├── Parse voice expression
      ├── Send text + emotion
      │
      ▼
EmojiVoice worker
      │
      ├── Matcha-TTS
      ├── HiFiGAN
      │
      ▼
Audio + duration
      │
      ├── Publish /tts/speech
      │
      └── Play audio using sounddevice
```

The `/skill/say` action is provided by the **Dialogue Manager**. The Dialogue Manager processes the generic voice-expression syntax and sends the resulting text to the `/tts/say` TTS backend.

For more information, see the [Dialogue Manager documentation](https://gitlab.iiia.csic.es/socialminds/ros4hri/dialogue_manager/-/tree/main/dialogue_manager).

---

## 1. Setup

### EmojiVoice

This package depends on EmojiVoice:

[EmojiVoice](https://github.com/rosielab/emojivoice)

EmojiVoice must be installed and configured before installing/running this ROS package.

Follow the installation and setup instructions in the EmojiVoice repository, including the installation of its Matcha-TTS dependency and the required EmojiVoice model.

### EmojiVoice setup used for this project

For this project, the EmojiVoice installation was performed following the steps documented in:

```text
installation_emojivoice.txt
```

In particular, the setup involves cloning/installing EmojiVoice and installing Matcha-TTS as described in the EmojiVoice documentation.

---

## 2. Download the EmojiVoice model

EmojiVoice requires a trained model for speech synthesis.

The model currently used by this package is:

```text
emoji-hri-paige-inference.ckpt
```

You may use another compatible EmojiVoice model if required.

The model can be stored inside the EmojiVoice installation:

```bash
mkdir -p Matcha-TTS/models
```

The model can be downloaded from:

[EmojiVoice models](https://drive.google.com/drive/folders/1BBgJCF0nSaO3V53BZ8WdD6rjH63Ci2k2)

Your EmojiVoice installation should contain something similar to:

```text
<EMOJIVOICE_DIR>/
├── Matcha-TTS/
│   └── models/
│       └── emoji-hri-paige-inference.ckpt
└── ...
```

Refer to the EmojiVoice repository for the complete model and setup information.

---

## 3. Test EmojiVoice independently

The repository also provides:

```text
tts_synthesise.py
```

This script can be used to test EmojiVoice without running ROS.

Clone this repository:

```bash
git clone https://github.com/SaraCooperAmun/emojivoice_tts.git
```

Then copy `tts_synthesise.py` into the root of your EmojiVoice installation:

```text
<EMOJIVOICE_DIR>/
├── tts_synthesise.py
├── Matcha-TTS/
└── ...
```

Activate the EmojiVoice Python environment and run:

```bash
python3 tts_synthesise.py
```

The script will ask for the text to synthesize and the emotion/emoji to use.

This provides a simple way to verify that EmojiVoice and the model are working correctly before troubleshooting the ROS package.

---

## 4. EmojiVoice configuration

The EmojiVoice Python environment and model path are configured using a ROS 2 YAML configuration file.

The configuration file is:

```text
config/emojivoice.yaml
```

It contains:

```yaml
tts_node:
  ros__parameters:
    emojivoice_python: "/path/to/emojivoice/bin/python"
    tts_model_path: "/path/to/Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
```

For example:

```yaml
tts_node:
  ros__parameters:
    emojivoice_python: "/home/emorobcare/.local/share/mamba/envs/emojivoice/bin/python"
    tts_model_path: "/home/emorobcare/vizij_project/do_you_feel_me/Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
```

### Changing the paths

When moving the package to another machine, change these two parameters:

```yaml
emojivoice_python: "/path/to/emojivoice/bin/python"
tts_model_path: "/path/to/Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
```

No source-code changes are required.

The worker receives the model path as a command-line argument, while the ROS node starts the worker using the configured EmojiVoice Python interpreter.

The worker path itself does not need to be configured because `emojivoice_worker.py` is located relative to the ROS package.

---

## 5. Build the ROS package

Whenever the package is changed:

```bash
cd ~/vizij_project/ros_ws
source /opt/ros/jazzy/setup.bash

colcon build --packages-select emojivoice_tts --symlink-install

source install/setup.bash
```

---

## 6. Start EmojiVoice TTS

The recommended way to start the node is using the ROS 2 launch file:

```bash
ros2 launch emojivoice_tts emojivoice_tts.launch.py
```

The launcher:

1. Starts the `tts_node` ROS node.
2. Loads `config/emojivoice.yaml`.
3. Provides the EmojiVoice Python environment path.
4. Provides the EmojiVoice model path.
5. Starts the EmojiVoice worker.
6. Loads Matcha-TTS and HiFiGAN.

The node provides:

```text
/tts/say
/tts/speech
/robot_speaking
```

The node should load the EmojiVoice worker and eventually report that the EmojiVoice models are loaded.

Keep this terminal running.

---

## 7. `/tts/say` action

The EmojiVoice ROS node provides:

```text
/tts/say
```

with type:

```text
communication_skills/action/Say
```

Check that it is available:

```bash
ros2 action list -t | grep /tts/say
```

Expected:

```text
/tts/say [communication_skills/action/Say]
```

The `/skill/say` action is provided by the Dialogue Manager and should not be confused with the TTS backend action.

The architecture is:

```text
Application
    │
    ▼
/skill/say
    │
    │ Dialogue Manager
    ▼
/tts/say
    │
    │ EmojiVoice
    ▼
Audio
```

For more information about the `/skill/say` interface and voice-expression handling, see the [Dialogue Manager documentation](https://gitlab.iiia.csic.es/socialminds/ros4hri/dialogue_manager/-/tree/main/dialogue_manager).

---

## 8. Test speech

### Neutral speech

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "Hello, this is EmojiVoice"}'
```

### Speech with a voice expression

EmojiVoice receives the generic format:

```text
<voice_expression(😍)>Hello, I am happy to see you!</voice_expression>
```

For example:

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "<voice_expression(😍)>Hello, I am happy to see you!</voice_expression>"}'
```

The ROS node extracts the emoji and maps it to the corresponding EmojiVoice speaker ID before generating the speech.

---

## 9. Dialogue Manager integration

The Dialogue Manager uses the generic syntax:

```text
<use voice_expression(EXPRESSION)>text</use>
```

For example:

```text
<use voice_expression(😍)>Hello!</use>
```

The Dialogue Manager processes this expression and sends the corresponding tagged text to the TTS backend:

```text
<voice_expression(😍)>Hello!</voice_expression>
```

EmojiVoice then converts the emoji into its internal speaker ID.

This keeps the Dialogue Manager independent of the specific TTS backend.

For more details, see the [Dialogue Manager documentation](https://gitlab.iiia.csic.es/socialminds/ros4hri/dialogue_manager/-/tree/main/dialogue_manager).

---

## 10. Emoji → voice mapping

The current EmojiVoice mapping is:

```text
😍  → speaker 107
😡  → speaker 58
😎  → speaker 79
😭  → speaker 103
🙄  → speaker 66
😁  → speaker 18
🙂  → speaker 12
🤣  → speaker 15
😮  → speaker 54
😅  → speaker 22
🤔  → speaker 17
```

Neutral speech does not use a voice-expression tag.

For example:

```text
Hello, how are you?
```

is generated without an expression.

An expression is specified using:

```text
<voice_expression(😍)>Hello!</voice_expression>
```

The EmojiVoice node converts:

```text
😍
```

into:

```text
107
```

before sending the request to the EmojiVoice worker.

---

## 11. Action feedback

During playback, the `/tts/say` action provides word-level feedback through:

```text
Say.Feedback.feedback.data_str
```

For example:

```text
Hello,

how

are

you?
```

The feedback is generated while the audio is playing.

This allows clients such as the Dialogue Manager or other ROS components to receive the currently spoken word.

---

## 12. Speech metadata

The node publishes speech metadata on:

```text
/tts/speech
```

Check it with:

```bash
ros2 topic echo /tts/speech
```

When speech starts, a message similar to the following is published:

```json
{
  "text": "Hello, this is EmojiVoice",
  "duration": 1.2
}
```

The duration is the generated audio duration.

The published text does **not** contain the voice-expression tag.

For example:

```text
<voice_expression(😍)>Hello!</voice_expression>
```

is published as:

```json
{
  "text": "Hello!",
  "duration": 1.2
}
```

---

## 13. Vizij synchronization

The generated speech duration from `/tts/speech` is used to synchronize speech with Vizij's visual/viseme behaviour.

The sequence is:

```text
Receive /tts/say
        ↓
Parse text + voice expression
        ↓
Generate audio with EmojiVoice
        ↓
Publish /tts/speech
        ↓
Start audio playback
```

The `/tts/speech` message is therefore published before playback starts.

This allows the Vizij side to receive the text and duration before the corresponding audio begins.

Note: THIS WILL BE FIXED BASED ON VISEME BASED ARCHITECTURE.

### Playback delay

The current implementation contains a 2.0 second delay immediately before playback.

This is currently used for the robot setup and may need to be removed or adjusted depending on the target system.

---

## 14. Important files

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

config/
└── emojivoice.yaml

launch/
└── emojivoice_tts.launch.py
```

### `tts_node.py`

Runs with the ROS 2 Python 3.12 environment.

Responsible for:

* `/tts/say`
* voice-expression parsing
* emoji → speaker ID mapping
* ROS action feedback/results
* cancellation
* audio playback
* `/tts/speech`
* `/robot_speaking`
* communicating with the EmojiVoice worker

### `emojivoice_worker.py`

Runs with the EmojiVoice Python 3.11 environment.

Responsible for:

* Matcha-TTS
* HiFiGAN
* speaker ID selection
* audio generation
* returning generated audio and duration

### `config/emojivoice.yaml`

Contains machine-specific configuration:

* EmojiVoice Python interpreter
* EmojiVoice Matcha-TTS model path

### `launch/emojivoice_tts.launch.py`

Starts `tts_node` and loads the EmojiVoice configuration.

---

## 15. Python environments

ROS 2 Jazzy uses Python 3.12, while EmojiVoice runs in its own Python 3.11 environment.

The architecture is therefore:

```text
ROS 2 Jazzy
Python 3.12
    │
    │ subprocess
    ▼
EmojiVoice environment
Python 3.11
    │
    ├── Matcha-TTS
    └── HiFiGAN
```

Do **not** change the ROS 2 launcher to Python 3.11.

The EmojiVoice worker continues to run using the Python interpreter specified by:

```yaml
emojivoice_python: "/path/to/emojivoice/bin/python"
```

---

## 16. Troubleshooting

### Check the `/tts/say` action

```bash
ros2 action info /tts/say
```

Make sure the EmojiVoice node is providing the action.

### Check the node

```bash
ros2 node list
```

The node should appear as:

```text
/tts_node
```

### Check speech metadata

```bash
ros2 topic echo /tts/speech
```

### Test an expression directly

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "<voice_expression(😍)>Hello, how are you?</voice_expression>"}' \
--feedback
```

Expected logs include:

```text
Voice expression detected: '😍' -> EmojiVoice emotion 107
Clean speech text: 'Hello, how are you?'
Speech emotion: '107'
```

and word-level feedback during playback.

## Testing

Run the package tests from the ROS 2 workspace:

```bash
cd ~/vizij_project/ros_ws

colcon test --packages-select emojivoice_tts
colcon test-result --verbose
```

The test suite includes:

* Python unit tests for `TtsNode`
* `flake8` code-style checks
* `pep257` docstring checks

To run the tests after rebuilding the package:

```bash
colcon build --packages-select emojivoice_tts
source install/setup.bash

colcon test --packages-select emojivoice_tts
colcon test-result --verbose
```

If a linting test fails, the checks can also be run directly from the package source directory:

```bash
cd ~/vizij_project/ros_ws/src/emojivoice_tts
```

Run `flake8`:

```bash
python3 -m flake8 emojivoice_tts
```

Run `pep257`:

```bash
python3 -m ament_pep257.main emojivoice_tts launch test
```
