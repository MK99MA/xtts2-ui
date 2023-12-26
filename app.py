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
from datetime import datetime
#import tqdm
#import time

def is_mac_os():
	return platform.system() == 'Darwin'

css = """
.token {
	height: 27.5px !important;
}
.wrap-inner {
	gap: 0px !important;
}
.remove-all {
	margin-left: unset !important;
}
.icon-wrap {
	margin-right: unset !important;
}
.adminbutton {
	bottom: 0;
	height: 50%;
	position: absolute;
}
.empty {
	background: var(--block-background-fill);
}
.button_75 {
	height: 75%;
}
.row_75 {
	height: 30px;
	gap: unset;
}
.vert_button {
	height: 60px;
}
.adminrow {
	background: var(--block-background-fill);
	gap:unset;
}
.vert_bar {
	background: var(--body-background-fill);
	gap: 10px;
}
.background-basic {
	background: var(--block-background-fill);
}
.headline {
	text-align: center;
}
"""

#--button-secondary-background-fill
#var(--neutral-600);
#--border-color-primary


# https://docs.coqui.ai/en/latest/models/xtts.html#inference-parameters
params = {
	"activate": True,
	"autoplay": True,
	"show_text": False,
	"remove_trailing_dots": False,
	"voice": "Rogger.wav",
	"language": "English",
	"model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
}

# DOWNLOAD in VOICE GEN!!

# SUPPORTED_FORMATS = ['wav', 'mp3', 'flac', 'ogg']
SAMPLE_RATE = 16000
device = None

# Set the default speaker name
default_speaker_name = "Rogger"
def_struct = ["Speaker", "Input"]
fl_name = ''#'outputs/' + def_struct + '.wav'
output_file = Path(fl_name)
my_waveform = {
	"waveform_color": "white",
	"waveform_progress_color": "orange",
	"show_controls": False,
	"skip_length": 0.5
}

#print(gr.__version__)

def set_hardware(cpu_val):
	if cpu_val:
		use_device = 'cpu'
	else:
		if torch.cuda.is_available():
			use_device = 'cuda:0'
		else:
			use_device = 'cpu'

	# Decide on Hardware to use
	if is_mac_os():
		device = torch.device('cpu')
	else:
		#device = torch.device('cuda:0')
		#AMD GPU and too lazy to add a coded check...
		device = torch.device(use_device) #'cpu')

	# Load model
	tts = TTS(model_name=params["model_name"]).to(device)
	return tts

###############################################################################
############################### Generate Voice ################################
###############################################################################

# # Random sentence (assuming harvard_sentences.txt is in the correct path)
# def random_sentence():
#	 with open(Path("harvard_sentences.txt")) as f:
#		 return random.choice(list(f))

# toggle cancel button
def handle_cancel():
	return gr.update(interactive = False)
	# Change when Abortfunction stops the actual Generation True)

def block_cancel():
	gr.Warning("Generation was aborted.")
	return gr.update(interactive = False)

def handle_custom_text(input):
	input = html.unescape(input)
	input = input.replace(" ", "_")
	gr.Info("Custom string was set to " + input)
	return gr.update(
		value = input
	)

def filename_selection(structure, input):
	for elem in structure:
		if elem == "Custom":
			enable_box = True
		else:
			enable_box = False

	return(
		gr.update(
			interactive = enable_box
		)
	)

def get_iso(lang):
	try:
		with open('languages.json', 'r') as langfile:
			data = json.load(langfile)
	except FileNotFoundError:
		data = {}

	iso = data.get(lang, None)

	return iso

