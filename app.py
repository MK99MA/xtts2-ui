import gradio as gr
import torch
import platform
import random
import json
from pathlib import Path
from TTS.api import TTS
import uuid
import html
import soundfile as sf

def is_mac_os():
    return platform.system() == 'Darwin'

params = {
    "activate": True,
    "autoplay": True,
    "show_text": False,
    "remove_trailing_dots": False,
    "voice": "Rogger.wav",
    "language": "English",
    "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
}

# SUPPORTED_FORMATS = ['wav', 'mp3', 'flac', 'ogg']
SAMPLE_RATE = 16000
device = None

# Set the default speaker name
default_speaker_name = "Rogger"
# change default speaker name and read from config?

if is_mac_os():
    device = torch.device('cpu')
else:
    #device = torch.device('cuda:0')
    #AMD GPU and too lazy to add a coded check...
    device = torch.device('cpu')

# Load model
tts = TTS(model_name=params["model_name"]).to(device)

# # Random sentence (assuming harvard_sentences.txt is in the correct path)
# def random_sentence():
#     with open(Path("harvard_sentences.txt")) as f:
#         return random.choice(list(f))

# Voice generation function
def gen_voice(string, spk, speed, english):
    string = html.unescape(string)
    short_uuid = str(uuid.uuid4())[:8]
    string_ul = string.replace(" ","_")
    fl_name='outputs/' + string_ul + '.wav'#spk + "-" + short_uuid +'.wav'
    output_file = Path(fl_name)
    this_dir = str(Path(__file__).parent.resolve())
    tts.tts_to_file(
        text=string,
        speed=speed,
        file_path=output_file,
        speaker_wav=[f"{this_dir}/targets/" +spk + ".wav"],
        language=languages[english]
    )
    return output_file

def set_default_speaker():
    default_speaker_name = selected_speaker

def update_speakers():
    speakers = {p.stem: str(p) for p in list(Path('targets').glob("*.wav"))}
    return list(speakers.keys())

def update_dropdown(_=None, selected_speaker=default_speaker_name):
    return gr.Dropdown(choices=update_speakers(), value=selected_speaker, label="Select Speaker")

def handle_recorded_audio(audio_data, speaker_dropdown, filename = "user_entered"):
    if not audio_data:
        return speaker_dropdown

    #Use entered name or set default if empty
    #to do
    if filename_input == "":
        filename = 'user_entered'
    else:
        filename = filename_input.value
        
    
    sample_rate, audio_content = audio_data
    
    save_path = f"targets/{filename}.wav"

    # Write the audio content to a WAV file
    sf.write(save_path, audio_content, sample_rate)

    # Create a new Dropdown with the updated speakers list, including the recorded audio
    updated_dropdown = update_dropdown(selected_speaker=filename)
    return updated_dropdown


# Load the language data
with open(Path('languages.json'), encoding='utf8') as f:
    languages = json.load(f)

# Gradio Blocks interface
with gr.Blocks() as app:
    
    gr.Markdown("### TTS based Voice Cloning.")
    
    with gr.Row():
        with gr.Column():
            text_input = gr.Textbox(lines=2, label="Speechify this Text",value="Even in the darkest nights, a single spark of hope can ignite the fire of determination within us, guiding us towards a future we dare to dream.")
            speed_slider = gr.Slider(label='Speed', minimum=0.1, maximum=1.99, value=0.8, step=0.01)
            language_dropdown = gr.Dropdown(list(languages.keys()), label="Language/Accent", value="English")

            gr.Markdown("### Speaker Selection and Voice Cloning")
            
            with gr.Row():
                with gr.Column():
                    #Update Dropdown with new values
                    speaker_dropdown = update_dropdown()
                    refresh_button = gr.Button("Refresh Speakers")
                with gr.Column():
                    #Save a new speaker
                    filename_input = gr.Textbox(label="Add new Speaker", placeholder="Enter a name for your recording/upload to save as")
                    save_button = gr.Button("Save Below Recording")
            with gr.Row():
                #
                with gr.Column():
                    #Delete selected Speaker
                    delete_speaker_button = gr.Button("Delete selected speaker")
                    delete_speaker_button.click(
                        fn= #function,
                        inputs= #vars,
                        outputs= #gradio_component to use)
                #
                with gr.Column():
                    #Set as default Speaker
                    default_speaker_button = gr.Button("Set as default speaker")
                    default_speaker_button.click(
                        fn=set_default_speaker,
                        inputs=[speaker_dropdown],
                        outputs=speaker_dropdown)
                    
                
            refresh_button.click(fn=update_dropdown, inputs=[], outputs=speaker_dropdown)

            with gr.Row():
                record_button = gr.Audio(label="Record Your Voice")
                
            save_button.click(fn=handle_recorded_audio, inputs=[record_button, speaker_dropdown, filename_input], outputs=speaker_dropdown)
            record_button.stop_recording(fn=handle_recorded_audio, inputs=[record_button, filename_input], outputs=speaker_dropdown)
            record_button.upload(fn=handle_recorded_audio, inputs=[record_button, filename_input], outputs=speaker_dropdown)
            
            submit_button = gr.Button("Convert")

        with gr.Column():
            audio_output = gr.Audio()

            with gr.Row():
                # Column for filename structure
                with gr.Column():
                    filename_struct = gr.Textbox(label="Filename structure", value = fl_name)
                with gr.Column():
                    download_input = gr.Textbox(label="Overwrite filename", placeholder="Enter a custom name for the generated audio")
            #
            with gr.Row():
                # Download Button
                download_button = gr.Button("Download", link = output_file)

    submit_button.click(
        fn=gen_voice,
        inputs=[text_input, speaker_dropdown, speed_slider, language_dropdown],
        outputs=audio_output
    )

if __name__ == "__main__":
    public = input("Launch with public URL? (Y/N)")
    if public.lower() == 'y' or public.lower() == 'yes':
        app.launch(share=True)
    else:
        app.launch()
