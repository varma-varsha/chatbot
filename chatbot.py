import json
import spacy
from code_highlighter import *
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


class Chatbot:
    def __init__(self, knowledge_base_path):
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            self.knowledge_base = json.load(f)

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            spacy.cli.download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

        self.highlighted_codes = generate_language_code_highlights()
        self.user_states = {}

    def _generate_ai_response(self, prompt):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful programming tutor."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print("Groq Error:", e)
            return "Sorry, I'm having trouble connecting to AI services right now."


    def get_user_state(self, user_id):
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "awaiting_course_confirmation": False,
                "selected_language": None,
                "last_response": None
            }
        return self.user_states[user_id]

    def process_message(self, user_message, user_id):
        state = self.get_user_state(user_id)
        message_lines = user_message.strip().split("\n")

        for line in message_lines:
            if not line.strip() or line.startswith("```") or ":" in line[:20]:
                continue
            response = self._process_single_message(line.strip(), state)
            state["last_response"] = response

        return state["last_response"]

    def _process_single_message(self, user_message, state):
        if state["awaiting_course_confirmation"]:
            if "yes" in user_message.lower():
                response = {
                    "response": f"Great! Starting the course on {state['selected_language']}.",
                    "start_course": True,
                    "language": state["selected_language"]
                }
                self._reset_state(state)
                return response
            elif "no" in user_message.lower():
                self._reset_state(state)
                return "No problem! Let me know if you'd like to learn about something else."

        for lang in self.knowledge_base["programming_languages"]:
            if (
                lang["language"].lower() in user_message.lower()
                and any(
                    keyword in user_message.lower()
                    for keyword in ["learn", "start", "begin", "tutorial"]
                )
            ):
                state["awaiting_course_confirmation"] = True
                state["selected_language"] = lang["language"]
                return {
                    "response": f"Language: {lang['language']}\n\nDescription: {lang['description']}",
                    "language": lang["language"],
                    "code": self.highlighted_codes.get(lang["language"]),
                    "follow_up": f"Would you like to start a course on {lang['language']}? If yes, we'll proceed with course cards.",
                    "course_data": lang
                }

        for qa in self.knowledge_base["bot_info"]:
            if self._check_similarity(user_message, qa["question"]):
                return qa["response"]

        return self._generate_ai_response(user_message)

    def _check_similarity(self, message1, message2, threshold=0.6):
        doc1 = self.nlp(message1.lower())
        doc2 = self.nlp(message2.lower())
        return doc1.similarity(doc2) > threshold

    def _reset_state(self, state):
        state.update({
            "awaiting_course_confirmation": False,
            "selected_language": None,
            "last_response": None
        })