# Voice generation function
def gen_voice(string, spk, speed, english, structure, custom):
	string = html.unescape(string)
	short_uuid = str(uuid.uuid4())[:8]

	iso_code = get_iso(english)
	date = datetime.now().date()
	date = date.strftime("%d%m%Y")

	mapping = {
		"Input": string,
		"Speaker": spk,
		"Speed": speed,
		"Language": english,
		"ISO Code": iso_code,
		"Custom": custom,
		"UUID": short_uuid,
		"Date": date
	}

	if len(structure) == 0:
		out_string = string
	elif len(structure) == 1:
		buf1 = mapping.get(structure[0], "")
		buf2 = ""
		buf3 = ""
	elif len(structure) == 2:
		buf1 = mapping.get(structure[0], "")
		buf2 = mapping.get(structure[1], "")
		buf3 = ""
	elif len(structure) == 3:
		buf1 = mapping.get(structure[0], "")
		buf2 = mapping.get(structure[1], "")
		buf3 = mapping.get(structure[2], "")

	out_string = "_".join(filter(None, [buf1, buf2, buf3]))

	out_string = out_string.replace(" ", "_")
	fl_name = 'outputs/' + out_string + '.wav'#spk + "-" + short_uuid +'.wav'
	fl_name, name = modify_filename(fl_name)
	output_file = Path(fl_name)
	this_dir = str(Path(__file__).parent.resolve())
	tts.tts_to_file(
		text=string,
		speed=speed,
		file_path=output_file,
		speaker_wav=[f"{this_dir}/targets/" +spk + ".wav"],
		language=languages[english]
	)
	return(
		output_file,
		gr.update(interactive = False)
	)

