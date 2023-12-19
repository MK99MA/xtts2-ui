import gradio as gr
import torch
import platform
import random
import json
from pathlib import Path
from TTS.api import TTS
from zipfile import ZipFile
import uuid
import html
import soundfile as sf
import os
import requests
import hashlib
#import tqdm
#import time

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
def_struct = 'spk + string_ul'
fl_name = ''#'outputs/' + def_struct + '.wav'
output_file = Path(fl_name)
my_waveform = {
	"waveform_color": "white",
	"waveform_progress_color": "orange",
	"show_controls": False,
	"skip_length": 0.5
}

#print(gr.__version__)

# Decide on Hardware to use
if is_mac_os():
	device = torch.device('cpu')
else:
	#device = torch.device('cuda:0')
	#AMD GPU and too lazy to add a coded check...
	device = torch.device('cpu')

###############################################################################
############################### Generate Voice ################################
###############################################################################

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

###############################################################################
############################# Settings & Config ###############################
###############################################################################

# Create Configuration
def createConfig():
	#Check if config exists
	if not os.path.isfile('config.json'):
		# Default config values for creation
		default_vals = {
			"default_speaker_name": default_speaker_name,
			"def_struct": def_struct,
			"language": "English",
			"speed": "0.8",
			"launch":{
				"browser": False,
				"share": False,
				"favicon": "mk99.ico"
			}
		}

		myJSON = json.dumps(default_vals, indent=2)

		with open ('config.json', 'w') as jsonfile:
			jsonfile.write(myJSON)

def loadConfig():
	root_dir = os.getcwd()
	out_path = root_dir + "/outputs"
	tar_path = root_dir + "/targets"
	temp_path = root_dir + "/temp"
	browser_val = get_config_val("launch", "browser")
	share_val = get_config_val("launch", "share")
	favicon = get_config_val("launch", "favicon")
	default_speaker_name = get_config_val("default_speaker_name")
	language = get_config_val("language")
	speed = get_config_val("speed")
	def_struct = get_config_val("def_struct")

	return(
		out_path,
		tar_path,
		temp_path,
		browser_val,
		share_val,
		favicon,
		default_speaker_name,
		speed,
		def_struct
	)

# Display content of config.json
def display_json(file_path):
    try:
        with open(file_path, 'r') as file:
            json_content = json.load(file)
            return json_content
    except Exception as e:
        return f"Error: {str(e)}"

# Refresh config.json display
def refresh_json():
	return gr.update(display_json("config.json"))

# Update config with new value
def update_config(key, value, subkey=None):
	try:
		with open ('config.json', 'r') as jsonfile:
			data = json.load(jsonfile)
	except FileNotFoundError:
		data = {}

	if subkey:
		data[key] = data.get(key, {})
		data[key][subkey] = value
	else:
		data[key] = value

	with open('config.json', 'w') as jsonfile:
		json.dump(data, jsonfile, indent=2)
		#jsonfile.close()

# Get config Values
def get_config_val(key, subkey=None):
	try:
		with open ('config.json', 'r') as jsonfile:
			data = json.load(jsonfile)
	except FileNotFoundError:
		data = {}

	conf_value = data.get(key, {})

	if subkey:
		conf_value = conf_value.get(subkey, None)

	return conf_value

def share_handler(checkbox, admin_state):
	if admin_state:
		if checkbox:
			update_config("launch", True, "share")
			gr.Info("Public sharing has been enabled for the next start!")
		else:
			update_config("launch", False, "share")
			gr.Info("Public sharing has been disabled for the next start!")

		return gr.update()
	else:
		gr.Warning("You have to enter the admin password to change this value.")
		if checkbox:
			return gr.update(value=False)
		else:
			return gr.update(value=True)


# handle password Box
def comp_pw(text, admin_state):
	#pl34Sed0n'Tabu5eMe
	password = "91f0660bb9cf2d91875508527cbf46a8"
	enc_text = text.encode('utf-8')
	if hashlib.md5(enc_text).hexdigest() == password:
		admin_state = True
		return admin_state
	else:
		admin_state = False
		return admin_state

###############################################################################
################################### OUTPUT ####################################
###############################################################################

# Zip files for download
def zipped_download(selected_files):
	with ZipFile("temp/generated_audio.zip","w") as zipObj:
		for file_path in selected_files:
			if os.path.exists(file_path):
				zipObj.write(file_path, arcname=os.path.basename(file_path))
			else:
				return None
	url = "/file=temp/" + "generated_audio.zip"
	return url #"tmp.zip"

