# EmojiVoice TTS — ROS 2 Jazzy

ROS 2 TTS backend using **EmojiVoice / Matcha-TTS + HiFiGAN** to provide emotion-aware text-to-speech through the `/tts/say` action.

The package acts as a ROS 2 wrapper around EmojiVoice and provides aligned phoneme and viseme information during speech playback.

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
Audio + aligned phonemes
      │
      ├── Play audio using sounddevice
      │
      ├── Publish /tts/speech
      │
      ├── Publish /tts/phoneme
      │
      └── Publish /tts/visemes
                         │
                         ▼
                    Vizij face
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
│
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

The EmojiVoice Python environment, model path, and viseme mode are configured using a ROS 2 YAML configuration file.

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
    viseme_mode: "normal"
```

For example:

```yaml
tts_node:
  ros__parameters:
    emojivoice_python: "/home/emorobcare/.local/share/mamba/envs/emojivoice/bin/python"
    tts_model_path: "/home/emorobcare/vizij_project/do_you_feel_me/Matcha-TTS/models/emoji-hri-paige-inference.ckpt"
    viseme_mode: "normal"
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

### Viseme mode

The `viseme_mode` parameter controls how visemes are generated and published.

The available modes are:

```text
normal
static
open_close
```

#### `normal`

Uses the phoneme alignment returned by EmojiVoice/Matcha-TTS.

Each aligned phoneme is converted into its corresponding facial viseme and published during audio playback.

```yaml
viseme_mode: "normal"
```

#### `static`

Disables viseme publication.

The audio and phoneme streams continue to operate normally, but no messages are published on `/tts/visemes`.

```yaml
viseme_mode: "static"
```

This mode can be used when the robot face should remain static or when another component is responsible for facial animation.

#### `open_close`

Ignores the individual phoneme alignment for facial animation and generates a simple alternating open/closed mouth sequence during speech.

```yaml
viseme_mode: "open_close"
```

The generated sequence alternates between:

```text
OH  = 13
SIL = 0
```

at a fixed interval during the generated audio.

This provides a simple talking-mouth animation without requiring the phoneme-to-viseme mapping.

### Changing the viseme mode at runtime

The viseme mode is a ROS 2 parameter and can be changed while the node is running:

```bash
ros2 param set /tts_node viseme_mode normal
```

```bash
ros2 param set /tts_node viseme_mode static
```

```bash
ros2 param set /tts_node viseme_mode open_close
```

The selected mode is applied to the next utterance.

Check the current value with:

```bash
ros2 param get /tts_node viseme_mode
```

The launch file also exposes `viseme_mode` as a launch argument:

```bash
ros2 launch emojivoice_tts emojivoice_tts.launch.py viseme_mode:=normal
```

or:

```bash
ros2 launch emojivoice_tts emojivoice_tts.launch.py viseme_mode:=static
```

or:

```bash
ros2 launch emojivoice_tts emojivoice_tts.launch.py viseme_mode:=open_close
```

The launch argument overrides the value specified in the YAML configuration for that launch.

---

## 5. ROS 4 HRI message dependencies

The package uses the local ROS 4 HRI `hri_msgs` package for speech alignment messages.

The repository is:

```text
https://gitlab.iiia.csic.es/socialminds/ros4hri/hri_msgs.git
```

The package provides the following messages used by EmojiVoice TTS:

```text
hri_msgs/msg/Phoneme
hri_msgs/msg/Visemes
hri_msgs/msg/Viseme
```

### Phoneme message

`Phoneme.msg` contains:

```text
uint8 value

float32 time

float32 duration
```

The `value` identifies a normalized phoneme, while `time` and `duration` specify its aligned position in the generated utterance.

### Viseme messages

`Visemes.msg` contains:

```text
Viseme[] visemes
```

Each `Viseme.msg` contains:

```text
uint8 value

float32 time

float32 duration
```

The `value` identifies the corresponding facial viseme, while `time` and `duration` specify its aligned position in the utterance.

The current `Viseme` vocabulary is:

```text
SIL = 0
PP  = 1
FF  = 2
TH  = 3
DD  = 4
KK  = 5
CH  = 6
SS  = 7
NN  = 8
RR  = 9
AA  = 10
E   = 11
IH  = 12
OH  = 13
OU  = 14
```

The phoneme-to-viseme conversion is performed by `tts_node.py`.

The TTS node supports two general ways of providing viseme information:

1. Publish individual visemes as they need to be played during audio playback. In this case, the `time` and `duration` fields are not required for synchronization because the message arrival time represents the playback event.

