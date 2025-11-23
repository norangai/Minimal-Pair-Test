import streamlit as st
import pandas as pd
import requests
import random
import os
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# ============================================================================
# Configuration & Constants
# ============================================================================

CSV_FILE = "Minimal Pairs.csv"
AUDIO_DIR = Path("audio")
SPEAKER_IDS = [13]
TTS_BASE_URL = "http://localhost:50021"
PROGRESS_FILE = "progress.json"
FEEDBACK_FILE = "audio_feedback.json"
DAILY_TARGET = 20  # Realistic daily target: 20 questions per day

# ============================================================================
# Local Storage Functions
# ============================================================================

def save_progress():
    """Save progress to local JSON file."""
    try:
        # Convert datetime objects to ISO format strings
        serializable_progress = {}
        for pair_id, data in st.session_state.progress.items():
            serializable_progress[pair_id] = {
                "correct_streak": data["correct_streak"],
                "ease_factor": data["ease_factor"],
                "interval_days": data["interval_days"],
                "next_review": data["next_review"].isoformat(),
                "ever_correct": data["ever_correct"]
            }
        
        save_data = {
            "progress": serializable_progress,
            "session_correct": st.session_state.session_correct,
            "session_total": st.session_state.session_total,
            "current_streak": st.session_state.current_streak,
            "daily_stats": st.session_state.get("daily_stats", {}),
            "last_saved": datetime.now().isoformat()
        }
        
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"Failed to save progress: {e}")
        return False

def load_progress():
    """Load progress from local JSON file."""
    try:
        if not Path(PROGRESS_FILE).exists():
            return False
        
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        
        # Convert ISO format strings back to datetime objects
        loaded_progress = {}
        for pair_id, data in save_data.get("progress", {}).items():
            loaded_progress[int(pair_id)] = {
                "correct_streak": data["correct_streak"],
                "ease_factor": data["ease_factor"],
                "interval_days": data["interval_days"],
                "next_review": datetime.fromisoformat(data["next_review"]),
                "ever_correct": data["ever_correct"]
            }
        
        st.session_state.progress = loaded_progress
        st.session_state.session_correct = save_data.get("session_correct", 0)
        st.session_state.session_total = save_data.get("session_total", 0)
        st.session_state.current_streak = save_data.get("current_streak", 0)
        st.session_state.daily_stats = save_data.get("daily_stats", {})
        
        return True
    except Exception as e:
        st.error(f"Failed to load progress: {e}")
        return False

def log_audio_feedback(pair_id, word_type, issue_description):
    """Log feedback about problematic audio files."""
    try:
        # Load existing feedback
        feedback_data = []
        if Path(FEEDBACK_FILE).exists():
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        
        # Add new feedback entry
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "audio_file": f"{pair_id}_{word_type}.wav",
            "pair_id": pair_id,
            "word_type": word_type,
            "issue": issue_description
        }
        feedback_data.append(feedback_entry)
        
        # Save updated feedback
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"Failed to log feedback: {e}")
        return False

def update_daily_stats(is_correct):
    """Update daily statistics."""
    if "daily_stats" not in st.session_state:
        st.session_state.daily_stats = {}
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if today not in st.session_state.daily_stats:
        st.session_state.daily_stats[today] = {
            "questions_answered": 0,
            "correct_answers": 0,
            "started_at": datetime.now().isoformat()
        }
    
    st.session_state.daily_stats[today]["questions_answered"] += 1
    if is_correct:
        st.session_state.daily_stats[today]["correct_answers"] += 1

def get_today_stats():
    """Get today's statistics."""
    if "daily_stats" not in st.session_state:
        st.session_state.daily_stats = {}
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if today not in st.session_state.daily_stats:
        return {"questions_answered": 0, "correct_answers": 0, "accuracy": 0}
    
    stats = st.session_state.daily_stats[today]
    accuracy = int((stats["correct_answers"] / stats["questions_answered"]) * 100) if stats["questions_answered"] > 0 else 0
    
    return {
        "questions_answered": stats["questions_answered"],
        "correct_answers": stats["correct_answers"],
        "accuracy": accuracy
    }