# Download handler
def get_selected(selected_files):
	if len(selected_files) >= 1:
		download_link = zipped_download(selected_files)
		if download_link == None:
			return gr.update(interactive=False)
		else:
			return gr.Button(value = "Download", link = download_link, interactive = True)
	else:
		return gr.Button(value = "Download", link = "", interactive = False)


# Outputs Preview handler
def playfile(selected_files, radio):
	if len(selected_files) == 0:
		return gr.Audio(label="Preview", visible = False)
	else:
		if radio == "Multi":
			file = selected_files[0]
		else:
			file = selected_files

		if os.path.exists(file):
			folder, filename = os.path.split(file)
			url = "outputs/" + filename
		else:
			gr.Warning("File does not exist anymore.\n\nPlease select another file for playback.")
			return gr.update(visible = False)

		if len(selected_files) > 1 and radio == "Multi":
			gr.Info('Please select only 1 file at a time for playback!\n\nOnly the first selected file in list will be available for playback.')
			return gr.update(value = url, visible = True)
		else:
			return gr.update(value = url, visible = True, show_download_button = True, show_share_button = True, format = 'wav')



# Output deletion selection handler
def del_output_sel(selected_files, admin_state):
	#print(selected_files)
	if len(selected_files) == 0:
		#return gr.Button(value = "Delete", interactive = False)
		return(
		 	gr.update(visible=True, interactive = False),
			gr.update(visible=False),
			gr.update(visible=False),
			gr.update(visible=False)
		)
	else:
		for file in selected_files:
			if os.path.exists(file) and admin_state == True:
				#return gr.Button(value = "Delete", interactive = True)
				return(
					gr.update(interactive = True),
					gr.update(),
					gr.update(),
					gr.update()
				)

			else:
				return(
				 	gr.update(visible=True, interactive = False),
					gr.update(visible=False),
					gr.update(visible=False),
					gr.update(visible=False)
				)

# Delete Button Function
def del_files(selected_files):
	for file in selected_files:
		if os.path.exists(file):
			folder, filename = os.path.split(file)
			del_path = 'outputs/' + filename
		else:
			return (
				gr.update(visible=True, interactive = False),
				#gr.Button(value = "Delete", interactive = False),
				gr.update(value = []),
				#gr.FileExplorer(glob = '*.wav', root="outputs", label="Select files to download", height = 400.0)
				gr.update(visible=False),
				gr.update(visible=False),
				gr.update(visible=False)
			)
		if os.path.exists(del_path):
			os.remove(del_path)
			return(
				#gr.Button(value = "Delete", interactive = False),
				gr.update(visible=True, interactive = False),
				#gr.FileExplorer(glob = '*.wav', root="outputs", label="Select files to download", height = 400.0)
				gr.update(choices=list_dir(), value = []),
				gr.update(visible=False),
				gr.update(visible=False),
				gr.update(visible=False)
			)
		else:
			print("The file does not exist: " + del_path)
			return(
				gr.update(visible=True, interactive = False),
				#gr.Button(value = "Delete", interactive = False),
				gr.update(value = []),
				#gr.FileExplorer(glob = '*.wav', root="outputs", label="Select files to download", height = 400.0)
				gr.update(visible=False),
				gr.update(visible=False),
				gr.update(visible=False)
			)

def list_dir_out():
	pathlist = []
	filelist = []
	fullpath = os.getcwd() + "/outputs/"
	for path in os.listdir("outputs"):
		if os.path.isfile(os.path.join("outputs", path)):
			folder, ext = os.path.splitext(path)
			if ext == ".wav":
				pathlist.append(fullpath + path)
				filelist.append(path)

			pathlist = sorted(pathlist, key=str.casefold)
			filelist = sorted(filelist, key=str.casefold)

	return list(map(lambda x, y:(x,y), filelist,pathlist))


def radio_select(radio):
	if radio == "Multi":
		return(
			gr.update(multiselect = True),
			gr.update(interactive = True),
			gr.update(visible = False)
		)
	else:
		return(
		 	gr.update(multiselect = False),
			gr.update(interactive = False),
			gr.update(visible = False)
		)

# Selection button handler
def select_all(drop_explorer):
	pathlist = []
	fullpath = os.getcwd() + "/outputs/"
	for path in os.listdir("outputs"):
		if os.path.isfile(os.path.join("outputs", path)):
			folder, ext = os.path.splitext(path)
			if ext == ".wav":
				pathlist.append(fullpath + path)
				pathlist = sorted(pathlist, key=str.casefold)

	return gr.update(value = pathlist)