2. Compute the expected timing of the visemes and provide the timing information in the messages.

The current `normal` implementation publishes aligned visemes progressively during playback. The `open_close` mode generates its own timed open/close sequence.

---

## 6. Build the ROS package

Whenever the package is changed:

```bash
cd ~/vizij_project/ros_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select hri_msgs emojivoice_tts --symlink-install
source install/setup.bash
```

If only `emojivoice_tts` was changed and `hri_msgs` has already been built, it is sufficient to build:

```bash
colcon build --packages-select emojivoice_tts --symlink-install
```

---

## 7. Start EmojiVoice TTS

The recommended way to start the node is using the ROS 2 launch file:

```bash
ros2 launch emojivoice_tts emojivoice_tts.launch.py
```

The launcher:

1. Starts the `tts_node` ROS node.
2. Loads `config/emojivoice.yaml`.
3. Provides the EmojiVoice Python environment path.
4. Provides the EmojiVoice model path.
5. Provides the `viseme_mode` parameter.
6. Starts the EmojiVoice worker.
7. Loads Matcha-TTS and HiFiGAN.

A specific viseme mode can be selected at launch:

```bash
ros2 launch emojivoice_tts emojivoice_tts.launch.py viseme_mode:=normal
```

The node provides:

```text
/tts/say
/tts/speech
/tts/phoneme
/tts/visemes
/robot_speaking
```

The node should load the EmojiVoice worker and eventually report that the EmojiVoice models are loaded.

Keep this terminal running.

---

## 8. `/tts/say` action

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
Audio + speech alignment
```

For more information about the `/skill/say` interface and voice-expression handling, see the [Dialogue Manager documentation](https://gitlab.iiia.csic.es/socialminds/ros4hri/dialogue_manager/-/tree/main/dialogue_manager).

---

## 9. Test speech

### Neutral speech

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "Hello, this is EmojiVoice"}'
```

### Speech with a voice expression

EmojiVoice accepts both emoji and semantic string expressions using the generic format:

```text
<set expression(EXPRESSION)>text</expression>
```

For example:

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "<set expression(😍)>Hello, I am happy to see you!</expression>"}'
```

Or using a semantic expression name:

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "<set expression(happy)>Hello, I am happy to see you!</expression>"}'
```

The ROS node extracts the expression and maps it to the corresponding EmojiVoice speaker ID before generating the speech.

---

## 10. Dialogue Manager integration

The Dialogue Manager uses the generic syntax:

```text
<set expression(EXPRESSION)>text</expression>
```

For example:

```text
<set expression(😍)>Hello!</expression>
```

The Dialogue Manager processes this expression and sends the corresponding tagged text to the TTS backend:

```text
<set expression(😍)>Hello!</expression>
```

EmojiVoice then converts the emoji into its internal speaker ID.

This keeps the Dialogue Manager independent of the specific TTS backend.