def daily_target_reached():
    """Check if today's target has been reached."""
    today_stats = get_today_stats()
    current_target = DAILY_TARGET + st.session_state.get("extra_questions_added", 0)
    return today_stats["questions_answered"] >= current_target

def get_current_target():
    """Get the current target including any extra questions added."""
    return DAILY_TARGET + st.session_state.get("extra_questions_added", 0)

# ============================================================================
# Session State Initialization
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    if "df" not in st.session_state:
        st.session_state.df = None
    if "progress" not in st.session_state:
        st.session_state.progress = {}
    if "current_pair_id" not in st.session_state:
        st.session_state.current_pair_id = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "user_answer" not in st.session_state:
        st.session_state.user_answer = None
    if "session_correct" not in st.session_state:
        st.session_state.session_correct = 0
    if "session_total" not in st.session_state:
        st.session_state.session_total = 0
    if "current_streak" not in st.session_state:
        st.session_state.current_streak = 0
    if "progress_loaded" not in st.session_state:
        st.session_state.progress_loaded = False
        st.session_state.show_progress_loaded_msg = False
        # Try to load saved progress on first init
        if load_progress():
            st.session_state.show_progress_loaded_msg = True
        st.session_state.progress_loaded = True
    if "show_progress_loaded_msg" not in st.session_state:
        st.session_state.show_progress_loaded_msg = False
    if "show_csv_loaded_msg" not in st.session_state:
        st.session_state.show_csv_loaded_msg = False
    if "show_feedback_form" not in st.session_state:
        st.session_state.show_feedback_form = False
    if "feedback_target" not in st.session_state:
        st.session_state.feedback_target = None
    if "daily_stats" not in st.session_state:
        st.session_state.daily_stats = {}
    if "extra_questions_added" not in st.session_state:
        st.session_state.extra_questions_added = 0

# ============================================================================
# Audio Generation
# ============================================================================

def extract_first_word(text):
    """Extract the first word from comma/space/line-separated text."""
    if pd.isna(text):
        return ""
    text = str(text)
    # Split by comma, newline, or space and take first non-empty item
    for delimiter in [',', '\n', ' ']:
        parts = [p.strip() for p in text.split(delimiter) if p.strip()]
        if parts:
            return parts[0]
    return text.strip()

def generate_audio_tts(text, output_path):
    """Generate audio using VOICEVOX TTS API."""
    try:
        speaker_id = random.choice(SPEAKER_IDS)
        
        # Step 1: Text → Audio Query
        query = requests.post(
            f"{TTS_BASE_URL}/audio_query",
            params={"text": text, "speaker": speaker_id},
            timeout=10
        ).json()
        
        # Step 2: Query → WAV file
        wav = requests.post(
            f"{TTS_BASE_URL}/synthesis",
            headers={"Content-Type": "application/json"},
            params={"speaker": speaker_id},
            json=query,
            timeout=10
        )
        
        with open(output_path, "wb") as f:
            f.write(wav.content)
        return True
    except Exception as e:
        st.error(f"TTS error for '{text}': {e}")
        return False

def generate_single_audio(args):
    """Generate a single audio file (for parallel processing)."""
    pair_id, word_type, text, output_path = args
    try:
        if generate_audio_tts(text, output_path):
            return (True, pair_id, word_type)
        else:
            return (False, pair_id, word_type)
    except Exception as e:
        return (False, pair_id, word_type, str(e))

