# 🎧 Japanese Minimal Pairs Practice

A streamlit-based web application for practicing Japanese minimal pairs using the **odd-one-out listening method**. This tool helps you train your ear to distinguish subtle pronunciation differences in Japanese through blind listening exercises with spaced repetition.

---

## 📖 Method & Rationale

### What are Minimal Pairs?
Minimal pairs are words that differ by only one sound, such as:
- **らか (落下)** vs **りゃく (略)** — distinguishing /ra/ from /rya/
- **こうほ (候補)** vs **こうほう (航法)** — recognizing long vowels

### The Odd-One-Out Method
Each practice session presents you with **4 audio clips**:
- 3 clips of the same word (majority)
- 1 clip of a different word (odd one out)

Your task: **identify which position (1-4) sounds different**.

This method is highly effective because:
1. **Completely blind** — no visual hints, forcing active listening
2. **Multiple exposures** — you hear both words 3+ times per question
3. **Immediate feedback** — reinforces correct distinctions
4. **Spaced repetition** — difficult pairs return more frequently

### Why This Works
Based on principles from [**Fluent Forever by Gabriel Wyner**](https://fluent-forever.com/), training your ear to hear phonetic distinctions is crucial for:
- Accurate pronunciation
- Better listening comprehension
- Natural accent development
- Avoiding fossilized pronunciation errors

---

## ✨ Features

### 🎯 Smart Practice System
- **Spaced Repetition (SRS)** — Algorithm tracks your progress for each pair
- **Realistic daily targets** — Default 20 questions/day (customizable)
- **Mixed practice** — Automatically shuffles different minimal pair types to prevent monotony
- **Bonus mode** — Add 5 more questions at a time if you want to keep practicing

### 📊 Progress Tracking
- **Daily dashboard** with accuracy, questions answered, and target progress
- **Last 7 days summary** showing your consistency
- **Progress by type** with cute emoji indicators (🌟 🎵 🎧 💚 🌱)
- **Mastery levels** tracked per minimal pair

### 🎵 Audio System
- **Parallel audio generation** — Fast batch processing with progress bar
- **High-quality TTS** using [VOICEVOX](https://voicevox.hiroshiba.jp/)
- **Persistent storage** — Audio files cached locally for instant playback

### 🚩 Quality Control
- **Report issue button** for problematic audio
- **Feedback logging** saved to `audio_feedback.json` for batch review
- **Manual regeneration** option for specific files

### 💾 Local Data Storage
- All progress stored in `progress.json`
- Survives app restarts
- No cloud dependency — complete privacy
- Easy backup by copying JSON files

---

## 🚀 Setup Instructions

### Prerequisites
1. **Python 3.8+**
2. **VOICEVOX** — Download and install from [voicevox.hiroshiba.jp](https://voicevox.hiroshiba.jp/)
   - Must be running on `localhost:50021` for audio generation

### Installation

1. **Clone or download this repository**

2. **Install dependencies**
   ```bash
   pip install streamlit pandas requests
   ```
   - Download the Minimal Pairs.csv from the reddit post 

3. **Ensure VOICEVOX is running**
   - Launch the VOICEVOX application
   - Verify it's accessible at `http://localhost:50021`

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **First launch**
   - The app will automatically generate audio files for all 4,420 minimal pairs
   - This uses parallel processing and may take several minutes
   - Progress bar will show generation status
   - Audio files are saved to the `audio/` folder for future use

### File Structure
```
folder_name/
├── app.py                    # Main Streamlit application
├── Minimal Pairs.csv         # 4,420 minimal pairs dataset <- download from the reddit post
├── progress.json             # Your learning progress (auto-generated)
├── audio_feedback.json       # Audio issue reports (auto-generated)
├── audio/                    # Generated audio files (auto-generated)
│   ├── 0_A.wav
│   ├── 0_B.wav
│   └── ...
└── README.md                 # This file
```

---

## 💡 Usage Tips

### Getting Started
1. Start with the default 20 questions/day target
2. Focus on accuracy over speed
3. Use headphones for better audio quality
4. Practice consistently rather than in long sessions

### When to Report Audio Issues
- Pronunciation sounds incorrect
- Audio quality is poor or distorted
- Wrong word is being spoken
- Audio cuts off prematurely

### Managing Progress
- Use **💾 Save** button to manually backup progress
- Use **📂 Load** button if you need to restore from backup
- **🔄 Restart Session** clears all progress (use carefully!)

---

## 🔮 Future Plans

- [ ] **Multi-language support** — Add minimal pairs for other languages

---

## 📝 License & Usage

### For Educational & Individual Use Only
This application is provided free for:
- ✅ Personal language learning
- ✅ Individual practice and study
- ✅ Educational research

**Not permitted:**
- ❌ Commercial use or redistribution
- ❌ Integration into paid products/services

### Collaboration Welcome! 🤝
- **Suggestions** — Open an issue with feature requests
- **Bug reports** — Help improve the app by reporting issues
- **Contributions** — Pull requests for improvements are welcome
- **Language pairs** — Share datasets for other languages

---

## 🙏 Credits & Acknowledgments

### Methodology
- **Gabriel Wyner** — [*Fluent Forever*](https://fluent-forever.com/) book for the core methodology and minimal pair training approach

### Dataset
- **Minimal Pairs List** — 4,420 Japanese minimal pairs compiled by Reddit user u/Luxyyr (Thank you so much for the high quality list!)
  - Original post: [reddit.com/r/japaneseresources/.../list_of_4420_minimal_pairs](https://www.reddit.com/r/japaneseresources/comments/183y3yi/list_of_4420_minimal_pairs/)

### Technology
- **VOICEVOX** — High-quality Japanese text-to-speech engine
  - [voicevox.hiroshiba.jp](https://voicevox.hiroshiba.jp/)
- **Streamlit** — Web application framework
- **Python** — Programming language
- **Claude Sonnet 4.5** — AI assistant used for code generation and development

---

**Happy Learning! がんばって！ 🎌**