import openai
import os

def translate_text(text, target_language='en'):
    try:
        # Ensure the OpenAI API key is set in environment variables
        openai.api_key = os.getenv('OPENAI_API_KEY')

        # Using the correct method for text completion
        response = openai.Completion.create(
            model="text-davinci-002",
            prompt=f"Translate the following text to {target_language}: {text}",
            max_tokens=50  # Specify the maximum number of tokens for the translation
        )
        translation = response.choices[0].text.strip()
        return translation
    except Exception as e:
        print(f"Error in text translation: {str(e)}")
        return text
