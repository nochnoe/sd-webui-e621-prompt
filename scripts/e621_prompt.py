import gradio as gr

from modules import scripts, script_callbacks
from modules.shared import opts, OptionInfo

from urllib.request import urlopen
from hashlib import md5
from base64 import b64encode

import re
import requests

NAME = "e621 Prompt"

# List of tags categories. Shared between settings and UI
tags_categories_options = ["general", "species", "character", "copyright", "artist", "invalid", "lore", "meta", "rating"]
default_tags_categories = ["general", "species", "character", "artist"]

# Conditionally replaces underscores
def replace_underscores(value):
  if opts.e621_prompt_replace_underscores:
    return value.replace("_", " ")

  return value

# Escapes some prompt-specific special characters
def escape_special_characters(value):
  return value.replace("(", "\(").replace(")", "\)")

# Converts string of comma-separated values into set
def comma_separated_string_to_set(string):
  return set(filter(None, [s.strip() for s in string.split(",")]))

# Returns set of excluded tags
def excluded_tags():
  return comma_separated_string_to_set(opts.e621_prompt_excluded_tags)

# Returns set of appended tags, replacing underscores if needed
def appended_tags():
  tags = comma_separated_string_to_set(opts.e621_prompt_appended_tags)

  if opts.e621_prompt_replace_underscores_in_appended:
    return set([replace_underscores(tag) for tag in tags])

  return tags

class Script(scripts.Script):
  def title(self):
    return NAME

  def show(self, _is_img2img):
    return scripts.AlwaysVisible

  # Wrapper around requests.request that sets required headers
  def make_request(self, headers={}, **kwargs):
    # Setup headers
    req_headers = {
      "User-Agent": opts.e621_prompt_user_agent
    }

    # Setup auth
    if opts.e621_prompt_username and opts.e621_prompt_api_key:
      req_headers["Authorization"] = b64encode(f"{opts.e621_prompt_username}:{opts.e621_prompt_api_key}".encode())

    # Mix our headers with additional ones
    req_headers.update(headers)

    # Setup proxy
    proxies = None
    if opts.e621_prompt_use_proxy and opts.e621_prompt_proxy_url:
      proxies = {
        "https": opts.e621_prompt_proxy_url
      }

    response = requests.request(**kwargs, headers=req_headers, proxies=proxies)

    response.raise_for_status()

    return response.json()

  # Parse source and extract md5 hash or id
  def normalize_source(self, source):
    if source is None:
      return ("error", "Enter post info")

    found_hash = re.search(r"([a-fA-F\d]{32})", source)

    if found_hash:
      return ("md5", found_hash.group(0))

    found_post_url = re.search(r"e621.net\/posts\/(\d+)", source)

    if found_post_url:
      return ("id", found_post_url.group(1))

    if source.isnumeric():
      return ("id", source)

    return ("error", "No valid post url, id, or md5 hash provided")

  # Fetches post from e621 by md5 or id
  def get_post(self, post_info):
    try:
      match post_info:
        case ("md5", md5):
          json = self.make_request(
            method="GET",
            url="https://e621.net/posts.json",
            params={"tags": f"md5:{md5}", "limit": 1}
          )

          if json["posts"] is None or len(json["posts"]) == 0:
            return ("error", f"No post found for md5 {md5}")

          return ("post", json["posts"][0])
        case ("id", id):
          json = self.make_request(
            method="GET",
            url=f"https://e621.net/posts/{id}.json"
          )

          if json["post"] is None:
            return ("error", f"No post found for id {id}")

          return json["post"]
        case _:
          return post_info
    except Exception as e:
      return ("error", str(e))

  # Formats rating, following the rules and prefixes
  def format_rating(self, post):
    full_map = {
      "e": "explicit",
      "q": "questionable",
      "s": "safe"
    }

    value = post["rating"]

    if opts.e621_prompt_rating_format == "full":
      value = full_map[post["rating"]]

    return f"{opts.e621_prompt_rating_prefix}{value}"

  # Formats tags from category, excluding tags from the settings, adding prefix and replacing underscores if needed
  def format_category(self, post, category):
    prefix = getattr(opts, f"e621_prompt_{category}_prefix")
    tags = set(post["tags"][category] or []) - excluded_tags()

    return set([f"{prefix}{escape_special_characters(replace_underscores(tag))}" for tag in tags])

  # Converts post data into tags
  def process_post(self, post, categories):
    match post:
      case ("error", _):
        return post
      case ("post", p):
        post = p

    result = set()

    for category in categories:
      match category:
        case 'rating':
          result.add(self.format_rating(post))
        case _:
          result = result | self.format_category(post, category)

    result = result | appended_tags()

    return ("result", ", ".join(result))

  # Stitches everything together
  def generate_callback(self, source, categories):
    if not categories:
      return "ERROR: No categories selected"

    result = self.process_post(self.get_post(self.normalize_source(source)), categories)

    match result:
      case ("error", error):
        return f"ERROR: {error}"
      case ("result", prompt):
        return prompt

  # Clears form
  def clear_callback(self):
    return default_tags_categories, None, None, None

  # Calculates hash of the uploaded image, and puts it inside of "source" field
  def image_upload_callback(self, source, image):
    if image is None:
      return source

    with urlopen(image) as response:
      return md5(response.read()).hexdigest()

  # Renders ui
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
          value=default_tags_categories,
          label="Categories"
        )

        result = gr.Textbox(value="", label="Result", lines=5, interactive=False).style(show_copy_button=True)

        with gr.Row():
          with gr.Column():
            clear_btn = gr.Button("Reset form")
            clear_btn.click(fn=self.clear_callback, inputs=None, outputs=[categories, result, source, file_source])
          with gr.Column():
            generate_btn = gr.Button("Generate", variant="primary")
            generate_btn.click(fn=self.generate_callback, inputs=[source, categories], outputs=[result])

    # This return is required, because otherwise "path" in ui_config.json and "Defaults" section of the settings
    # would be really wrong
    return [source, file_source, categories, result, clear_btn, generate_btn]

# Settings section
def on_ui_settings():
  default_excluded_tags = ", ".join([
    "comic", "watermark", "text", "sign", "patreon_logo", "internal", "censored", "censored_genitalia", "censored_penis", "censored_pussy",
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
    ("e621_prompt_invalid_prefix", "", "Prefix for invalid tags (for example, invalid:)"),
    ("e621_prompt_rating_prefix", "rating:", "Prefix for rating (for example, rating:)"),
    ("e621_prompt_rating_format", "short", "Rating format (short: e/s/q, full: explicit/safe/questionable)", gr.Dropdown, lambda: {"choices": ["short", "full"]}),
  ]

  for setting_name, *data in settings_options:
    opts.add_option(setting_name, OptionInfo(*data, section=section))

script_callbacks.on_ui_settings(on_ui_settings)