For more details, see the [Dialogue Manager documentation](https://gitlab.iiia.csic.es/socialminds/ros4hri/dialogue_manager/-/tree/main/dialogue_manager).

---

## 11. Emoji → voice mapping

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

Semantic names:

```text
happy       → speaker 18
sad         → speaker 103
angry       → speaker 58
cool        → speaker 79
annoyed     → speaker 66
joyful      → speaker 18
surprised   → speaker 54
embarrassed → speaker 22
thinking    → speaker 17
```

Neutral speech does not use a voice-expression tag.

For example:

```text
Hello, how are you?
```

is generated without an expression.

An expression is specified using:

```text
<set expression(😍)>Hello!</expression>
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

## 12. Action feedback

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

## 13. Speech metadata

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
<set expression(😍)>Hello!</expression>
```

is published as:

```json
{
  "text": "Hello!",
  "duration": 1.2
}
```

`/tts/speech` provides speech metadata. It is **not** the timing source for Vizij facial animation.

---

# 14. Phoneme alignment

EmojiVoice / Matcha-TTS provides attention information that can be used to align generated audio with the phoneme sequence.

The EmojiVoice worker converts this alignment into a sequence of timed phonemes.

The ROS node publishes each aligned phoneme on:

```text
/tts/phoneme
```

Check it with:

```bash
ros2 topic echo /tts/phoneme
```

Each message contains:

```text
value

time

duration
```

For example:

```text
value: 23
time: 0.0
duration: 0.0232
---

value: 39
time: 0.0464
duration: 0.0348
---

value: 19
time: 0.1045
duration: 0.0348
```

The timestamps are measured from the beginning of audio playback.

Non-phonetic Matcha tokens such as stress markers, length markers, spaces, punctuation and other alignment symbols are ignored by the ROS node.

---

# 15. Viseme alignment

The aligned phonemes are converted into facial visemes using the mapping implemented in `tts_node.py`.

The resulting visemes are published on:

```text
/tts/visemes
```

Check them with:

```bash
ros2 topic echo /tts/visemes
```

Each message contains an array of `Viseme.msg` values:

```text
value

time

duration
```

In `normal` mode, the phoneme-to-viseme mapping is performed during playback. When the timestamp of an aligned phoneme is reached, the corresponding viseme is published.

For example:

```text
value: 12
time: 0.0
duration: 0.0232
---

value: 12
time: 0.0464
duration: 0.0348
---

value: 8
time: 0.1045
duration: 0.0348
---

value: 13
time: 0.2322
duration: 0.0348
```

The phoneme and viseme messages use the same timing information.

For example:

```text
Phoneme:

    value: 35
    time: 0.2322
    duration: 0.0348

Viseme:

    value: 13
    time: 0.2322
    duration: 0.0348
```

This allows clients such as Vizij to use the viseme stream directly without having to perform phoneme-to-viseme conversion themselves.

### Viseme modes

The `/tts/visemes` behavior depends on the configured `viseme_mode`.

#### Normal mode

```text
viseme_mode: normal
```

EmojiVoice phoneme alignment is used to generate the corresponding visemes.

Visemes are published progressively during audio playback.

#### Static mode

```text
viseme_mode: static
```

No `/tts/visemes` messages are published.

The TTS audio and `/tts/phoneme` stream continue to operate normally.

This mode is intended for cases where the face should remain static or where another component controls facial animation.

#### Open/close mode

```text
viseme_mode: open_close
```

The aligned phoneme sequence is replaced by a generated alternating mouth sequence.

The sequence alternates between:

```text
OH  = 13
SIL = 0
```

with a fixed interval during speech.

For example:

```text
time: 0.12  value: 13
time: 0.24  value: 0
time: 0.36  value: 13
time: 0.48  value: 0
...
```

The open/close sequence lasts for the duration of the generated audio.

---

# 16. Real-time playback synchronization

The phoneme and viseme streams are generated and published **during audio playback**.

The sequence is:

```text
Receive /tts/say
        │
        ▼
Parse text + voice expression
        │
        ▼
Generate audio with EmojiVoice
        │
        ├───────────────┐
        ▼               │
Start audio playback   │
        │               │
        ▼               │
Measure playback time  │
        │               │
        ├── /tts/phoneme
        │
        └── /tts/visemes
                │
                ▼
              Vizij
                │
                ▼
           Face animation
```

The ROS node records the playback start time immediately after starting the audio:

```python
playback_start = time.monotonic()
```

During playback, the elapsed time is compared with the alignment timestamp of the next phoneme.

A phoneme is published when its aligned timestamp is reached:

```python
elapsed = time.monotonic() - playback_start
```

The corresponding viseme is published at the same time when viseme publication is enabled.

Therefore, Vizij does not need to reconstruct the speech timing from `/tts/speech`.

Instead, Vizij can subscribe directly to:

```text
/tts/visemes
```

and update the face as the viseme messages arrive.

---

# 17. Vizij integration

Vizij uses the `/tts/visemes` topic as the real-time facial animation stream.

The intended architecture is:

```text
                ROS 2
                  │
                  │ /tts/say
                  ▼
          ┌─────────────────┐
          │  emojivoice_tts │
          └─────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
      Speaker         /tts/visemes
                           │
                           ▼
                      Vizij Rust
                           │
                           ▼
                      Face shapes
```

The TTS node remains responsible for:

* text processing
* voice-expression parsing
* EmojiVoice synthesis
* audio playback
* phoneme alignment
* phoneme publication
* viseme conversion
* viseme publication

Vizij is responsible for:

* receiving the ROS 2 viseme messages
* mapping ROS viseme values to the corresponding face shapes
* applying the face animation

Vizij should **not generate a second copy of the audio** from the TTS service.

The EmojiVoice ROS node is the component responsible for audio playback.

This avoids playing the same utterance twice and ensures that the face animation is synchronized with the audio playback controlled by the TTS node.

---

# 18. Final silence

In `normal` and `open_close` modes, a final `SIL` viseme is used to return the face to its neutral/resting mouth shape when an utterance finishes.

The sequence is therefore:

```text
speech

  │

  ├── viseme

  ├── viseme

  ├── viseme

  ├── ...

  └── SIL
```

This prevents the face from remaining on the last spoken mouth shape after the utterance has finished.

The `SIL` value is:

```text
Viseme.SIL = 0
```

In `static` mode, **no final `SIL` viseme is published**, because `/tts/visemes` publication is disabled entirely.

---

# 19. Playback delay

The current implementation contains a 2.0 second delay immediately before playback:

```python
time.sleep(2.0)
```

This is currently used for the robot setup.

The delay occurs before `play_audio()` starts the audio and before the playback clock is initialized.

Therefore, the 2.0 second delay is **not included in the viseme timestamps**.

The current playback timing starts when the audio is actually started.

This delay may be removed or adjusted depending on the target robot/system.

---

# 20. Important files

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
* `/tts/phoneme`
* `/tts/visemes`
* `/robot_speaking`
* communicating with the EmojiVoice worker
* phoneme → viseme conversion
* viseme mode handling

### `emojivoice_worker.py`

Runs with the EmojiVoice Python 3.11 environment.

Responsible for:

* Matcha-TTS
* HiFiGAN
* speaker ID selection
* audio generation
* phoneme alignment
* returning generated audio
* returning aligned phonemes

### `config/emojivoice.yaml`

Contains machine-specific configuration:

* EmojiVoice Python interpreter
* EmojiVoice Matcha-TTS model path
* default viseme mode

### `launch/emojivoice_tts.launch.py`

Starts `tts_node`, loads the EmojiVoice configuration, and exposes the `viseme_mode` launch argument.

---

# 21. Python environments

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

# 22. Testing the viseme stream

After building the package and starting the TTS node, first check that the topics exist:

```bash
source ~/vizij_project/ros_ws/install/setup.bash

ros2 topic list | grep /tts
```

Expected topics include:

```text
/tts/say
/tts/speech
/tts/phoneme
/tts/visemes
```

### Check the current viseme mode

```bash
ros2 param get /tts_node viseme_mode
```

### Test phonemes

In one terminal:

```bash
source ~/vizij_project/ros_ws/install/setup.bash

RMW_IMPLEMENTATION=rmw_zenoh_cpp ros2 topic echo /tts/phoneme
```

Then send speech from another terminal.

### Test normal visemes

Set:

```bash
ros2 param set /tts_node viseme_mode normal
```

Then:

```bash
RMW_IMPLEMENTATION=rmw_zenoh_cpp ros2 topic echo /tts/visemes
```

Send:

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "Hello, I am a talking face."}'
```

The `/tts/visemes` messages should appear progressively during playback.

### Test static mode

Set:

```bash
ros2 param set /tts_node viseme_mode static
```

Then monitor:

```bash
RMW_IMPLEMENTATION=rmw_zenoh_cpp ros2 topic echo /tts/visemes
```

Send speech.

No `/tts/visemes` messages should be published in this mode.

The audio and `/tts/phoneme` stream should continue normally.

### Test open/close mode

Set:

```bash
ros2 param set /tts_node viseme_mode open_close
```

Then monitor:

```bash
RMW_IMPLEMENTATION=rmw_zenoh_cpp ros2 topic echo /tts/visemes
```

Send:

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "Hello, I am a talking face."}'
```

