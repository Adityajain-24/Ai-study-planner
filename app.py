import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="AI Study Planner", layout="wide")
st.title("🎓 AI Adaptive Study Planner")

# Securely handle API Key
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- STEP 1: INGESTION ---
st.header("1. Upload Syllabus")
uploaded_file = st.file_uploader("Upload your course syllabus (PDF)", type="pdf")
free_hours = st.number_input("How many hours can you study per week?", min_value=1, value=10)

if uploaded_file and api_key:
    # Read PDF text
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    # Parse Syllabus with AI
    if 'syllabus_data' not in st.session_state:
        with st.spinner("Analyzing syllabus..."):
            prompt = f"Extract a list of study topics from this syllabus. Return ONLY a JSON list of strings: {text[:5000]}"
            response = model.generate_content(prompt)
            # Clean response text to ensure it's valid JSON
            cleaned_json = response.text.strip().replace("```json", "").replace("```", "")
            st.session_state.syllabus_data = json.loads(cleaned_json)
            # Initialize weights (Reinforcement Learning 'State')
            st.session_state.weights = {topic: 1.0 for topic in st.session_state.syllabus_data}

# --- STEP 2: RL-BASED SCHEDULER ---
if 'syllabus_data' in st.session_state:
    st.header("2. Your Adaptive Schedule")
    
    def calculate_schedule():
        total_w = sum(st.session_state.weights.values())
        return {t: (w/total_w) * free_hours for t, w in st.session_state.weights.items()}

    schedule = calculate_schedule()
    st.table([{"Topic": t, "Hours/Week": f"{h:.1f}"} for t, h in schedule.items()])

    # --- STEP 3: MICRO-QUIZ & RL ADJUSTMENT ---
    st.divider()
    st.header("3. Weekly Micro-Quiz")
    selected_topic = st.selectbox("Take a quiz on:", st.session_state.syllabus_data)
    
    if st.button("Generate Quiz"):
        quiz_prompt = f"Generate 1 difficult multiple choice question about {selected_topic}. Provide the question, 4 options, and the correct letter."
        st.session_state.current_quiz = model.generate_content(quiz_prompt).text
    
    if 'current_quiz' in st.session_state:
        st.write(st.session_state.current_quiz)
        score = st.slider("What was your score? (0-100)", 0, 100, 50)
        
        if st.button("Update My Schedule"):
            # Simple RL logic: If score is low, increase weight for that topic
            current_weight = st.session_state.weights[selected_topic]
            if score < 70:
                st.session_state.weights[selected_topic] += 0.5 # Reinforce
                st.success(f"Increased focus on {selected_topic}!")
            else:
                st.session_state.weights[selected_topic] = max(0.5, current_weight - 0.3)
                st.balloons()
            st.rerun()

else:
    st.info("Please upload a syllabus and enter your API key to begin.")
          
