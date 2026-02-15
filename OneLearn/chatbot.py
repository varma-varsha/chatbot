# chatbot.py
import json
import spacy
import random
from code_highlighter import *


class Chatbot:
    def __init__(self, knowledge_base_path):
        # Load knowledge base
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            self.knowledge_base = json.load(f)

        # Load spaCy model
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            print("Downloading spaCy English model...")
            spacy.cli.download('en_core_web_sm')
            self.nlp = spacy.load('en_core_web_sm')

        # Pre-generate highlighted code
        self.highlighted_codes = generate_language_code_highlights()

        # Initialize states dictionary to store states for different users
        self.user_states = {}

    def get_user_state(self, user_id):
        """Get or create state for a specific user"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'awaiting_course_confirmation': False,
                'selected_language': None,
                'last_response': None
            }
        return self.user_states[user_id]

    def process_message(self, user_message, user_id):
        # Get state for this user
        state = self.get_user_state(user_id)

        # Split message into lines to handle multi-line input
        message_lines = user_message.strip().split('\n')

        # Process each line that appears to be user input
        for line in message_lines:
            # Skip empty lines or lines that look like code/system output
            if not line.strip() or line.startswith('```') or ':' in line[:20]:
                continue

            # Process actual user input
            response = self._process_single_message(line.strip(), state)
            state['last_response'] = response

        # Return the last processed response
        return state['last_response']

    def _process_single_message(self, user_message, state):
        # Handle course confirmation if we're awaiting it
        if state['awaiting_course_confirmation']:
            if "yes" in user_message.lower():
                response = {
                    'response': f"Great! Starting the course on {state['selected_language']}.",
                    'start_course': True,
                    'language': state['selected_language']
                }
                # Reset state after handling the response
                self._reset_state(state)
                return response
            elif "no" in user_message.lower():
                # Reset state and provide a response
                self._reset_state(state)
                return "No problem! Let me know if you'd like to learn about something else."

        # Check if the message contains a language course query
        for lang in self.knowledge_base['programming_languages']:
            if lang['language'].lower() in user_message.lower() and any(
                    keyword in user_message.lower() for keyword in ['learn', 'start', 'begin', 'tutorial']):
                # Set state to await confirmation
                state['awaiting_course_confirmation'] = True
                state['selected_language'] = lang['language']

                return {
                    'response': f"Language: {lang['language']}\n\nDescription: {lang['description']}",
                    'language': lang['language'],
                    'code': self.highlighted_codes[lang['language']],
                    'follow_up': f"Would you like to start a course on {lang['language']}? If yes, we'll proceed with course cards.",
                    'course_data': lang
                }

        # Check bot info questions
        for qa in self.knowledge_base['bot_info']:
            if self._check_similarity(user_message, qa['question']):
                return qa['response']

        # Default response if no match is found
        return "I'm sorry, I don't have a specific response for that query. Could you rephrase or ask something else?"

    def _check_similarity(self, message1, message2, threshold=0.6):
        # Use spaCy for semantic similarity
        doc1 = self.nlp(message1.lower())
        doc2 = self.nlp(message2.lower())
        return doc1.similarity(doc2) > threshold

    def _reset_state(self, state):
        """Reset the state to default values"""
        state.update({
            'awaiting_course_confirmation': False,
            'selected_language': None,
            'last_response': None
        })