The viseme stream should alternate between:

```text
value: 13
value: 0
value: 13
value: 0
...
```

where:

```text
13 = OH
0  = SIL
```

The sequence is generated according to the duration of the generated audio.

---

# 23. Troubleshooting

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

### Check the current viseme mode

```bash
ros2 param get /tts_node viseme_mode
```

To change it without restarting the node:

```bash
ros2 param set /tts_node viseme_mode normal
```

```bash
ros2 param set /tts_node viseme_mode static
```

```bash
ros2 param set /tts_node viseme_mode open_close
```

The selected mode applies to subsequent speech.

### Check speech metadata

```bash
ros2 topic echo /tts/speech
```

### Check phoneme alignment

```bash
ros2 topic echo /tts/phoneme
```

### Check viseme alignment

```bash
ros2 topic echo /tts/visemes
```

### Check the message interfaces

```bash
ros2 interface show hri_msgs/msg/Phoneme
```

and:

```bash
ros2 interface show hri_msgs/msg/Visemes
```

### Test an expression directly

```bash
ros2 action send_goal /tts/say communication_skills/action/Say \
'{meta: {priority: 128}, input: "<set expression(😍)>Hello, how are you?</expression>"}' \
--feedback
```

Expected logs include:

```text
Voice expression detected: '😍' -> EmojiVoice emotion 107

Clean speech text: 'Hello, how are you?'

Speech emotion: '107'
```

and word-level feedback during playback.

---

# 24. Testing

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
