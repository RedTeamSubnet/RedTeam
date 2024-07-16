import requests

import yaml, copy, base64, io
from PIL import Image
import time
import argparse

def pil_image_to_base64(image: Image.Image, format="JPEG") -> str:
    if format not in ["JPEG", "PNG"]:
        format = "JPEG"
    image_stream = io.BytesIO()
    image = image.convert("RGB")
    image.save(image_stream, format=format)
    base64_image = base64.b64encode(image_stream.getvalue()).decode("utf-8")
    return base64_image

conditional_image = pil_image_to_base64(Image.open("assets/images/image.png"))
MODEL_CONFIGS = yaml.load(
    open("generation_models/configs/model_config.yaml"), yaml.FullLoader
)

nicheimage_catalogue = {
    "GoJourney": {
        "model_incentive_weight": 0.04,
        "supporting_pipelines": MODEL_CONFIGS["GoJourney"]["params"][
            "supporting_pipelines"
        ],
        "reward_type": "custom",
        "timeout": 12,
        "inference_params": {},
    },
    "DreamShaperXL": {
        "model_incentive_weight": 0.06,
        "supporting_pipelines": MODEL_CONFIGS["DreamShaperXL"]["params"][
            "supporting_pipelines"
        ],
        "reward_type": "image",
        "inference_params": {
            "num_inference_steps": 8,
            "width": 1024,
            "height": 1024,
            "guidance_scale": 2,
        },
        "timeout": 16,
    },
    "JuggernautXL": {
        "supporting_pipelines": MODEL_CONFIGS["JuggernautXL"]["params"][
            "supporting_pipelines"
        ],
        "model_incentive_weight": 0.18,
        "reward_type": "image",
        "inference_params": {
            "num_inference_steps": 30,
            "width": 1024,
            "height": 1024,
            "guidance_scale": 6,
        },
        "timeout": 12,
    },
    "RealitiesEdgeXL": {
        "supporting_pipelines": MODEL_CONFIGS["RealitiesEdgeXL"]["params"][
            "supporting_pipelines"
        ],
        "model_incentive_weight": 0.29,
        "reward_type": "image",
        "inference_params": {
            "num_inference_steps": 7,
            "width": 1024,
            "height": 1024,
            "guidance_scale": 5.5,
        },
        "timeout": 12,
    },
    "AnimeV3": {
        "supporting_pipelines": MODEL_CONFIGS["AnimeV3"]["params"][
            "supporting_pipelines"
        ],
        "model_incentive_weight": 0.27,
        "reward_type": "image",
        "inference_params": {
            "num_inference_steps": 25,
            "width": 1024,
            "height": 1024,
            "guidance_scale": 7.0,
            "negative_prompt": "out of frame, nude, duplicate, watermark, signature, mutated, text, blurry, worst quality, low quality, artificial, texture artifacts, jpeg artifacts",
        },
        "timeout": 12,
    },
    "Gemma7b": {
        "supporting_pipelines": MODEL_CONFIGS["Gemma7b"]["params"][
            "supporting_pipelines"
        ],
        "model_incentive_weight": 0.03,
        "timeout": 64,
        "reward_type": "text",
        "inference_params": {},
    },
    "StickerMaker": {
        "supporting_pipelines": MODEL_CONFIGS["StickerMaker"]["params"][
            "supporting_pipelines"
        ],
        "model_incentive_weight": 0.03,
        "timeout": 64,
        "reward_type": "image",
        "inference_params": {"is_upscale": False},
    },
    "FaceToMany": {
        "supporting_pipelines": MODEL_CONFIGS["FaceToMany"]["params"][
            "supporting_pipelines"
        ],
        "model_incentive_weight": 0.03,
        "timeout": 64,
        "reward_type": "image",
        "inference_params": {},
    },
    "Llama3_70b": {
        "supporting_pipelines": MODEL_CONFIGS["Llama3_70b"]["params"][
            "supporting_pipelines"
        ],
        "model_incentive_weight": 0.04,
        "timeout": 128,
        "reward_type": "text",
        "inference_params": {},
    },
    "DallE": {
        "supporting_pipelines": MODEL_CONFIGS["DallE"]["params"][
            "supporting_pipelines"
        ],
        "reward_type": "custom",
        "timeout": 36,
        "inference_params": {},
        "model_incentive_weight": 0.04,
    }
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test validator endpoint')
    parser.add_argument('--n_times', type=int, default=2, help='Number of times to test')
    parser.add_argument(
        "--generate_endpoint",
        type=str,
        help="The endpoint to send generate requests to.",
        default="http://127.0.0.1:13300/generate",
    )
    args = parser.parse_args()

    request_inputs = []
    for model_name, config in nicheimage_catalogue.items():
        if not config["reward_type"] in ["image"]:
            continue
        dt = {
            "prompt": "a cute cat",
            "seed": 0,
            "pipeline_params": config["inference_params"]
        }
        for pipeline_type in config["supporting_pipelines"]:
            dt_cp = copy.deepcopy(dt)
            dt_cp["pipeline_type"] = pipeline_type
            if pipeline_type in ["img2img", "instantid", "controlnet"]:
                dt_cp["conditional_image"] = conditional_image
            req = {
                "model_name": model_name,
                "prompts": [
                    dt_cp
                ]
            }
            request_inputs.append(req)

    request_inputs = request_inputs * args.n_times
    t1 = time.time()
    for req in request_inputs:
        print("Processing: ", req["model_name"], req["prompts"][0]["pipeline_type"])
        res = requests.post(args.generate_endpoint, json = req)
        print("Status code: ", res.status_code)
        assert res.status_code == 200

    print("Total time: ", time.time()-t1)