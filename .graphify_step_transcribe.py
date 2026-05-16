import json, os
from pathlib import Path
from graphify.transcribe import transcribe_all

detect = json.loads(Path('.graphify_detect.json').read_text(encoding='utf-8'))
video_files = detect.get('files', {}).get('video', [])
prompt = os.environ.get('GRAPHIFY_WHISPER_PROMPT', 'Use proper punctuation and paragraph breaks.')

print(f'Transcribing {len(video_files)} audio file(s)...')
transcript_paths = transcribe_all(video_files, initial_prompt=prompt)
Path('graphify-out/.graphify_transcripts.json').write_text(json.dumps(transcript_paths), encoding='utf-8')
print(f'Transcribed {len(transcript_paths)} file(s)')