def select_none(drop_explorer):
	return gr.update(value = [])

###############################################################################
################################### TARGET ####################################
###############################################################################
def list_dir_tar():
	pathlist = []
	filelist = []
	fullpath = os.getcwd() + "/targets/"
	for path in os.listdir("targets"):
		if os.path.isfile(os.path.join("targets", path)):
			folder, ext = os.path.splitext(path)
			if ext == ".wav":
				pathlist.append(fullpath + path)
				filelist.append(path)

			pathlist = sorted(pathlist, key=str.casefold)
			filelist = sorted(filelist, key=str.casefold)

	return list(map(lambda x, y:(x,y), filelist,pathlist))

# Targets Preview handler
def playfile_target(selected_files):
	if selected_files:
		if len(selected_files) > 1:
			file = selected_files
			if os.path.exists(file):
				folder, filename = os.path.split(file)
				url = "targets/" + filename
				return gr.update(value = url, show_download_button = True)
			else:
				return gr.update(visible=False, value=None)
		else:
			return gr.update(visible = False, value=None)
	else:
		return gr.update(visible = False, value=None)


# Save currently selected Speaker (dropbox) as default in config
def set_default_speaker(speaker_dropdown):
	sel_speaker = speaker_dropdown
	#print(sel_speaker)
	update_config('default_speaker_name', sel_speaker)
	return gr.Dropdown(
		choices=update_speakers(),
		value=default_speaker_name,
		label="Select Speaker"
	)

# Delete currently selected Speaker (Dropbox)
def del_speaker(speaker_dropdown, admin_state):
	speaker_del = speaker_dropdown
	del_path = 'targets/' + speaker_del + '.wav'
	if os.path.exists(del_path):
		os.remove(del_path)
		#Refresh Box and set default value
		return gr.Dropdown(choices=update_speakers(),
			value=default_speaker_name,
			label="Select Speaker"
		)
	else:
		print("The file does not exist: " + del_path)

# Get files in directory /targets
def update_speakers():
	speakers = {p.stem: str(p) for p in list(Path('targets').glob("*.wav"))}
	speakerlist = list(speakers.keys())

	speakerlist = sorted(speakerlist, key=str.casefold)

	return speakerlist #list(speakers.keys())

# Create Dropdown
# update_speakers () = list of voices
def update_dropdown(_=None, selected_speaker=default_speaker_name):
	print("upd_drop" + default_speaker_name)
	return gr.Dropdown(choices=update_speakers(), value=selected_speaker, label="Select Speaker", filterable=True)

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



###############################################################################
#################################### MAIN #####################################
###############################################################################
createConfig()
out_path, tar_path, temp_path, browser_val, share_val, favicon, default_speaker_name, speed, def_struct = loadConfig()

# Load the language data
with open(Path('languages.json'), encoding='utf8') as f:
	languages = json.load(f)

################################################################################
# Gradio Blocks interface
with gr.Blocks(mode = "MK99", title = "MK99 - TTS Gen") as app:
	gr.Markdown("### TTS based Voice Cloning.")
	admin_state = gr.State(
		value=False
	)

	with gr.Tab("Voice Generation"):
		with gr.Row():
			with gr.Column():
				text_input = gr.Textbox(
					lines=2,
					label="Speechify this Text",
					value="Even in the darkest nights, a single spark of hope can ignite the fire of determination within us, guiding us towards a future we dare to dream."
				)
				speed_slider = gr.Slider(
					label='Speed',
					minimum=0.1,
					maximum=1.99,
					value=0.8,
					step=0.01
				)
				with gr.Row():
					with gr.Column():
						#SYNC!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
						speaker_dropdown = update_dropdown()
					with gr.Column():
						language_dropdown = gr.Dropdown(list(languages.keys()), label="Language/Accent", value="English")

				submit_button = gr.Button("Convert")
################## TODO: Clear Button?
				#CANCELBUTTON FÜR RAPHAEL
			with gr.Column():
				audio_output = gr.Audio()

				with gr.Row():
					# Column for filename structure
					with gr.Column():
#########################TODO
						filename_struct = gr.Textbox(
							label="Filename structure",
							value = fl_name
						)
					with gr.Column():
#########################TODO
						download_input = gr.Textbox(
							label="Overwrite filename",
							placeholder="Enter a custom name for the generated audio"
						)
				with gr.Row():
