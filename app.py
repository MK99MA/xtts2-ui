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
import os

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

#GET RID OF THIS?
# Set the default speaker name
default_speaker_name = "Rogger"
def_struct = 'spk + string_ul'
fl_name = ''#'outputs/' + def_struct + '.wav'
output_file = Path(fl_name)

# Decide on Hardware to use
if is_mac_os():
	device = torch.device('cpu')
else:
	#device = torch.device('cuda:0')
	#AMD GPU and too lazy to add a coded check...
	device = torch.device('cpu')

# Load model
# Disabled for testing
#tts = TTS(model_name=params["model_name"]).to(device)

# # Random sentence (assuming harvard_sentences.txt is in the correct path)
# def random_sentence():
#	 with open(Path("harvard_sentences.txt")) as f:
#		 return random.choice(list(f))

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

# Display content of config.json
# TODO
def display_json(file_path):
    try:
        with open(file_path, 'r') as file:
            json_content = file.read()
            return json_content
    except Exception as e:
        return f"Error: {str(e)}"

# Update config with new value
def update_config(key, value):
	try:
		with open ('config.json', 'r') as jsonfile:
			data = json.load(jsonfile)
	except FileNotFoundError:
		data = {}

	data[key] = value

	with open('config.json', 'w') as jsonfile:
		json.dump(data, jsonfile, indent=2)
		#jsonfile.close()

# Get a list of .wav files in directory
def get_wav_files(folder_path):
	wav_files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
	return wav_files

# Save currently selected Speaker (dropbox) as default in config
def set_default_speaker(speaker_dropdown):
	#print(speaker_dropdown)
	sel_speaker = speaker_dropdown
	print(sel_speaker)
	update_config('default_speaker_name', sel_speaker)
	return gr.Dropdown(choices=update_speakers(), value=get_config_val('default_speaker_name'), label="Select Speaker")

# Delete currently selected Speaker (Dropbox)
def del_speaker(speaker_dropdown):
	speaker_del = speaker_dropdown
	del_path = 'targets/' + speaker_del + '.wav'
	if os.path.exists(del_path):
		os.remove(del_path)
		#Refresh Box and set default value
		return gr.Dropdown(choices=update_speakers(), value=get_config_val('default_speaker_name'), label="Select Speaker")
	else:
		print("The file does not exist: " + del_path)

# Get files in directory /targets
def update_speakers():
	speakers = {p.stem: str(p) for p in list(Path('targets').glob("*.wav"))}
	return list(speakers.keys())

def get_config_val(key):
	try:
		with open ('config.json', 'r') as jsonfile:
			data = json.load(jsonfile)
	except FileNotFoundError:
		data = {}

	conf_value = data[key]
	return conf_value

# Create Dropdown
# update_speakers () = list of voices
def update_dropdown(_=None, selected_speaker=default_speaker_name):
	return gr.Dropdown(choices=update_speakers(), value=selected_speaker, label="Select Speaker")

# Target filename Check
def modify_filename(save_path):
	if os.path.exists(save_path):
		folder, filename = os.path.split(save_path)
		name, ext = os.path.splitext(filename)

		count = 1

		while os.path.exists(f"{folder}/{name}_{count}{ext}"):
			count += 1

		save_path = f"{folder}/{name}_{count}{ext}"
		filename = f"{name}_{count}"
		#print(save_path)
		#print(filename)
	return save_path, filename

# Handle audio
def handle_recorded_audio(audio_data, speaker_dropdown, filename_input): # = "user_entered"):
	if not audio_data:
		return speaker_dropdown

	#Use entered name or set default if empty
	if filename_input == None:
		filename = 'NewVoice'
	elif filename_input == "":
		filename = 'NewVoice'
	else:
		filename = filename_input

	sample_rate, audio_content = audio_data

	# Set save path
	save_path = f"targets/{filename}.wav"

	# Check save path and modify it if needed
	if os.path.exists(save_path):
		save_path, filename = modify_filename(save_path)

	# Write the audio content to a WAV file
	sf.write(save_path, audio_content, sample_rate)

	# Create a new Dropdown with the updated speakers list, including the recorded audio
	updated_dropdown = update_dropdown(selected_speaker=filename)
	return updated_dropdown

#Check if config exists
if not os.path.isfile('config.json'):
	# Default config values for creation
	default_vals = {
		"default_speaker_name": default_speaker_name,
		"def_struct": def_struct,
		"language": "English",
		"speed": "0.8"
	}

	myJSON = json.dumps(default_vals, indent=2)

	with open ('config.json', 'w') as jsonfile:
		jsonfile.write(myJSON)

# Load the language data
with open(Path('languages.json'), encoding='utf8') as f:
	languages = json.load(f)

