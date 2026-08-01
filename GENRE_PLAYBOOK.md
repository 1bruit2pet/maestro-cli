# Maestro & Claw-DAW Genre-Specific Orchestration Playbook
> [!IMPORTANT]
> This reference playbook defines chord progressions, rhythmic syncopation rules, sound selection, and arrangement patterns for the major musical genres. AI agents must use this playbook to write professional scripts for `claw-daw` rendering.

---

## 1. Afrobeat

*   **Tempo**: $95 - 120\text{ BPM}$
*   **Key Signature**: Major keys (G, C, D) or minor keys (Am, Dm) playing modal progressions.
*   **Progressions**: Highly repetitive, groove-centric 2-bar loops:
    *   `i - iv - v - iv` (e.g., in Am: `Am - Dm - Em - Dm`)
    *   `I - IV - V - IV` (e.g., `C - F - G - F`)
*   **Sound Selection**:
    *   **Drums**: Trap/Acoustic hybrid kits (accenting rimshots and shakers).
    *   **Bass**: Subby 808 or synth bass carrying a driving syncopated pattern.
    *   **Melody/Chords**: Clean highlife electric guitars (skank style), bright brass stabs, marimba/kalimba.
*   **Rhythmic Code Mapping**:
    *   *Groove*: The drum beat relies heavily on the **three-stroke syncopation** (3:2 Clave).
    *   *Kick*: Hits on beat 1 and the upbeat of beat 2 (`0:0` and `1:2`).
    *   *Snare/Rim*: Snare hits on the upbeat of 3 (`3:2`).
    *   *Perception*: Perpetual shaker/tambourine running sixteenth notes.

---

## 2. Trap