#####################TODO
					# Download Button
					download_button = gr.Button("Download", link = output_file)

		submit_button.click(
			fn=gen_voice,
			inputs=[text_input, speaker_dropdown, speed_slider, language_dropdown],
			outputs=audio_output
		)

	with gr.Tab("Voice cloning and management"):
		gr.Markdown("### Speaker Selection and Voice Cloning")

		with gr.Group():
			with gr.Row():
				with gr.Column():
					#Enter new Name
					filename_input = gr.Textbox(label="Add new Speaker",
						placeholder="Enter a name for your recording/upload to save as"
					)
				with gr.Column():
					speaker_dropdown = gr.Dropdown(
						choices = update_speakers(),
						value = default_speaker_name,
						label = "Select Speaker",
						filterable = True
					)#update_dropdown()
					print("drop create"  + default_speaker_name)
					print(speaker_dropdown.value)

			with gr.Row():
				with gr.Column(scale = 1, min_width = 200):
					#Save a new speaker
					save_button = gr.Button(
						value = "💾 Save Voice"
					)
				with gr.Column(scale = 1, min_width = 200):
					#Set as default Speaker
					default_speaker_button = gr.Button(
						value = "⚙️ Set default speaker",
						interactive = False
					)
				with gr.Column(scale = 1, min_width = 200):
					rename_button = gr.Button(
						value = "🖊️ Rename Speaker",
						interactive = False
					)
				with gr.Column(scale = 1, min_width = 200):
					rename_box = gr.Textbox(
						container = False,
						interactive = False,
						placeholder = "New name"
					)
				with gr.Column(scale = 1, min_width = 200):
					#Delete selected Speaker
					delete_speaker_button = gr.Button(
						value = "🗑️ Delete speaker",
						interactive = False
					)

		with gr.Row():
			record_button = gr.Audio(
				label="Record Your Voice"
			)

		with gr.Row():
			with gr.Accordion(label="🔽 Download Voice 🔽", open=False):
				# CHANGE TO DROPDOWN!!!
				target_drop = gr.Dropdown(
					choices = list_dir_tar(),
					label="Preview / Download Voice",
					interactive = True,
					multiselect = False,
					filterable = True
				)
				with gr.Row():
					previewfile_target = gr.Audio(
						label="Preview",
						interactive=False
					)

		default_speaker_button.click(
			fn=set_default_speaker,
			inputs=[speaker_dropdown], #vars,
			outputs=speaker_dropdown
		)

		delete_speaker_button.click(
			fn=del_speaker, #function,
			inputs=[speaker_dropdown, admin_state], #vars,
			outputs=speaker_dropdown
		) #gradio_component to use)

#		refresh_button.click(
#			fn=update_dropdown,
#			inputs=[],
#			outputs=speaker_dropdown
#		)

		rename_button.click(
			print("Click")
		)

		save_button.click(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=speaker_dropdown
		)

		record_button.stop_recording(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=speaker_dropdown
		)

		record_button.upload(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=speaker_dropdown
		)

		target_drop.change(
			fn=playfile_target,
			inputs=[target_drop],
			outputs= previewfile_target,
			queue = False
		)

	with gr.Tab("Outputs"):
		with gr.Row():
			with gr.Column(scale=1):
				gr.Markdown("### Output Archive - Download generated files")

		with gr.Group():
			with gr.Row():
				gr.Markdown("###    Selection Mode")
			with gr.Row():
				gr.Textbox(
					value = "[Single] - Only one file can be selected, best for playback.\n\n[Multi] - Multiple files can be selected, best for managing.",
					container = False,
					lines = 3,
					interactive = False,
				)
			with gr.Row():
				select_radio = gr.Radio(
					choices = ["Single", "Multi"],
					show_label = False,
					value = "Single"
				)

			with gr.Row():
				drop_explorer = gr.Dropdown(
					choices = list_dir_out(),
					label = "Select files to download / preview",
					interactive = True,
					filterable = True,
					multiselect = False
				)

			with gr.Row():
				with gr.Column(scale=0, min_width=65):
					selectall_button = gr.Button(
						value = "🗹",
						interactive = False
					)

				with gr.Column(scale=0, min_width=65):
					selectnone_button = gr.Button(
						value = "☐"
					)

				with gr.Column(scale=2):
					download_button = gr.Button(
						value = "Download",
						interactive = False
					)

				with gr.Column(scale=0, min_width=130):
					delete_button = gr.Button(
						value = "🗑️",
						interactive = False
					)

			with gr.Row():
				with gr.Column(scale=2):
					empty = gr.Markdown(
						value=" ",
						visible=False
					)
				with gr.Column(scale=0, min_width=65):
					confirm_button = gr.Button(
						value = "✔️",
						variant = "primary",
						visible = False
					)
				with gr.Column(scale=0, min_width=65):
					cancel_button = gr.Button(
						value = "❌",
						visible = False
					)

			with gr.Row():
				previewfile = gr.Audio(
					label = "Preview",
					visible = False,
					interactive = False,
					waveform_options = my_waveform
				)

		# Handle selection mode
		select_radio.change(
			fn=radio_select,
			inputs=[select_radio],
			outputs=[drop_explorer, selectall_button, previewfile]
		)

		# Handle selection for donwload button
		drop_explorer.change(
			fn=get_selected,
			inputs=[drop_explorer],
			outputs=download_button
		)

		# Handle selection for Playback
		drop_explorer.change(
			fn=playfile,
			inputs=[drop_explorer, select_radio],
			outputs=previewfile
		)

		# Handle selection for deletion
		drop_explorer.change(
			fn=del_output_sel,
			inputs=[drop_explorer, admin_state],
			outputs=[delete_button, confirm_button, cancel_button, empty] #HIDE CONFIRM / CANCEL
		)