# Check if config is valid and Load config data
if os.path.isfile('config.json'):
	try:
		with open(Path('config.json'), encoding='utf8') as jsonfile:
			config = json.load(jsonfile)

		default_speaker_name = config['default_speaker_name']
		def_struct = config['def_struct']
		language = config['language']
		speed = config['speed']

	except json.JSONDecodeError:
		print(f"Error decoding JSON.")
	except Exception as e:
		print(f"An error occurred while loading config data: {e}")
else:
	print(f"{config_file_path} does not exist.")


# Gradio Blocks interface
with gr.Blocks() as app:
	gr.Markdown("### TTS based Voice Cloning.")

	with gr.Tab("Voice Generation"):
		with gr.Row():
			with gr.Column():
				text_input = gr.Textbox(lines=2, label="Speechify this Text",value="Even in the darkest nights, a single spark of hope can ignite the fire of determination within us, guiding us towards a future we dare to dream.")
				speed_slider = gr.Slider(label='Speed', minimum=0.1, maximum=1.99, value=0.8, step=0.01)
				with gr.Row():
					with gr.Column():
						speaker_dropdown = update_dropdown()
					with gr.Column():
						language_dropdown = gr.Dropdown(list(languages.keys()), label="Language/Accent", value="English")

				submit_button = gr.Button("Convert")
################## TODO: Clear Button?
			with gr.Column():
				audio_output = gr.Audio()

				with gr.Row():
					# Column for filename structure
					with gr.Column():
#########################TODO
						filename_struct = gr.Textbox(label="Filename structure", value = fl_name)
					with gr.Column():
#########################TODO
						download_input = gr.Textbox(label="Overwrite filename", placeholder="Enter a custom name for the generated audio")
				with gr.Row():
#####################TODO
					# Download Button
					download_button = gr.Button("Download", link = output_file)

	with gr.Tab("Voice cloning and management"):
		gr.Markdown("### Speaker Selection and Voice Cloning")

		with gr.Row():
			with gr.Column():
				#Enter new Name
				filename_input = gr.Textbox(label="Add new Speaker", placeholder="Enter a name for your recording/upload to save as")
			with gr.Column():
				speaker_dropdown = update_dropdown()

		with gr.Row():
			with gr.Column():
				#Save a new speaker
				save_button = gr.Button("Save Below Recording")
			with gr.Column():
				#Delete selected Speaker
				delete_speaker_button = gr.Button("Delete selected speaker")
				delete_speaker_button.click(
					fn=del_speaker, #function,
					inputs=[speaker_dropdown], #vars,
					outputs=speaker_dropdown) #gradio_component to use)

		with gr.Row():
			with gr.Column():
				#Set as default Speaker
				default_speaker_button = gr.Button("Set as default speaker")
				default_speaker_button.click(
					fn=set_default_speaker,
					inputs=[speaker_dropdown], #vars,
					outputs=speaker_dropdown)
			#
			with gr.Column():
				#Update Dropdown with new values
	############# Replace with Rename Function?
				refresh_button = gr.Button("Refresh Speakers")

			refresh_button.click(fn=update_dropdown, inputs=[], outputs=speaker_dropdown)

		with gr.Row():
			record_button = gr.Audio(label="Record Your Voice")

		save_button.click(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=speaker_dropdown)
		record_button.stop_recording(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=speaker_dropdown)
		record_button.upload(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=speaker_dropdown)

	with gr.Tab("Outputs"):
#########TODO
		gr.Markdown("### Output Archive - Download generated files")
		gr.FileExplorer(glob=".wav", root='Outputs', label="Select files to download", every=60.0, height = 300.0)
		gr.FileExplorer(label="Outputs", every=60.0, height = 300.0)

		output = gr.Output(label="Download")
	#def download_file(file_path):
    # Implement your logic to handle the selected file
    # For simplicity, this example assumes 'file_path' is the path to the file
#    return open(file_path, 'rb').read()

#file_explorer = gr.FileExplorer(glob="*", label="Select a file")

# Output component with a download link/button
#output = gr.Output(label="Download Link")

#def update_output(file_path):
#    if file_path:
#        file_content = download_file(file_path)
#        output.update(f'<a href="data:application/octet-stream;base64,{gr.utils.base64_encode(file_content)}" download="{file_path}">Download File</a>')

	with gr.Tab("Settings"):
#########TODO
		#json_data = display_json("/onfig.json")
		gr.JSON(label="Configuration") #, value=json_data)


	submit_button.click(
		fn=gen_voice,
		inputs=[text_input, speaker_dropdown, speed_slider, language_dropdown],
		outputs=audio_output
	)

if __name__ == "__main__":
#	public = input("Launch with public URL? (Y/N)")
#	if public.lower() == 'y' or public.lower() == 'yes':
#		app.launch(share=True)
#	else:
#		app.launch()
	 app.launch()
