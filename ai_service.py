import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load environment variables (like GEMINI_API_KEY)
load_dotenv()

# Configure the Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# We use gemini-pro for text tasks
model = genai.GenerativeModel('gemini-3-flash-preview')

def generate_quick_content(topic: str, time_limit_minutes: int) -> str:
    """Generates a concise learning module for a specific time frame."""
    prompt = f"""
    Create a highly engaging, concise, and structured crash course about "{topic}".
    The user only has {time_limit_minutes} minutes to read this. 
    Format using Markdown. Include:
    1. A brief hook/introduction.
    2. The core concepts explained as simply as possible.
    3. An analogy or a real-world example.
    4. A quick summary.
    Keep it strictly within a length readable in {time_limit_minutes} minutes (assume 200 words per minute).
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating content: {e}")
        return f"Sorry, there was an error generating the course content for '{topic}'. Error: {str(e)}"

def answer_followup(context: str, question: str, history: list) -> str:
    """Answers a user's question based on the content and previous chat history."""
    
    # Format history into a string
    history_str = ""
    for entry in history:
        history_str += f"User: {entry.get('user')}\nAI: {entry.get('ai')}\n"
        
    prompt = f"""
    You are an AI learning assistant.
    The user is studying a mini-course. Here is the course content:
    ---
    {context}
    ---
    Here is your conversation history so far:
    {history_str}
    ---
    The user just asked: "{question}"
    
    Answer the user's question directly, clearly, and concisely in Markdown. 
    Base your answer primarily on the course content. If the content doesn't cover it, use your general knowledge but keep it relevant to the topic.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error in chat: {e}")
        return "Sorry, I couldn't process your question at the moment."

def generate_quiz(topic: str, content: str, history: list) -> list:
    """Generates 7 multiple choice questions covering the content and Q&A."""
    
    # Format history
    history_str = ""
    for entry in history:
        history_str += f"User: {entry.get('user')}\nAI: {entry.get('ai')}\n"
        
    prompt = f"""
    Based on the following learning material about "{topic}" and the subsequent Q&A, generate exactly 7 multiple-choice questions to test the user's understanding.
    
    Course material:
    ---
    {content}
    ---
    
    Q&A History:
    {history_str}
    ---
    
    Output strictly in Valid JSON format as a list of dictionaries. The structure MUST be exactly like this, with NO markdown formatting blocks like ```json around it:
    [
      {{
        "id": 1,
        "question": "Question text here?",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "answer": "A) ...",
        "topic_tag": "Specific sub-topic tested"
      }},
      ... (6 more)
    ]
    """
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        # Remove any potential markdown block wrappers
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        quiz_data = json.loads(result_text.strip())
        return quiz_data
    except Exception as e:
        print(f"Error generating quiz: {e}")
        print(f"Raw Response was: {response.text if 'response' in locals() else 'None'}")
        
        # Fallback dummy questions if parsing fails
        return [
            {
                "id": 1,
                "question": "Could not generate questions. Error communicating with AI.",
                "options": ["Error", "Error", "Error", "Error"],
                "answer": "Error",
                "topic_tag": "Error"
            }
        ] * 7

def evaluate_quiz(user_answers: dict, quiz_data: list) -> dict:
    """
    Evaluates the user's answers against the quiz data.
    user_answers format: {"1": "A) ...", "2": "C) ..."}
    returns report dict.
    """
    correct_count = 0
    strong_topics = set()
    focus_topics = set()
    
    for q in quiz_data:
        q_id = str(q["id"])
        user_ans = user_answers.get(q_id)
        correct_ans = q["answer"]
        topic = q["topic_tag"]
        
        if user_ans == correct_ans:
            correct_count += 1
            strong_topics.add(topic)
        else:
            focus_topics.add(topic)
            
    # Some topics might be in both if they got one right and one wrong. Prioritize focus.
    strong_topics = strong_topics - focus_topics
            
    return {
        "score": f"{correct_count} / {len(quiz_data)}",
        "percentage": round((correct_count / len(quiz_data)) * 100) if quiz_data else 0,
        "strong_topics": list(strong_topics) if strong_topics else ["Keep practicing to find your strengths!"],
        "focus_topics": list(focus_topics) if focus_topics else ["You nailed everything!"],
        "detailed_results": [
            {
                "id": q["id"],
                "question": q["question"],
                "user_answer": user_answers.get(str(q["id"]), "No answer"),
                "correct_answer": q["answer"],
                "is_correct": user_answers.get(str(q["id"])) == q["answer"]
            } for q in quiz_data
        ]
    }
