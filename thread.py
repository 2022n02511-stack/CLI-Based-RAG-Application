import threading
import queue
import re
from audio_add import audio_gen, text_to_speech, trim_silence
import asyncio
import os
from strean_llm import stream_llm

sentence_queue = queue.Queue()

all_res = ""

def producer(response):

    global all_res

    buffer = ""
    chunk_number = 0

    for content in response:

        if not content:

            continue

        buffer += content
        all_res += content

        match = re.search(r'([.!?])(\s|$)', buffer)
    
        if match:
            sentence_to_speak = buffer[:match.end()].strip()
            buffer = buffer[match.end():]

            chunk_number += 1
            filename = f"chunk_{chunk_number}.mp3"

            aud_file = asyncio.run(audio_gen(sentence_to_speak, filename))

            trim_silence(aud_file)

            sentence_queue.put((sentence_to_speak, aud_file))

    if buffer.strip():

        chunk_number += 1
        filename = f"chunk_{chunk_number}.mp3"

        aud_file = asyncio.run(audio_gen(buffer.strip(), filename))

        trim_silence(aud_file)

        sentence_queue.put((buffer.strip(), aud_file))

    sentence_queue.put(None)       

def consumer():

    while True:
        item = sentence_queue.get()

        if item is None:
            break

        try:
            sentence, aud_file = item 
            print(sentence, end=" ", flush=True)
            text_to_speech(aud_file)
            os.remove(aud_file)
        except Exception as e:
            print(f"Playback failed: {e}")

def stream_tts(provider, system_prompt, prompt):

    global all_res

    all_res = ""

    response = stream_llm(provider, system_prompt, prompt)

    producer_thread = threading.Thread(target=producer, args=(response,))
    consumer_thread = threading.Thread(target=consumer)

    producer_thread.start()
    consumer_thread.start()

    producer_thread.join()
    consumer_thread.join()

    return all_res