# restore defaults
def reload_defaults():
	default_speaker_name = get_config_val("default_speaker_name")
	language = get_config_val("language")
	def_speed = get_config_val("speed")
	def_struct = get_config_val("def_structure")
	return(
		def_speed,
		default_speaker_name,
		language,
		def_struct
	)


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
			"def_structure": def_struct,
			"language": "English",
			"speed": "0.8",
			"launch":{
				"browser": False,
				"share": False,
				"favicon": "mk99.ico",
				"cpu": cpu_val
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
	cpu_val = get_config_val("launch", "cpu")
	default_speaker_name = get_config_val("default_speaker_name")
	language = get_config_val("language")
	def_speed = get_config_val("speed")
	def_struct = get_config_val("def_structure")

	return(
		out_path,
		tar_path,
		temp_path,
		browser_val,
		share_val,
		favicon,
		cpu_val,
		default_speaker_name,
		def_speed,
		def_struct,
		language
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
	return gr.update(value = display_json("config.json"))

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

# Share Checkbox
def share_handler(checkbox, admin_state):
	if checkbox:
		update_config("launch", True, "share")
		gr.Info("Public sharing has been enabled for the next start!")
	else:
		update_config("launch", False, "share")
		gr.Info("Public sharing has been disabled for the next start!")

	return gr.update()

# Browser Checkbox
def browser_handler(checkbox, admin_state):
	if checkbox:
		update_config("launch", True, "browser")
		gr.Info("The browser will automatically open the webinterface after the next start!")
	else:
		update_config("launch", False, "browser")
		gr.Info("The browser won't automatically open the webinterface after the next start!")

	return gr.update()

# CPU checkbox
def cpu_handler(checkbox, admin_state):
	if checkbox:
		update_config("launch", True, "cpu")
		gr.Info("Generation will use the CPU after the next start!")
	else:
		if torch.cuda.is_available():
			update_config("launch", False, "cpu")
			gr.Info("Generation will use the GPU after the next start!")
		else:
			update_config("launch", True, "cpu")
			gr.Warning("Can't use GPU generation on this system!")

			return gr.update(value = True)

	return gr.update()

# handle password Box
def comp_pw(text, admin_state, *components):
	#pl34Sed0n'Tabu5eMe
	password = "91f0660bb9cf2d91875508527cbf46a8"
	enc_text = text.encode('utf-8')
	returnlist = []
	if hashlib.md5(enc_text).hexdigest() == password:
		admin_state = True
		gr.Info("Password correct! Admin access enabled.")
		info_text = "### Admin Access **(Active)**:"
		for component in components:
			component = gr.update(interactive = True)
			returnlist.append(component)
	else:
		admin_state = False
		gr.Warning("Wrong password! Admin access disabled.")
		info_text = "### Admin Access **(Inactive)**:"
		for component in components:
			component = gr.update(interactive = False)
			returnlist.append(component)
	return(
		gr.update(value = ""),
		gr.update(value = info_text),
		admin_state,
		*returnlist
	)

def set_default_lang(lang_drop_val):
	update_config('language', lang_drop_val)
	language = lang_drop_val
	return(
		gr.update(
			value = language
		),
		gr.update(
			value = language
		)
	)

def set_default_structure(structure):
	update_config('def_structure', structure)
	def_struct = structure
	return(
		gr.update(
			value = structure
		),
		gr.update(
			value = structure
		)
	)

def set_default_speed(speed_slide_val):
	update_config('speed', speed_slide_val)
	speed = speed_slide_val
	return(
		gr.update(
			value = speed
		),
		gr.update(
			value = speed
		)
	)


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
				print("none ?!")
				return None
	url = "/file=temp/" + "generated_audio.zip"
	return url #"tmp.zip"

def single_download(selected_file):
	if os.path.exists(selected_file):
		folder, filename = os.path.split(selected_file)
		url = "file=outputs/" + filename
	else:
		return None

	return url

# Download handler
def get_selected(selected_files, radio):
	if selected_files != None:
		if (radio == "Single"):
			download_link = single_download(selected_files)
		else:
			if len(selected_files) >= 1:
				download_link = zipped_download(selected_files)
			else:
				return gr.update(link = "", interactive = False)

		if download_link == None:
			return gr.update(interactive=False)
		else:
			return gr.update(link = download_link, interactive = True)
	else:
		return gr.update(link = "", interactive = False)

# Outputs Preview handler
def playfile(selected_files, radio):
	if selected_files != None:
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
	else:
		return gr.Audio(label="Preview", visible = False)


# Output deletion selection handler
def del_output_sel(selected_files, admin_state):
	#print(selected_files)
	if selected_files != None:
		if len(selected_files) > 0:
			for file in selected_files:
				if os.path.exists(file) and admin_state == True:
					return(
						gr.update(interactive = True),
						gr.update(),
						gr.update()
					)

	return(
	 	gr.update(visible=True, interactive = False),
		gr.update(visible=False),
		gr.update(visible=False)
	)

# Delete Button Function
def del_files(selected_files):
	delete_list = []
	if isinstance(selected_files, str):
		if os.path.exists(selected_files):
			folder, filename = os.path.split(selected_files)
			del_path = 'outputs/' + filename

	else:
		for file in selected_files:
			if os.path.exists(file):
				folder, filename = os.path.split(file)
				del_path = 'outputs/' + filename
				delete_list.append(del_path)

	if isinstance(selected_files, str):
		if os.path.exists(del_path):
			os.remove(del_path)
		sel_value = None
	else:
		for path in delete_list:
			if os.path.exists(path):
				os.remove(path)
		sel_value = []

	return(
		gr.update(visible=True, interactive = False),
		gr.update(choices=list_dir_out(), value = sel_value),
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

def reload_outputs():
	return gr.update(choices = list_dir_out())


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
	update_config('default_speaker_name', sel_speaker)
	default_speaker_name = sel_speaker
	return(
		gr.update(
			choices = update_speakers(),
			value = sel_speaker
		),
		gr.update(
			choices = update_speakers(),
			value = sel_speaker
		)
	)

# Delete currently selected Speaker (Dropbox)
def del_speaker(speaker_dropdown):
	speaker_del = speaker_dropdown
	del_path = 'targets/' + speaker_del + '.wav'
	if os.path.exists(del_path):
		os.remove(del_path)
	else:
		print("The file does not exist: " + del_path)

	default_speaker_name = get_config_val("default_speaker_name")
	if default_speaker_name == speaker_del:
		speakerlist = update_speakers()
		default_speaker_name = speakerlist[0]
		update_config("default_speaker_name", default_speaker_name)

	#Refresh Box and set default value
	return(
		gr.update(choices=update_speakers(),
			value=default_speaker_name
		),
		gr.update(visible = True),
		gr.update(visible = False),
		gr.update(visible = False)
	)

# Get files in directory /targets
def update_speakers():
	speakers = {p.stem: str(p) for p in list(Path('targets').glob("*.wav"))}
	speakerlist = list(speakers.keys())

	speakerlist = sorted(speakerlist, key=str.casefold)

	return speakerlist

# Create Dropdown
# update_speakers () = list of voices
def update_dropdown(_=None, selected_speaker=default_speaker_name):
	return gr.Dropdown(choices=update_speakers(), value=selected_speaker, label="Select Speaker", filterable=True)

# Rename Target filename
def rename_target(target, newname):
	if newname =="":
		newname = "unnamed"
	old = 'targets/' + target + '.wav'
	new = 'targets/' + newname + '.wav'
	if os.path.exists(old):
		os.rename(old, new)
		update_config('default_speaker_name', newname)

		return(
			gr.update(
				choices = update_speakers(),
				value = newname
				),
			gr.update(
				choices = update_speakers()
			)
		)

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
	return save_path, ""

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
	#return	updated_dropdown
	return(
		gr.update(
			choices = update_speakers()
			),
		gr.update(
			choices = update_speakers()
		)
	)

###############################################################################
#################################### MAIN #####################################
###############################################################################
createConfig()
out_path, tar_path, temp_path, browser_val, share_val, favicon, cpu_val, default_speaker_name, speed, def_struct, language = loadConfig()

if "Custom" in def_struct:
	custom_active = True
else:
	custom_active = False

tts = set_hardware(cpu_val)

# Load the language data
with open(Path('languages.json'), encoding='utf8') as f:
	languages = json.load(f)

struct_list = ["Custom", "Date", "Input", "ISO Code", "Language", "Speaker", "Speed", "UUID"] # Text = string_ul

################################################################################
# Gradio Blocks interface
with gr.Blocks(mode = "MK99", title = "MK99 - TTS Gen", css = css) as app:
	gr.Markdown("### TTS based Voice Cloning.")
	admin_state = gr.State(
		value=False
	)

	with gr.Tab("Voice Generation") as t1:
		with gr.Row():
			with gr.Column(scale=1):
				with gr.Group():
					with gr.Row():
						with gr.Column(scale=2):
							text_input = gr.Textbox(
								lines=2,
								label="Speechify this Text",
								autofocus = True,
								value="Even in the darkest nights, a single spark of hope can ignite the fire of determination within us, guiding us towards a future we dare to dream."
							)

					with gr.Row():
						with gr.Column(scale=2):
							speed_slider = gr.Slider(
								label = 'Speed',
								minimum = 0.1,
								maximum = 1.99,
								value = speed, # 0.8,
								step = 0.01
							)

					with gr.Row():
						with gr.Column():
							gen_speaker_dropdown = gr.Dropdown(
								choices = update_speakers(),
								value = default_speaker_name,
								label = "Select Speaker",
								filterable = True
							)#update_dropdown()
						with gr.Column():
							language_dropdown = gr.Dropdown(
								list(languages.keys()),
								label = "Language/Accent",
								value = language #"English"
							)

			with gr.Column(scale=0, min_width=75):
				with gr.Group():
					with gr.Column(elem_classes="vert_bar"):
						cleargen_button = gr.ClearButton(
							components = [text_input],
							value = "Clear Text",
							elem_classes = "vert_button"
						)
						submit_button = gr.Button(
							value = "Generate Voice",
							elem_classes = "vert_button"
						)
						# TODO
						cancel_gen_button = gr.Button(
							value = "Abort Process",
							elem_classes = "vert_button",
							interactive = False
						)
						reload_def = gr.Button(
							value = "Restore Defaults",
							elem_classes = "vert_button"
						)

			with gr.Column(scale=1):
				with gr.Group():
					with gr.Row():
						audio_output = gr.Audio()

					with gr.Row(elem_classes = "row_75"):
						with gr.Column(scale = 1, min_width = 50):
							download_button = gr.Button(
								value = "Download",
								icon = "dl.ico",
								link = output_file,
								elem_classes = "button_75"
							)

					with gr.Row():
						# Column for filename structure
						with gr.Column(scale=1, min_width = 150):
							filename_struct = gr.Dropdown(
								label = "Filename structure",
								info = "Select up to 3 elements to be used in the filename.",
								choices = struct_list,
								multiselect = True,
								filterable = True,
								value = def_struct,
								max_choices = 3,
								interactive = True
							)
						with gr.Column(scale = 0, min_width = 275):
							custom_input = gr.Textbox(
								label = "Enter 'custom' string",
								info = "Enter to confirm.",
								placeholder = "Enter a custom value",
								interactive = custom_active
							)

		submit_click = submit_button.click(
			fn=gen_voice,
			inputs=[text_input, gen_speaker_dropdown, speed_slider, language_dropdown, filename_struct, custom_input],
			outputs=[audio_output, cancel_gen_button]
		)

		submit_button.click(
			fn=handle_cancel,
			inputs=[],
			outputs=[cancel_gen_button]
		)

		custom_input.submit(
			fn=handle_custom_text,
			inputs=[custom_input],
			outputs=[custom_input],
			show_progress = "hidden"
		)

		filename_struct.select(
			fn=filename_selection,
			inputs=[filename_struct, custom_input],
			outputs=[custom_input]
		)

		cancel_gen_button.click(
			fn=block_cancel,
			inputs=[],
			outputs=[cancel_gen_button],
			cancels=[submit_click]
		)

		reload_def.click(
			fn=reload_defaults,
			inputs=[],
			outputs=[speed_slider, gen_speaker_dropdown, language_dropdown, filename_struct]
		)

	with gr.Tab("Voice cloning and management") as t2:
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
					)

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
					with gr.Row():
						with gr.Column(scale=1, min_width = 200):
							#Delete selected Speaker
							delete_speaker_button = gr.Button(
								value = "🗑️ Delete speaker",
								interactive = False
							)
						with gr.Column(scale=1, min_width = 100):
							tar_confirm_button = gr.Button(
								value = "✔️",
								variant = "primary",
								visible = False
							)
						with gr.Column(scale=1, min_width = 100):
							tar_cancel_button = gr.Button(
								value = "❌",
								visible = False
							)

		with gr.Row():
			record_button = gr.Audio(
				label="Record Your Voice"
			)

		with gr.Row():
			with gr.Accordion(label="🔽 Download Voice 🔽", open=False):
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

		# Handle default speaker button ADMIN ACCESS
		default_speaker_button.click(
			fn=set_default_speaker,
			inputs=[speaker_dropdown], #vars,
			outputs=[speaker_dropdown, gen_speaker_dropdown]
		)

		speaker_dropdown.change(
			fn=lambda :[gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)],
			inputs=None,
			outputs=[delete_speaker_button, tar_confirm_button, tar_cancel_button]
		)

		delete_speaker_button.click(
			fn=lambda :[gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)],
			inputs=None,
			outputs=[delete_speaker_button, tar_confirm_button, tar_cancel_button]
		)

		# Handle confirm button for deletion
		tar_confirm_button.click(
			fn=del_speaker,
			inputs=[speaker_dropdown],
			outputs=[speaker_dropdown, delete_speaker_button, tar_confirm_button, tar_cancel_button]
		)

		# Handle cancel button for deletion
		tar_cancel_button.click(
			fn=lambda :[gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)],
			inputs=None,
			outputs=[delete_speaker_button, tar_confirm_button, tar_cancel_button]
		)

		# Handle rename button ADMIN ACCESS TODO
		rename_button.click(
			fn=rename_target,
			inputs=[speaker_dropdown, rename_box],
			outputs=[speaker_dropdown, gen_speaker_dropdown]
		)

		# Handle save recording button
		save_button.click(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=[speaker_dropdown,gen_speaker_dropdown]
		)
		# UPDATE VOICEGEN LIST!!

		# Handle stop recording button
		record_button.stop_recording(
			fn=handle_recorded_audio,
			inputs=[record_button, speaker_dropdown, filename_input],
			outputs=[speaker_dropdown,gen_speaker_dropdown]
		)

