import gradio as gr

from modules import scripts, script_callbacks
from modules.ui_components import DropdownMulti
from modules.shared import opts, OptionInfo

from urllib.request import urlopen
from hashlib import md5

NAME = "e621 Prompt"

# List of tags categories. Shared between settings and UI
tags_categories_options = ["general", "species", "character", "copyright", "artist", "invalid", "lore", "meta", "rating"]

class E621PromptScript(scripts.Script):
  def title(self):
    return NAME

  def show(self, _is_img2img):
    return scripts.AlwaysVisible

  def clear_callback(self):
    return opts.e621_prompt_included_tags_categories, None, None, None

  def generate_callback(self, source, file_source, categories):
    if not source or file_source is None:
      return "ERROR: No input provided"

    if not categories:
      return "ERROR: No categories selected"

    return "result will be here"

  # Calculates hash of the uploaded image, and puts it inside of "source" field
  def image_upload_callback(self, source, image):
    if image is None:
      return source

    with urlopen(image) as response:
      return md5(response.read()).hexdigest()

  def ui(self, _is_img2img):
    with gr.Group():
      with gr.Accordion(NAME, open=False):
        source = gr.Textbox(label="Source", value="", placeholder="e621 post link / e621 post id / md5 hash of the image")

        file_source = gr.Image(
          source="upload",
          label="or upload image for hash calculation",
          type="numpy"
        )

        file_source.upload(self.image_upload_callback, inputs=[source, file_source], outputs=[source], preprocess=False)

        categories = gr.Dropdown(
          tags_categories_options,
          multiselect=True,
          value=opts.e621_prompt_included_tags_categories,
          label="Categories"
        )

        result = gr.Textbox(value="", label="Result", lines=5, interactive=False).style(show_copy_button=True)

        with gr.Row():
          with gr.Column():
            clear_btn = gr.Button("Reset form")
            clear_btn.click(fn=self.clear_callback, inputs=None, outputs=[categories, result, source, file_source])
          with gr.Column():
            generate_btn = gr.Button("Generate", variant="primary")
            generate_btn.click(fn=self.generate_callback, inputs=[source, file_source, categories], outputs=[result])

def on_ui_settings():
  default_tags_categories = ["artist", "species", "character", "general"]
  default_excluded_tags = ", ".join([
    "comic", "watermark", "text", "sign", "patreon_logo", "censored", "censored_genitalia", "censored_penis", "censored_pussy",
    "censored_text", "censored_anus", "multiple_poses", "multiple_images", "dialogue", "speech_bubble", "english_text", "dialogue_box",
  ])

  section = ("e621-prompt", NAME)

  settings_options = [
    ("e621_prompt_username", "", "e621 Username. Not required, but highly preferred"),
    ("e621_prompt_api_key", "", "e621 API Key. Not required, but highly preferred"),
    (
      "e621_prompt_user_agent",
      "sd-webui-e621-prompt (nochnoe)",
      "User-Agent for API calls. DO NOT change this line if you don't know what you're doing"
    ),
    ("e621_prompt_use_proxy", False, "Use proxy when accessing e621"),
    ("e621_prompt_proxy_url", "", "HTTPS proxy"),
    (
      "e621_prompt_included_tags_categories",
      default_tags_categories,
      "Default tag categories to include",
      DropdownMulti,
      lambda: {"choices": tags_categories_options}
    ),
    ("e621_prompt_excluded_tags", default_excluded_tags, "Tags that always should be EXCLUDED from the final result. Comma-separated, with underscores"),
    ("e621_prompt_appended_tags", "", "Tags that always should be APPENDED to the final result. Comma-separated, with underscores"),
    ("e621_prompt_replace_underscores", True, "Replace underscores with spaces"),
    ("e621_prompt_replace_underscores_in_appended", True, "Replace underscores with spaces in the appended tags"),
    ("e621_prompt_artist_prefix", "", "Prefix for artists (for example, artist:)"),
    ("e621_prompt_meta_prefix", "", "Prefix for meta tags (for example, meta:)"),
    ("e621_prompt_species_prefix", "", "Prefix for species tags (for example, species:)"),
    ("e621_prompt_character_prefix", "", "Prefix for characters tags (for example, character:)"),
    ("e621_prompt_lore_prefix", "", "Prefix for lore tags (for example, lore:)"),
    ("e621_prompt_general_prefix", "", "Prefix for general tags (for example, general:)"),
    ("e621_prompt_copyright_prefix", "", "Prefix for copyright tags (for example, copyright:)"),
    ("e621_prompt_rating_prefix", "rating:", "Prefix for rating (for example, rating:)"),
    ("e621_prompt_rating_format", "short", "Rating format (short: e/s/q, full: explicit/safe/questionable)", gr.Dropdown, lambda: {"choices": ["short", "full"]}),
  ]

  for setting_name, *data in settings_options:
    opts.add_option(setting_name, OptionInfo(*data, section=section))

script_callbacks.on_ui_settings(on_ui_settings)