def generate_all_audio(df):
    """Generate missing audio files for all pairs with parallel processing."""
    AUDIO_DIR.mkdir(exist_ok=True)
    
    total_files = len(df) * 2
    missing_files = []
    
    # Check what's missing
    for i in range(len(df)):
        path_a = AUDIO_DIR / f"{i}_A.wav"
        path_b = AUDIO_DIR / f"{i}_B.wav"
        if not path_a.exists():
            missing_files.append((i, 'A'))
        if not path_b.exists():
            missing_files.append((i, 'B'))
    
    if not missing_files:
        st.success(f"✓ All {total_files} audio files exist")
        return True
    
    st.info(f"🎵 Generating {len(missing_files)} missing audio files in parallel...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Prepare tasks for parallel processing
    tasks = []
    for pair_id, word_type in missing_files:
        row = df.iloc[pair_id]
        
        if word_type == 'A':
            text = extract_first_word(row["Word1 Kanji"])
            output_path = AUDIO_DIR / f"{pair_id}_A.wav"
        else:
            text = extract_first_word(row["Word2 Kanji"])
            output_path = AUDIO_DIR / f"{pair_id}_B.wav"
        
        tasks.append((pair_id, word_type, text, output_path))
    
    # Process in parallel with ThreadPoolExecutor
    completed = 0
    failed = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(generate_single_audio, task): task for task in tasks}
        
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            
            if not result[0]:
                failed.append(result[1:])
            
            # Update progress
            progress_bar.progress(completed / len(missing_files))
            status_text.text(f"Generated {completed} / {len(missing_files)} files...")
    
    status_text.empty()
    
    if failed:
        st.error(f"Failed to generate {len(failed)} audio files")
        return False
    
    st.success(f"✓ Generated {len(missing_files)} audio files")
    return True

# ============================================================================
# SRS Logic (SM-2 inspired)
# ============================================================================

def init_pair_progress(pair_id):
    """Initialize progress for a pair if not exists."""
    if pair_id not in st.session_state.progress:
        st.session_state.progress[pair_id] = {
            "correct_streak": 0,
            "ease_factor": 2.5,
            "interval_days": 0,
            "next_review": datetime.now(),
            "ever_correct": False
        }

def update_progress(pair_id, is_correct):
    """Update SRS progress after answer."""
    init_pair_progress(pair_id)
    progress = st.session_state.progress[pair_id]
    
    if is_correct:
        progress["correct_streak"] += 1
        progress["ever_correct"] = True
        
        # Calculate new interval
        if progress["correct_streak"] == 1:
            interval = 1
        else:
            interval = max(1, int(progress["interval_days"] * progress["ease_factor"]))
        
        progress["interval_days"] = interval
        
        # Use minutes for intervals < 1 day, otherwise days
        if interval < 1:
            progress["next_review"] = datetime.now() + timedelta(minutes=max(1, int(interval * 1440)))
        else:
            progress["next_review"] = datetime.now() + timedelta(days=interval)
    else:
        progress["correct_streak"] = 0
        progress["interval_days"] = 0
        progress["next_review"] = datetime.now()
    
    # Auto-save progress after each answer
    save_progress()

def select_next_pair(df):
    """Select the pair with earliest next_review that's due, shuffled by type to avoid sequential order."""
    due_pairs = []
    now = datetime.now()
    
    for pair_id in range(len(df)):
        init_pair_progress(pair_id)
        progress = st.session_state.progress[pair_id]
        if progress["next_review"] <= now:
            type_name = df.iloc[pair_id]["Type"]
            due_pairs.append((pair_id, progress["next_review"], type_name))
    
    if not due_pairs:
        return None
    
    # Sort by next_review first
    due_pairs.sort(key=lambda x: x[1])
    
    # Take the most urgent pairs (within a small time window) and shuffle them by type
    earliest_time = due_pairs[0][1]
    time_window = timedelta(minutes=5)  # Consider pairs due within 5 minutes as equally urgent
    
    urgent_pairs = [p for p in due_pairs if p[1] <= earliest_time + time_window]
    
    # If there are multiple urgent pairs, prefer different type from last shown
    if len(urgent_pairs) > 1 and hasattr(st.session_state, 'last_shown_type'):
        # Try to find a pair with different type
        different_type_pairs = [p for p in urgent_pairs if p[2] != st.session_state.last_shown_type]
        if different_type_pairs:
            selected = random.choice(different_type_pairs)
        else:
            selected = random.choice(urgent_pairs)
    else:
        selected = random.choice(urgent_pairs) if len(urgent_pairs) > 1 else urgent_pairs[0]
    
    # Remember the type we just showed
    st.session_state.last_shown_type = selected[2]
    
    return selected[0]

