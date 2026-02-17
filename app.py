import streamlit as st
import os
import google.generativeai as genai

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Long Wen - HSK1 Grammar Challenge",
    page_icon="🐲",
    layout="centered"
)

# --- 2. API Key Setup ---
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ API Key not found. Please check Render Environment Variables.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. System Prompt (English Version) ---
# This prompts the AI to act based on the student's language
SYSTEM_PROMPT = """
You are the elite HSK1 Grammar Teaching Assistant for "Long Wen Chinese School" (龙文中文学校).
Your sole purpose is to challenge students on **Unit 11 Grammar Points**.

### 🌍 LANGUAGE PROTOCOL (CRITICAL)
1. **DETECT**: Instantly identify if the student is using **English** or **Spanish**.
2. **ADAPT**: 
   - IF student uses **English**: Your entire response (feedback, explanations, next question) MUST be in **English**.
   - IF student uses **Spanish**: Your entire response (feedback, explanations, next question) MUST be in **Spanish**.

### 🎯 TEACHING RULES
1. **Active Challenger**: Do not wait for questions. Always end your turn by assigning a new **Translation Challenge** (e.g., "Translate this to Chinese: ...").
2. **Vocabulary Limit**: STRICTLY limit Chinese vocabulary to **HSK1 Unit 1-11**. Do not use words from Unit 12+.
3. **Correction Style**: 
   - If WRONG: Do not give the answer immediately. Give a hint about the grammar rule (e.g., "Time goes after the verb").
   - If RIGHT: Praise the specific grammar point used correctly (e.g., "Great job placing 'qian' at the end!"), then give the next question.

### 📚 UNIT 11 GRAMMAR SCOPE
1. **Time Expression "...前" ( ... qián)**
   - Rule: Placed AFTER the time/action (e.g., "Three days ago" -> "San tian qian").
   - Challenge: "Before 5 o'clock", "Before going home".
2. **Duration (Time Spent)**
   - Rule: Verb + Duration (e.g., "Sleep for 8 hours" -> "Shui ba ge xiaoshi"). *Note: Do not use 'le' for past tense yet, focus on 'xiang/yao' (want to).*
   - Challenge: "I want to live in Beijing for 3 years."
3. **Special Question Questions**
   - Rule: Question words do NOT move to the front.
   - Challenge: "What time do you go?", "When do you return?".
"""

# --- 4. Model Initialization (Paid Tier: 1.5 Flash) ---
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"Model configuration error: {e}")
    st.stop()

# --- 5. Chat UI Interface ---
st.title("🐲 Long Wen HSK1 Challenge")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Initial Greeting (Bilingual)
if not st.session_state.messages:
    st.info("👋 Welcome! / ¡Bienvenido! \n\nPlease type **'Hi'** (English) or **'Hola'** (Español) to start the challenge!")

# --- 6. Handle User Input ---
if prompt := st.chat_input("Type your answer here..."):
    # Display User Message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generate AI Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # Start session if needed
            if "chat_session" not in st.session_state:
                st.session_state.
