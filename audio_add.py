from faster_whisper import WhisperModel
import sounddevice as sd
from scipy.io.wavfile import write
import edge_tts
from pydub import AudioSegment
import numpy as np
from pydub.silence import detect_leading_silence



def speech_to_text():


    duration = 5
    fs = 44100

    print("Recording...")

    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1, device=0, dtype="int16")

    sd.wait()

    print("Recording Done.")

    write("faud.wav", fs, myrecording)

    print("Audio saved.")


    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )


    segments, info = model.transcribe("faud.wav")

    text = ""

    for segment in segments:
        text += segment.text

    print("Saved text: ", text)

    return text    


async def audio_gen(all_res, filename):

    comm = edge_tts.Communicate(all_res, "en-US-AriaNeural")

    await comm.save(filename)

    return filename


def text_to_speech(file_path):

    audio = AudioSegment.from_mp3(file_path)

    samples = np.array(audio.get_array_of_samples())

    if audio.channels == 2:
        samples = samples.reshape((-1, 2))

    sd.play(samples, samplerate=audio.frame_rate)
    sd.wait()


     
def trim_silence(file_path):

    audio = AudioSegment.from_mp3(file_path)

    start_trim = detect_leading_silence(audio)
    end_trim = detect_leading_silence(audio.reverse())

    trimmed = audio[start_trim:len(audio) - end_trim]

    trimmed.export(file_path, format="mp3")