def session_complete(df):
    """Check if session is complete: daily target reached or all pairs reviewed."""
    # Check if daily target reached
    if daily_target_reached():
        return True
    
    # Otherwise check if all pairs answered correctly and not due
    now = datetime.now()
    for pair_id in range(len(df)):
        init_pair_progress(pair_id)
        progress = st.session_state.progress[pair_id]
        if not progress["ever_correct"] or progress["next_review"] <= now:
            return False
    return True

# ============================================================================
# Question Generation
# ============================================================================

def create_question(pair_id, df):
    """Create an odd-one-out question for a pair."""
    row = df.iloc[pair_id]
    
    # Randomly choose which word is majority (3x) and which is odd (1x)
    if random.random() < 0.5:
        majority = 'A'
        odd = 'B'
    else:
        majority = 'B'
        odd = 'A'
    
    # Create sequence: 3 majority + 1 odd
    sequence = [majority, majority, majority, odd]
    random.shuffle(sequence)
    
    # Find correct answer position (1-indexed)
    correct_position = sequence.index(odd) + 1
    
    return {
        "pair_id": pair_id,
        "sequence": sequence,
        "correct_position": correct_position,
        "majority": majority,
        "odd": odd,
        "word1_kana": row["Word1 in Kana"],
        "word1_kanji": extract_first_word(row["Word1 Kanji"]),
        "word2_kana": row["Word2 in Kana"],
        "word2_kanji": extract_first_word(row["Word2 Kanji"]),
        "type": row["Type"]
    }

# ============================================================================
# Statistics
# ============================================================================

def get_statistics(df):
    """Calculate statistics by type."""
    stats = []
    
    for type_name in df["Type"].unique():
        type_pairs = df[df["Type"] == type_name].index.tolist()
        
        mastered = 0
        learning = 0
        
        for pair_id in type_pairs:
            init_pair_progress(pair_id)
            progress = st.session_state.progress[pair_id]
            
            if progress["correct_streak"] >= 3:
                mastered += 1
            elif progress["ever_correct"]:
                learning += 1
        
        total = len(type_pairs)
        progress_pct = int((mastered / total) * 100) if total > 0 else 0
        
        stats.append({
            "Type": type_name,
            "Mastered": mastered,
            "Learning": learning,
            "Total": total,
            "Progress": progress_pct
        })
    
    return pd.DataFrame(stats).sort_values("Progress", ascending=False)

# ============================================================================
# UI Components
# ============================================================================

def render_top_bar(df):
    """Render global progress bar."""
    total_pairs = len(df)
    mastered = sum(1 for i in range(total_pairs) 
                   if st.session_state.progress.get(i, {}).get("correct_streak", 0) >= 3)
    
    progress = mastered / total_pairs if total_pairs > 0 else 0
    st.progress(progress)
    st.caption(f"Total Mastery: {mastered} / {total_pairs} pairs")

def render_audio_player(position, word_type, pair_id):
    """Render a large numbered audio player button."""
    audio_path = AUDIO_DIR / f"{pair_id}_{word_type}.wav"
    
    if audio_path.exists():
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/wav")
    else:
        st.error(f"Audio file missing: {audio_path}")

def render_audio_player_with_feedback(position, word_type, pair_id, show_feedback_btn=False):
    """Render audio player with optional feedback button."""
    audio_path = AUDIO_DIR / f"{pair_id}_{word_type}.wav"
    
    if audio_path.exists():
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/wav")
        
        if show_feedback_btn:
            if st.button(f"🚩 Report Issue", key=f"feedback_{pair_id}_{word_type}_{position}", use_container_width=True):
                st.session_state.show_feedback_form = True
                st.session_state.feedback_target = (pair_id, word_type)
                st.rerun()
    else:
        st.error(f"Audio file missing: {audio_path}")

