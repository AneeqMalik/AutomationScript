from flask import Flask, jsonify, request
import json
import requests
import openai
import time
from flask_cors import CORS
from flask_ngrok import run_with_ngrok
import os

app = Flask(__name__)
run_with_ngrok(app)
CORS(app, origins="*")

CHAT_GPT_API_KEY = 'GPT_KEY_ADD'

MONSTER_API_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImE3MjY3ZWUzZWMyOTMxZThkZjM2OTFlNzFhMDEwM2VhIiwiY3JlYXRlZF9hdCI6IjIwMjMtMDktMDhUMTE6NDI6MjMuODkxMDE0In0.531Bc7PlsegG3OrcAZoknua2Hd9_dyx53DUfeMeZoIg'

openai.api_key = CHAT_GPT_API_KEY


def send_wav_to_whisper(file):
    url = "https://api.monsterapi.ai/v1/generate/whisper"
    print(file)
    file_format = file
    files = {"file": (file, open(file, "rb"), f"audio/{file_format[-3:]}")}
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {MONSTER_API_TOKEN}"
    }
    try:
        response = requests.post(url, files=files, headers=headers)

        response_data = json.loads(response.text)
        process_id = response_data.get("process_id")
        print(f"Process ID: {process_id}")

        while True:
            trans_text = get_text_from_whisper(process_id)
            text_data = json.loads(trans_text)
            status = text_data.get("status")

            if status == "IN_PROGRESS":
                print("Processing in progress. Waiting for completion...")
                time.sleep(5)  # Wait for 5 seconds before checking again
            else:
                if status == "COMPLETED":
                    print("Processing completed.")
                else:
                    print(f"Processing status: {status}")

                result = text_data.get("result")
                return result

    except Exception as e:
        return f"Error: {str(e)}"


def get_text_from_whisper(process_id):
    url = f"https://api.monsterapi.ai/v1/status/{process_id}"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {MONSTER_API_TOKEN}"
    }

    response = requests.get(url, headers=headers)

    return response.text


def gpt_response(input_text):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": input_text}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
    )
    assistant_response = response['choices'][0]['message']['content']
    return assistant_response


def bark_audio_generate(text, bark_url):
    bark_url = bark_url
    data_to_send = {
        'text': f'{text}'
    }
    response = requests.post(bark_url, json=data_to_send)
    return response


def bark_audio_prompt_generate(text, bark_url, voice):
    bark_url = bark_url
    data_to_send = {
        'text': f'{text}',
        'history_prompt': voice
    }
    response = requests.post(bark_url, json=data_to_send)
    return response


@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    try:
        file = request.files['audio']
        bark_url = request.form['bark_url']
        voice = request.form["voice"]
        if file:
            try:
                timestamp = int(time.time())
                new_filename = f"{timestamp}_{file.filename}"
                file.save(new_filename)
                text = send_wav_to_whisper(new_filename)
                prompt = text["text"]
                response = gpt_response(prompt)
                if voice == "":
                    audio = bark_audio_generate(response, bark_url)
                else:
                    audio = bark_audio_prompt_generate(
                        response, bark_url, voice)
                result = audio.json()
                audio_url = result.get('audio_url')
                os.remove(new_filename)
                return audio_url
            except Exception as e:
                return f"Error: {str(e)}"
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run()