#		delete_button.click(
#			fn=del_files,
#			inputs=[drop_explorer],
#			outputs=[delete_button, drop_explorer]
#		)

		delete_button.click(
			fn=lambda :[gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)],
			inputs=None,
			outputs=[delete_button, confirm_button, cancel_button, empty]
		)

		confirm_button.click(
			fn=del_files,
			inputs=[drop_explorer],
			outputs=[delete_button, drop_explorer, confirm_button, cancel_button, empty]
		)

		cancel_button.click(
			fn=lambda :[gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)],
			inputs=None,
			outputs=[delete_button, confirm_button, cancel_button, empty]
		)

		selectall_button.click(
			fn=select_all,
			inputs = [drop_explorer],
			outputs=drop_explorer
		)

		selectnone_button.click(
			fn=select_none,
			inputs = [drop_explorer],
			outputs=drop_explorer
		)

	with gr.Tab("Settings"):
		with gr.Row(equal_height=True):
			with gr.Column():
				with gr.Group():
					gr.Markdown("### Saved Configurations:")
					json_comp = gr.JSON(
						value=display_json("config.json"),
						label="Configuration"
					)
					refreshjson = gr.Button(
						value="Refresh JSON"
					)

			with gr.Column():
				with gr.Group():
					gr.Markdown("### Admin Access:")
					pw_text = gr.Textbox(
						label="Admin password",
						placeholder="Enter the password...",
						type="password",
						autofocus=True,
						info="Entering the correct password will enable the use of certain buttons in the other tabs."
					)

					#FUNCTIONS!
					with gr.Row():
						def_lang_drop = gr.Dropdown(
							interactive = False
						)
						def_speed_slide = gr.Slider(
							interactive = False
						)
					with gr.Row():
						share_check = gr.Checkbox(
							label="Create public link?",
							info="Enable to activate app sharing at launch (Requires restart)",
							interactive = False
						)
						browser_check = gr.Checkbox(
							label="Open Browser?",
							info="Enable to automatically open the browser at start. (Requires restart)",
							interactive = False
						)

	pw_text.input(
		fn=comp_pw,
		inputs=[pw_text,admin_state],
		outputs=admin_state,
		show_progress="hidden"
	)

# ENABLE ALL THE STUFF!!
	share_check.change(
		fn=share_handler,
		inputs=[share_check, admin_state],
		outputs=share_check
	)
	#ENABLE?
	# Standard Sprache?
	# Standard Speed?
	# CONFIG LESEN!!!!
#	browser_check.change(
#		fn=browser_handler,
#		inputs=[browser_check, admin_state]
#	)


####
	json_comp.change(
		fn=refresh_json,
		inputs=[],
		outputs=json_comp
	)

if __name__ == "__main__":

	app.launch(
		allowed_paths=[out_path, tar_path, temp_path], #["/home/mk99/xtts2-ui/outputs/","/home/mk99/xtts2-ui/temp/"],
		inbrowser=browser_val,
		favicon_path=favicon, #"mk99.ico",
		share=share_val,

	)


# REQUIRES FFMPEG
#				waveform = gr.make_waveform(
#					audio="outputs/2B-a88498e0.wav",
#					bg_color="pink",
#					fg_alpha=0.5,
#					bars_color=("white", "orange"),
#					bar_count = 100,
#					bar_width = 0.5,
#					animate = True
#				)