def render_question_ui(question):
    """Render the blind question interface."""
    st.markdown("### 🎧 Which one sounded different?")
    st.markdown("---")
    
    # Create 4 columns for the buttons
    cols = st.columns(4)
    
    for i, col in enumerate(cols):
        with col:
            position = i + 1
            word_type = question["sequence"][i]
            
            st.markdown(f"<h1 style='text-align: center;'>{position}</h1>", 
                       unsafe_allow_html=True)
            render_audio_player(position, word_type, question["pair_id"])
            
            if st.button(f"Select {position}", key=f"btn_{position}", 
                        use_container_width=True):
                st.session_state.user_answer = position
                st.session_state.session_total += 1
                
                is_correct = (position == question["correct_position"])
                if is_correct:
                    st.session_state.session_correct += 1
                    st.session_state.current_streak += 1
                else:
                    st.session_state.current_streak = 0
                
                update_progress(question["pair_id"], is_correct)
                update_daily_stats(is_correct)
                st.rerun()

def render_feedback_ui(question):
    """Render answer feedback."""
    user_pos = st.session_state.user_answer
    correct_pos = question["correct_position"]
    is_correct = (user_pos == correct_pos)
    
    # Result message
    if is_correct:
        st.success("✓ Correct!")
    else:
        st.error("✗ Wrong")
    
    st.markdown("---")
    
    # Show the 4 positions with highlighting
    cols = st.columns(4)
    for i, col in enumerate(cols):
        with col:
            position = i + 1
            word_type = question["sequence"][i]
            
            # Determine which word this is
            if word_type == 'A':
                word_kana = question['word1_kana']
                word_kanji = question['word1_kanji']
            else:
                word_kana = question['word2_kana']
                word_kanji = question['word2_kanji']
            
            # Color coding
            if position == correct_pos:
                bg_color = "#90EE90"  # Light green
                label = f"{position} ✓"
            elif position == user_pos:
                bg_color = "#FFB6C6"  # Light red
                label = f"{position} ✗"
            else:
                bg_color = "#F0F0F0"
                label = str(position)
            
            st.markdown(f"""
                <div style='background-color: {bg_color}; padding: 20px; 
                     border-radius: 10px; text-align: center; margin-bottom: 10px;'>
                    <h2>{label}</h2>
                    <p style='margin: 5px 0; font-size: 14px;'>{word_kana}</p>
                    <p style='margin: 0; font-size: 12px; color: #666;'>({word_kanji})</p>
                </div>
            """, unsafe_allow_html=True)
            
            render_audio_player_with_feedback(position, word_type, question["pair_id"], show_feedback_btn=True)
    
    st.markdown("---")
    
    # Show the words
    st.markdown("### 📝 The Two Words")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Word 1:** {question['word1_kana']} ({question['word1_kanji']})")
    
    with col2:
        st.markdown(f"**Word 2:** {question['word2_kana']} ({question['word2_kanji']})")
    
    st.caption(f"Type: {question['type']}")
    
    # Feedback form modal
    if st.session_state.show_feedback_form and st.session_state.feedback_target:
        pair_id, word_type = st.session_state.feedback_target
        
        st.markdown("---")
        st.markdown("### 🚩 Report Audio Issue")
        
        issue_type = st.selectbox(
            "What's the problem?",
            ["Pronunciation incorrect", "Audio quality poor", "Wrong word", "Audio cuts off", "Other"]
        )
        
        additional_notes = st.text_area("Additional notes (optional):")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit Feedback", type="primary", use_container_width=True):
                issue_desc = issue_type
                if additional_notes:
                    issue_desc += f" - {additional_notes}"
                
                if log_audio_feedback(pair_id, word_type, issue_desc):
                    st.success(f"✓ Feedback logged for {pair_id}_{word_type}.wav")
                    st.session_state.show_feedback_form = False
                    st.session_state.feedback_target = None
                    st.rerun()
        
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_feedback_form = False
                st.session_state.feedback_target = None
                st.rerun()
    
    # Next button
    if st.button("Next Question ➜", type="primary", use_container_width=True):
        st.session_state.user_answer = None
        st.session_state.current_question = None
        st.session_state.current_pair_id = None
        save_progress()  # Ensure progress is saved before moving to next question
        st.rerun()

