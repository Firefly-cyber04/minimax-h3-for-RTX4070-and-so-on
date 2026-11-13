# Generate the flat API prompt for H3-Image reference editing (img2img).
#
#   python scripts/make_img2img_prompt.py [--image NAME] [--prompt-file FILE]
#
# Topology mirrors the official template's:
#   LoadImage -> scale total pixels 4MP -> scale to multiple 32 -> GetImageSize
#   -> MiniMaxH3ImageConditioning(images.image_1) -> KSampler -> VAEDecode -> SaveImage
#
# Differences from the official template, all forced by this machine:
#   - DiT is the local GGUF Q3_K_M instead of the 21 GB int8 safetensors
#   - text encoder is the official NVFP4 safetensors on CPU
#   - the prompt-expander branch is removed (6.84 GB expander does not fit in 16 GB
#     of RAM), so the prompt must be written in its already-expanded form
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

UNET = "MiniMax-H3-Image-Pruned-Q3_K_M.gguf"
CLIP = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VAE = "minimax_h3_image_vae_fp16.safetensors"

# Worked example: the three-part expanded caption.
# Part 1 subject definition / Part 2 preservation / Part 3 changed-and-new only.
DEFAULT_PROMPT = (
    "The storefront in <Picture 1> is <Subject 1>. The target image shows <Subject 1> at "
    "night in the rain. <Subject 1> is fully preserved. The daylight sky and dry pavement "
    "of the original are replaced by a heavy rain-soaked night: the sky becomes deep "
    "indigo-black with falling rain streaks, the previously dry cobblestones turn into a "
    "wet mirror throwing long vertical reflections of the shop lights, and the warm interior "
    "glow is joined by a cold blue-white neon sign above the door that casts a cyan wash "
    "across the upper doorframe and the wall to its left."
)

DEFAULT_IMAGE = "reference_bakery.png"
# Shipped as samples/reference_bakery.png - copy it into <ComfyUI>\ComfyUI\input\ before running.


def build(image, prompt, seed=42):
    return {
        "1":  {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": UNET}},
        "2":  {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "minimax", "device": "cpu"}},
        "3":  {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4":  {"class_type": "LoadImage", "inputs": {"image": image, "upload": "image"}},
        "5":  {"class_type": "ResizeImageMaskNode",
               "inputs": {"input": ["4", 0], "resize_type": {"megapixels": 4.0}, "scale_method": "area"}},
        "6":  {"class_type": "ResizeImageMaskNode",
               "inputs": {"input": ["5", 0], "resize_type": {"multiple": 32}, "scale_method": "area"}},
        "7":  {"class_type": "GetImageSize", "inputs": {"image": ["6", 0]}},
        "8":  {"class_type": "MiniMaxH3ImageConditioning",
               "inputs": {"clip": ["2", 0], "vae": ["3", 0],
                          "images": {"image_1": ["6", 0]},
                          "prompt": prompt,
                          "width": ["7", 0], "height": ["7", 1]}},
        "9":  {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["8", 0]}},
        "10": {"class_type": "KSampler",
               "inputs": {"model": ["1", 0], "positive": ["8", 0], "negative": ["9", 0],
                          "latent_image": ["8", 1], "seed": seed, "steps": 6, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage",
               "inputs": {"images": ["11", 0], "filename_prefix": "minimax_h3_image_i2i"}},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=DEFAULT_IMAGE,
                    help="filename of the reference image inside ComfyUI/input")
    ap.add_argument("--prompt-file", default=None,
                    help="file holding the prompt text (default: the worked example below)")
    ap.add_argument("--prompt", default=None, help="prompt text, overrides --prompt-file")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=os.path.join(REPO, "workflows", "api_prompt_img2img.json"))
    args = ap.parse_args()

    if args.prompt:
        prompt = args.prompt
    elif args.prompt_file:
        prompt = open(args.prompt_file, encoding="utf-8").read().strip()
    else:
        prompt = DEFAULT_PROMPT

    api = build(args.image, prompt, args.seed)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(api, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