*   **Tempo**: $130 - 160\text{ BPM}$ (often double-timed at $65 - 80\text{ BPM}$)
*   **Key Signature**: Minor keys (Fm, E minor, C# minor) for dark, moody energy.
*   **Progressions**: Dark, minimal, shifting by half-steps:
    *   `i - VI` (e.g., in Fm: `Fm - Db`)
    *   `i - ii°` (e.g., `Fm - Gdim`)
*   **Sound Selection**:
    *   **Drums**: High-pitched snappy snares (pitch `38` or custom rim), rolling hi-hats, hard-hitting kicks.
    *   **Bass**: Long, sliding **808 bass** (pitch register `low`, sliding frequencies).
    *   **Melody/Chords**: Plucky bells, detuned dark piano, minor string pads.
*   **Rhythmic Code Mapping**:
    *   *Groove*: Sparse and heavy.
    *   *Hi-Hats*: Rapid rolls. Alternate sixteenth notes with triplets (`32nd notes` using tick subdivisions like `0:0:60`, `0:0:120`, `0:0:180`).
    *   *Snare*: Heavy accents strictly on beat 3.
    *   *808 Bass*: Locks with the kick but slides upwards (slide notes with short duration overlapping the next note's pitch).

---

## 3. Electro (French House / Future Bass)

*   **Tempo**: $120 - 128\text{ BPM}$
*   **Key Signature**: Major or minor keys depending on energy (Am, F major, G major).
*   **Progressions**: Sweeping four-chord loops:
    *   `VI - VII - i - v` (e.g., in Am: `F - G - Am - Em`)
    *   `IV - V - vi - iii` (e.g., `F - G - Am - Em`)
*   **Sound Selection**:
    *   **Drums**: Punchy electronic 909-style kick, wide clap/snare, open hi-hats.
    *   **Bass**: Sawtooth synth bass, sidechained (compressed/ducked on beat 1/3).
    *   **Melody/Chords**: Bright synth pads (Program 89 or custom saw synth), vocal chops.
*   **Rhythmic Code Mapping**:
    *   *Groove*: **Four-on-the-floor**.
    *   *Kick*: Hits strictly on every beat (`0:0`, `1:0`, `2:0`, `3:0`).
    *   *Clap/Snare*: Hits on beats 2 and 4 (`1:0` and `3:0`).
    *   *Open Hi-Hat*: Hits on offbeats (`0:2`, `1:2`, `2:2`, `3:2`) to create upbeat energy.

---

## 4. Country

*   **Tempo**: $75 - 110\text{ BPM}$
*   **Key Signature**: Strictly Major keys (G, D, C, A major).
*   **Progressions**: Open, narrative, major progressions:
    *   `I - IV - V - I` (e.g., in G: `G - C - D - G`)
    *   `I - V - vi - IV` (e.g., `G - D - Em - C`)
*   **Sound Selection**:
    *   **Drums**: Soft acoustic kit (brushes style for slow ballads).
    *   **Bass**: Acoustic double bass or clean electric bass.
    *   **Melody/Chords**: Acoustic steel guitar, fiddle/violin (prog 40), pedal steel, banjo.
*   **Rhythmic Code Mapping**:
    *   *Groove*: "Boom-Chick" pattern.
    *   *Bass*: Alternates root note on beat 1 and fifth on beat 3.
    *   *Acoustic Guitar/Banjo*: Continuous fingerpicking or rhythmic strumming using sixteenth note rolls.
    *   *Snare*: Quiet brush hits on beats 2 and 4.

---

## 5. Folk

*   **Tempo**: $70 - 100\text{ BPM}$
*   **Key Signature**: Major or natural minor keys (G major, C major, E minor).
*   **Progressions**: Simple, acoustic progressions:
    *   `I - vi - IV - I` (e.g., in C: `C - Am - F - C`)
    *   `i - VII - VI - VII` (e.g., in Em: `Em - D - C - D`)
*   **Sound Selection**:
    *   **Drums**: Ambient room percussion, cajon, frame drums (avoid heavy snare and electronic kicks).
    *   **Bass**: Warm electric or upright bass.
    *   **Melody/Chords**: Acoustic nylon guitar (prog 24), cello (prog 42), violin (prog 40).
*   **Rhythmic Code Mapping**:
    *   *Acoustic Guitar*: Play **Travis picking** (thumb alternates bass notes while fingers pluck melody lines).
    *   *Groove*: Relaxed, behind-the-beat velocity humanization.

---

## 6. R&B (Contemporary Neo-Soul)

*   **Tempo**: $70 - 95\text{ BPM}$
*   **Key Signature**: Minor keys or flat keys (Db major, Bb minor, Eb minor).
*   **Progressions**: Lush jazz seventh and ninth chord progressions:
    *   `ii9 - V13 - Imaj9 - VI7b9` (e.g., in Db: `Ebm9 - Ab13 - Dbmaj9 - Bb7b9`)
    *   `IVmaj9 - iii7 - ii7 - Imaj7`
*   **Sound Selection**:
    *   **Drums**: Hip-hop/Neo-Soul hybrid (soft snare, warm kick).
    *   **Bass**: Smooth electric bass (warm tone, prog 33 or 34).
    *   **Melody/Chords**: Rhodes electric piano (prog 4), warm synth pads (prog 89).
*   **Rhythmic Code Mapping**:
    *   *Groove*: Heavy swing and micro-timing offsets.
    *   *Rhodes Chords*: Roll the chord note timings slightly (e.g., note 1 at `0:0`, note 2 at `0:0:60`, note 3 at `0:0:120`) to simulate hands sweeping the keyboard.
    *   *Hi-Hats*: Lay back (delay hats by $+20$ to $+30$ ticks on offbeats).

---

## 7. Hip-Hop (Boom Bap / Lo-Fi)

*   **Tempo**: $80 - 95\text{ BPM}$
*   **Key Signature**: Minor keys (Am, Dm, Gm).
*   **Progressions**: Jazzy, sampled-style loops (often 2 or 4 bars):
    *   `ii7 - Imaj7` (e.g., in C: `Dm7 - Cmaj7`)
    *   `i - iv - VII - III` (e.g., in Am: `Am - Dm - G - C`)
*   **Sound Selection**:
    *   **Drums**: Gritty acoustic drums (MPC sampler vinyl style), fat kick, dry snare.
    *   **Bass**: Subby upright bass or synth sine bass.
    *   **Melody/Chords**: Rhodes, electric piano, trumpet/saxophone riffs, vinyl crackle effects.
*   **Rhythmic Code Mapping**:
    *   *Groove*: "Drunk" or unquantized swing.
    *   *Kick*: Heavy syncopation, hitting right before beat 3 (`1:3` or `1:3:120`).
    *   *Snare*: Solid on beat 2 and 4, occasionally layered with a snap.