def render_scoreboard(df):
    """Render live statistics table."""
    st.markdown("### 📊 Progress by Type")
    
    stats_df = get_statistics(df)
    
    # Format the display
    display_df = stats_df.copy()
    
    # Add cute emoji-based progress indicator
    def progress_emoji(pct):
        # Use single emoji to represent progress level
        if pct >= 90:
            return f"🌟 {pct}%"
        elif pct >= 70:
            return f"🎵 {pct}%"
        elif pct >= 50:
            return f"🎧 {pct}%"
        elif pct >= 30:
            return f"💚 {pct}%"
        else:
            return f"🌱 {pct}%"
    
    display_df["Progress"] = display_df["Progress"].apply(progress_emoji)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Overall stats
    total_pairs = len(df)
    total_mastered = sum(1 for i in range(total_pairs) 
                         if st.session_state.progress.get(i, {}).get("correct_streak", 0) >= 3)
    
    st.markdown(f"**Total mastery: {total_mastered} / {total_pairs} pairs**")

def render_daily_dashboard():
    """Render daily performance dashboard."""
    st.markdown("### 📅 Today's Progress")
    
    today_stats = get_today_stats()
    current_target = get_current_target()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Questions Today",
            f"{today_stats['questions_answered']} / {current_target}",
            delta=f"{min(today_stats['questions_answered'], current_target) - current_target}" if today_stats['questions_answered'] < current_target else "Target reached! 🎉"
        )
    
    with col2:
        st.metric(
            "Accuracy",
            f"{today_stats['accuracy']}%",
            delta=f"{today_stats['correct_answers']}/{today_stats['questions_answered']}"
        )
    
    with col3:
        progress_pct = min(today_stats['questions_answered'] / current_target, 1.0)
        st.metric(
            "Daily Target",
            f"{int(progress_pct * 100)}%"
        )
    
    # Progress bar
    st.progress(progress_pct)
    
    if daily_target_reached():
        st.success("🎉 Daily target reached! Great job! Feel free to continue or come back tomorrow.")
    else:
        remaining = current_target - today_stats['questions_answered']
        st.info(f"💪 {remaining} more questions to reach today's target!")
    
    # Last 7 days summary
    if len(st.session_state.daily_stats) > 1:
        st.markdown("#### 📊 Last 7 Days")
        
        # Get last 7 days of data
        last_7_days = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in st.session_state.daily_stats:
                stats = st.session_state.daily_stats[date]
                last_7_days.append({
                    "Date": datetime.strptime(date, "%Y-%m-%d").strftime("%m/%d"),
                    "Questions": stats["questions_answered"],
                    "Correct": stats["correct_answers"],
                    "Accuracy": f"{int((stats['correct_answers'] / stats['questions_answered']) * 100)}%" if stats["questions_answered"] > 0 else "0%"
                })
        
        if last_7_days:
            st.dataframe(pd.DataFrame(last_7_days), use_container_width=True, hide_index=True)

def render_session_complete_ui(df):
    """Render session complete screen."""
    st.balloons()
    
    today_stats = get_today_stats()
    current_target = get_current_target()
    
    if daily_target_reached():
        st.markdown("## 🎉 Congratulations!")
        st.markdown(f"### Fantastic work! You've completed {today_stats['questions_answered']} questions today!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Accuracy", f"{today_stats['accuracy']}%")
        with col2:
            st.metric("Correct Answers", f"{today_stats['correct_answers']}/{today_stats['questions_answered']}")
        
        st.markdown("---")
        
        # Show add more questions button
        st.markdown("### Want to keep going? 💪")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("➞ Add 5 More Questions", type="primary", use_container_width=True):
                st.session_state.extra_questions_added += 5
                # Reset question state to show next question
                st.session_state.user_answer = None
                st.session_state.current_question = None
                st.session_state.current_pair_id = None
                save_progress()
                st.rerun()
        
        with col2:
            if st.button("✓ Finish for Today", use_container_width=True):
                st.success("See you tomorrow! 👋")
                save_progress()
        
        # Show extra questions info if any were added
        if st.session_state.extra_questions_added > 0:
            st.info(f"🔥 Bonus mode: +{st.session_state.extra_questions_added} extra questions added! Current target: {current_target}")
    else:
        st.markdown("## 🎉 Session Complete!")
        st.markdown("You've successfully reviewed all due pairs!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Continue Practice", type="primary", use_container_width=True):
                # Reset some pairs to make them due
                for i in range(min(5, len(df))):
                    if i in st.session_state.progress:
                        st.session_state.progress[i]["next_review"] = datetime.now()
                st.rerun()
        
        with col2:
            if st.button("Finish for Today", use_container_width=True):
                st.success("See you tomorrow! 👋")
                save_progress()
    
    st.markdown("---")
    
    render_scoreboard(df)

