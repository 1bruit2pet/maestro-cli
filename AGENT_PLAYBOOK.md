# Maestro & Claw-DAW Advanced Music Theory Playbook
> [!IMPORTANT]
> This document serves as the core reference playbook for any AI agent orchestrating music within `maestro-cli` and rendering via `claw-daw`. Read and apply these music theory rules and syntax mappings to write professional, coherent, and highly emotional pieces.

---

## 1. Core Music Theory Rules

To elevate compositions from simple loops to professional arrangements, respect the following guidelines:

### A. Harmonic Progressions & Scale Degrees
* **Gothic/Epic Doom Moods**: Favor minor keys (specifically **D minor**, **A minor**, or **F# minor**). Use classical gothic progressions:
  * `i - VI - VII - v` (e.g., in Dm: `Dm - Bb - C - Am`)
  * `i - iv - VII - III` (e.g., `Dm - Gm - C - F`)
  * Inject the dramatic Picardy Third (`I` major at the very end of a minor piece).
* **Afrobeat/Gospel Swing Moods**: Use major keys (specifically **Db major**, **Gb major**, or **Ab major**).
  * Use jazzier progressions: `ii7 - V7 - Imaj7 - VI7` or `IVmaj7 - iii7 - ii7 - Imaj7`.

### B. Professional Chord Voicings (No Block Chords)
Never stack notes in basic triads (`Root-Third-Fifth`) close together in the low registers.
* **Bass**: Only play the root note or fifth in the low octave ($C1$ to $G2$, MIDI pitches $24$ to $43$).
* **Keyboard/Rhodes**: Use **drop-2 voicings** or spread chords across octaves.
  * *Example (Dm7)*: Instead of `[50, 53, 57, 60]` close together, play:
    * Left hand: `50` (Root)
    * Right hand: `57` (Fifth), `60` (Seventh), `65` (Third, octave up).
* **Sustained Strings Ensemble**: Use 3-note close voicings in the mid-high register ($C4$ to $C5$) to act as a gluing pad, leaving the bass and lead frequencies clear.

### C. Melodic Fluidity & Counterpoint
* **Violin/Lead Soloing**: Must be lyric and legato.
  * Use **step-wise motion** (moving to adjacent notes in the scale) $80\%$ of the time.
  * Use **leaps** (fourths, fifths, octaves) only on strong beats to create dramatic tension, followed immediately by step-wise resolution in the opposite direction.
* **Electric Guitar Solos**: To keep synthesized guitars fluid:
  * Avoid dry, fast sixteenth-note jumps.
  * Write notes with longer durations (e.g., quarter notes `0:1:0` or half notes `0:2:0`) that overlap slightly to trigger natural legato envelopes.
* **Counterpoint**: If the Violin goes up, the Electric Guitar countermelody or Cello bassline should move down (**contrary motion**).

---

## 2. Advanced Groove Design (The Drums)

To build a professional humanized groove, never place notes only on grid lines with identical velocities.

* **Hi-Hat Dynamics**: Accent the downbeats (velocity $95$) and quiet the offbeats (velocity $70-75$).
* **Micro-timing**: Shift offbeat notes (e.g., Hi-Hats on tick `240`) by a tiny delay ($+10$ to $+15$ ticks) to simulate natural human swing.
* **Ghost Notes**: Soft snare hits (pitches like `38` at velocity $45-55$) placed right before main beats add rolling energy.
* **Transitions/Fills**: Always write a fill in the last bar of a section (e.g. bar 7 of an 8-bar section) using tom rolls climbing down from high to low to signal arrangement changes.

---

## 3. Claw-DAW Instruction Syntax Reference

Translate the music theory directly into `claw-daw` txt script commands using this structure:

### A. Initialization & Tracks
```text
new_project <project_id> <bpm>
set_swing <amount_0_to_100>

# Instruments Map
# 0 = Basic GM Synth / Acoustic Bass / Drums
# 4 = Rhodes / Electric Piano
# 24 = Nylon Acoustic Guitar
# 29 = Overdriven Electric Guitar
# 40 = Solo Violin (Strings Lead)
# 48 = String Ensemble Pad
# 52 = Gothic Choir
# 60 = French Horn / Brass

add_track keys 4
set_volume 0 100
set_pan 0 64

add_track drums 0
set_kit 1 gm_basic
```

### B. Creating and Placing Patterns
Patterns are created per track and placed on the timeline (`bar:beat`).
```text
# Syntax: new_pattern <track_index> <pattern_name> <duration_bars>:0
new_pattern 0 pat_keys_intro 8:0

# Syntax: add_note_pat <track_index> <pattern_name> <midi_pitch/drum_key> <bar>:<beat>:<tick> <duration_bars>:<beats>:<ticks> <velocity>
# Place a Dm chord sweep at Bar 0, beat 0:
add_note_pat 0 pat_keys_intro 50 0:0:0 1:0:0 90
add_note_pat 0 pat_keys_intro 57 0:0:120 1:0:0 85
add_note_pat 0 pat_keys_intro 62 0:0:240 1:0:0 85

# Syntax: place_pattern <track_index> <pattern_name> <start_bar>:0
place_pattern 0 pat_keys_intro 0:0
```

---

## 4. How the AI Agent Must Act

When a user requests a style, prompt, or jam:
1. **Initialize the Project**: `maestro init <project_id> --style <style> --bpm <bpm> --key <key>`
2. **Translate to Script**: Edit [claw_daw_adapter.py](file:///root/agy-test/maestro-cli/src/maestro_cli/hosts/claw_daw_adapter.py) to map the instruments and program the dynamic, humanized note placement loops.
3. **Trigger the Render**: `maestro -p <project_id> render`
4. **Export**: Copy outputs from `out/` to `/sdcard/Download/<project_id>/`.
