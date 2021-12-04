import os
import yaml
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage

GOOGLE_CLOUD_STORAGE_BUCKET = "wordist-productions"

def upload_to_google_cloud_storage(audio_filename):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(GOOGLE_CLOUD_STORAGE_BUCKET)
    blob_name = os.path.basename(audio_filename)
    blob = bucket.blob(blob_name)
    if not blob.exists(storage_client):
        print(f"Uploading {audio_filename} to Google Storage Bucket")
        blob.upload_from_filename(audio_filename)

    return blob_name

def get_lyric_lines(lyrics_filename):
    with open(lyrics_filename, encoding="utf-16", mode="r") as file:
        segments = yaml.full_load(file)

    lines = []
    for segment in segments:
        lines.extend(segment["text"].split("\n"))
    return lines

def get_google_speech_subtitles(blob_name, lyric_lines):
    print("Getting speech recognition from Google Speech-to-Text API")

    speech_client = speech.SpeechClient()
    storage_uri = f"gs://{GOOGLE_CLOUD_STORAGE_BUCKET}/{blob_name}"
    audio = speech.RecognitionAudio(uri=storage_uri)

    speech_context = speech.SpeechContext(
        boost=20, # I've experimented with this boost level, but haven't seen much (if any) improvement
        phrases=lyric_lines,
    )

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        sample_rate_hertz=44100,
        language_code="en-US",
        enable_word_time_offsets=True,
        speech_contexts=[speech_context],
        audio_channel_count=1,
    )
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    return operation.result(timeout=60 * 5)

if __name__ == '__main__':
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), "../wordsmith/credentials/subtitles.json")

    # By default I'm using a mono file, but I've provided the stereo file as well
    # Note that you'll have to change the audio_channel_count to 2 if you use stereo
    vocals_only_filename = os.path.join(os.path.dirname(__file__), "resources/vocals_mono.wav")
    blob_name = upload_to_google_cloud_storage(vocals_only_filename)

    lyrics_filename = os.path.join(os.path.dirname(__file__), "resources/lyrics.yaml")
    lyric_lines = get_lyric_lines(lyrics_filename)

    # If this doesn't work on your end for some reason, I've already put the contents of this output
    # in the resources/output.txt file
    response = get_google_speech_subtitles(blob_name, lyric_lines)
    for result in response.results:
        word_infos = result.alternatives[0].words

        line = ""
        for i in range(len(word_infos)):
            line += word_infos[i].word + " "
            if i % 10 == 0:
                print(line)
                line = ""
        print(line)