# ============================================================================
# Main App
# ============================================================================

def main():
    st.set_page_config(
        page_title="Japanese Minimal Pairs Practice",
        page_icon="🎧",
        layout="wide"
    )
    
    # Custom CSS for minimalist Japanese design
    st.markdown("""
        <style>
        .stApp {
            background-color: #FAFAFA;
        }
        h1, h2, h3 {
            color: #2C3E50;
            font-weight: 300;
        }
        .stButton>button {
            background-color: #3498DB;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 16px;
        }
        .stButton>button:hover {
            background-color: #2980B9;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🎧 Japanese Minimal Pairs Practice")
    st.caption("Blind listening practice using the odd-one-out method")
    
    init_session_state()
    
    # Load CSV
    if st.session_state.df is None:
        try:
            st.session_state.df = pd.read_csv(CSV_FILE)
            st.session_state.show_csv_loaded_msg = True
        except Exception as e:
            st.error(f"Failed to load {CSV_FILE}: {e}")
            st.stop()
    
    # Show dismissible success messages
    if st.session_state.get("show_progress_loaded_msg", False):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.success("✓ Loaded saved progress!")
        with col2:
            if st.button("✕", key="close_progress_msg"):
                st.session_state.show_progress_loaded_msg = False
                st.rerun()
    
    if st.session_state.get("show_csv_loaded_msg", False):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.success(f"✓ Loaded {len(st.session_state.df)} pairs")
        with col2:
            if st.button("✕", key="close_csv_msg"):
                st.session_state.show_csv_loaded_msg = False
                st.rerun()
    
    df = st.session_state.df
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("## 🎛️ Controls")
        
        if st.button("🔄 Restart Session", use_container_width=True):
            st.session_state.progress = {}
            st.session_state.current_pair_id = None
            st.session_state.current_question = None
            st.session_state.user_answer = None
            st.session_state.session_correct = 0
            st.session_state.session_total = 0
            st.session_state.current_streak = 0
            st.session_state.extra_questions_added = 0
            save_progress()
            st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True):
                if save_progress():
                    st.success("Saved!")
        
        with col2:
            if st.button("📂 Load", use_container_width=True):
                if load_progress():
                    st.success("Loaded!")
                    st.rerun()
        
        with st.expander("🔧 Audio Management"):
            if st.button("Regenerate Missing Audio"):
                generate_all_audio(df)
            
            # Show feedback log count
            if Path(FEEDBACK_FILE).exists():
                try:
                    with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                        feedback_data = json.load(f)
                    st.caption(f"📝 {len(feedback_data)} audio issues reported")
                except:
                    pass
        
        st.markdown("---")
        render_daily_dashboard()
        st.markdown("---")
        render_scoreboard(df)
    
    # Generate audio on first run
    if not AUDIO_DIR.exists() or len(list(AUDIO_DIR.glob("*.wav"))) < len(df) * 2:
        with st.spinner("Checking audio files..."):
            generate_all_audio(df)
    
    st.markdown("---")
    
    # Main content area
    if session_complete(df):
        render_session_complete_ui(df)
    elif st.session_state.user_answer is not None:
        # Show feedback
        render_feedback_ui(st.session_state.current_question)
    else:
        # Generate new question if needed
        if st.session_state.current_question is None:
            next_pair_id = select_next_pair(df)
            
            if next_pair_id is None:
                render_session_complete_ui(df)
            else:
                st.session_state.current_pair_id = next_pair_id
                st.session_state.current_question = create_question(next_pair_id, df)
        
        # Show question
        if st.session_state.current_question:
            render_question_ui(st.session_state.current_question)

if __name__ == "__main__":
    main()