#		# Handle upload record button
#		record_button.upload(
#			fn=handle_recorded_audio,
#			inputs=[record_button, speaker_dropdown, filename_input],
#			outputs=[speaker_dropdown, gen_speaker_dropdown]
#		)

		# Handle Preview dropdown list
		target_drop.change(
			fn=playfile_target,
			inputs=[target_drop],
			outputs= previewfile_target,
			queue = False
		)

	with gr.Tab("Outputs") as t3:
		with gr.Row():
			with gr.Column(scale=1):
				gr.Markdown("### Output Archive - Download generated files")

		with gr.Group():
			with gr.Row():
				gr.Markdown(value = "###    Selection Mode", elem_classes = "headline")
			with gr.Row():
				gr.Textbox(
					value = "[Single] - Only one file can be selected, best for playback.\n\n[Multi] - Multiple files can be selected, best for managing.",
					container = False,
					lines = 3,
					interactive = False
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

				with gr.Column(scale = 0, min_width = 130):
					with gr.Row():
						with gr.Column(scale = 1, min_width = 130):
							delete_button = gr.Button(
								value = "🗑️",
								interactive = False
							)
						with gr.Column(scale=0, min_width=64.5):
							confirm_button = gr.Button(
								value = "✔️",
								variant = "primary",
								visible = False
							)
						with gr.Column(scale=0, min_width=64.5):
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

		# Update Dropdown on tab selected
		t3.select(
			fn=reload_outputs,
			inputs=[],
			outputs=drop_explorer
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
			inputs=[drop_explorer, select_radio],
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
			outputs=[delete_button, confirm_button, cancel_button] #HIDE CONFIRM / CANCEL
		)

		# Handle delete button - shows confirmation buttons
		delete_button.click(
			fn=lambda :[gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)],
			inputs=None,
			outputs=[delete_button, confirm_button, cancel_button]
		)

		# Handle confirm button for deletion
		confirm_button.click(
			fn=del_files,
			inputs=[drop_explorer],
			outputs=[delete_button, drop_explorer, confirm_button, cancel_button]
		)

		# Handle cancel button for deletion
		cancel_button.click(
			fn=lambda :[gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)],
			inputs=None,
			outputs=[delete_button, confirm_button, cancel_button]
		)

		# Handle select all button
		selectall_button.click(
			fn=select_all,
			inputs = [drop_explorer],
			outputs=drop_explorer
		)

		# Handle select none button
		selectnone_button.click(
			fn=select_none,
			inputs = [drop_explorer],
			outputs=drop_explorer
		)

	with gr.Tab("Settings") as t4:
		with gr.Row(equal_height=True):
			with gr.Column(scale=1):
				with gr.Group():
					gr.Markdown(value = "### Saved Configurations:", elem_classes = "headline")
					json_comp = gr.JSON(
						value=display_json("config.json"),
						label="Configuration"
					)
					refreshjson = gr.Button(
						value="Refresh JSON"
					)

			#with gr.Column(scale=1):
			#	with gr.Group():
			#		gr.Markdown(value = "### Enable Admin Access:", elem_classes = "headline")
			#		with gr.Column():
			#			pw_text = gr.Textbox(
			#				label="Admin password",
			#				placeholder="Enter the password...",
			#				type="password",
			#				autofocus=True,
			#				info="Entering the correct password will enable all blocked components."
			#			)
			#		with gr.Column(elem_classes="adminrow"):
			#			apply_btn = gr.Button(
			#				value = "Apply"
			#			)

			with gr.Column(scale=2):
				with gr.Group():
					status = gr.Markdown(value = "### Admin Access **(Inactive)**:", elem_classes = "headline")
					with gr.Row():
						with gr.Column(scale = 1):
							pw_text = gr.Textbox(
								label = "Admin password",
								placeholder = "Enter the password...",
								type = "password",
								autofocus = True,
								info = "Entering the correct password will enable all blocked components.",
							)
						#with gr.Column(scale = 0, min_width = 120, elem_classes="adminrow"):
							check_btn = gr.Button(
								value = "Check Password",
								#elem_classes = "adminbutton"
							)
						with gr.Column(scale = 0, min_width = 150, elem_classes = "empty"):
							def_lang_drop = gr.Dropdown(
								choices = list(languages.keys()),
								label = "Default Language",
								value = language,
								interactive = False,
								info = "Default selected language."
							)

						with gr.Column(scale = 1):
							def_file_struct = gr.Dropdown(
								choices = struct_list,
								label = "Default filename structure",
								interactive = False,
								multiselect = True,
								filterable = True,
								max_choices = 3,
								info = "Select up to 3 elements for downloaded files.",
								value = def_struct
							)

							struct_button = gr.Button(
								interactive = False,
								value = "Confirm",
							)

					with gr.Row():
						with gr.Column(scale = 1):
							def_speed_slide = gr.Slider(
								label = "Default Speed",
								minimum = 0.1,
								maximum = 1.99,
								value = speed,
								step = 0.01,
								interactive = False
							)

					# https://www.gradio.app/docs/interface#interface-launch-arguments
					with gr.Row():
						share_check = gr.Checkbox(
							label = "Create public link?",
							info = "Enable to activate app sharing at launch (Requires restart)",
							interactive = False,
							value = share_val
						)
						browser_check = gr.Checkbox(
							label = "Open Browser?",
							info = "Enable to automatically open the browser at start. (Requires restart)",
							interactive = False,
							value = browser_val
						)

					with gr.Row(elem_classes = "empty"):
						with gr.Column(scale=2):
							model_name = gr.Textbox(
								label = "Model name",
								interactive = False,
								value = params["model_name"]
							)
						with gr.Column(scale=1, elem_classes = "empty"):
							cpu_check = gr.Checkbox(
								label = "Use CPU?",
								info = "Enable to force using your CPU.",
								interactive = False,
								value = cpu_val
							)

	# Enable locked buttons if password is correct
	check_btn.click(
		fn=comp_pw,
		inputs=[pw_text, admin_state, def_lang_drop, def_speed_slide, share_check, browser_check, cpu_check, default_speaker_button, rename_button, rename_box, delete_speaker_button, def_file_struct, struct_button],
		outputs=[pw_text, status, admin_state, def_lang_drop, def_speed_slide, share_check, browser_check, cpu_check, default_speaker_button, rename_button, rename_box, delete_speaker_button, def_file_struct, struct_button],
		#show_progress="hidden"
	)

	struct_button.click(
		fn=set_default_structure,
		inputs=[def_file_struct],
		outputs=[def_file_struct, filename_struct]
	)

	# Handle default language checkbox
	def_lang_drop.change(
		fn=set_default_lang,
		inputs=[def_lang_drop],
		outputs=[def_lang_drop, language_dropdown]
	)

	# Handle default speed Slider
	def_speed_slide.release(
		fn=set_default_speed,
		inputs=[def_speed_slide],
		outputs=[def_speed_slide, speed_slider]
	)

	# Handle share checkbox selection ADMIN ACCESS
	share_check.change(
		fn=share_handler,
		inputs=[share_check, admin_state],
		outputs=share_check
	)

	# Handle browser checkbox selection ADMIN ACCESS
	browser_check.change(
		fn=browser_handler,
		inputs=[browser_check, admin_state],
		outputs=[browser_check]
	)

	# Handle CPU checkbox Selection
	cpu_check.select(
		fn=cpu_handler,
		inputs=[cpu_check, admin_state],
		outputs=[cpu_check]
	)

	# Handle json refresh button
	refreshjson.click(
		fn=refresh_json,
		inputs=[],
		outputs=json_comp
	)

	# Refresh JSON on selecting Tab
	t4.select(
		fn=refresh_json,
		inputs=[],
		outputs=json_comp
	)


if __name__ == "__main__":

	app.launch(
		allowed_paths=[out_path, tar_path, temp_path], #["/home/mk99/xtts2-ui/outputs/","/home/mk99/xtts2-ui/temp/"],
		inbrowser=browser_val,
		favicon_path=favicon, #"mk99.ico",
		share=share_val
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
