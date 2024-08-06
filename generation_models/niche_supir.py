from PIL import Image
from .base_model import BaseModel
from .utils import (
    base64_to_pil_image,
    upscale_image
)
import os
import torch
import sys
import bittensor as bt
import numpy as np
import numpy as np
from huggingface_hub import hf_hub_download, snapshot_download
import copy
import time
import einops
import yaml

class NicheSUPIR(BaseModel):
    def load_model(self, checkpoint_file, supporting_pipelines, **kwargs):
        sys.path.append("generation_models/custom_pipelines/SUPIR")
        from .custom_pipelines.SUPIR.SUPIR.util import HWC3, fix_resize, convert_dtype, create_SUPIR_model, load_QF_ckpt
        
        self.device = "cuda"
        self.supporting_pipelines = supporting_pipelines
        self.max_size_input = 1024

        if not os.path.exists(checkpoint_file):
            os.makedirs(checkpoint_file, exist_ok=True)

            path_clip_bigG = os.path.join(checkpoint_file, "CLIP-ViT-bigG-14-laion2B-39B-b160k")
            path_clip_large = os.path.join(checkpoint_file, "clip-vit-large-patch14")
            path_SUPIR_cache = os.path.join(checkpoint_file, "SUPIR_cache")
            path_SDXL_lightning_cache = os.path.join(checkpoint_file, "SDXL_lightning_cache")
            for path in [path_clip_bigG, path_clip_large, path_SUPIR_cache, path_SDXL_lightning_cache]:
                os.makedirs(path, exist_ok=True)
            snapshot_download(repo_id="openai/clip-vit-large-patch14", local_dir=path_clip_large)
            hf_hub_download(repo_id="laion/CLIP-ViT-bigG-14-laion2B-39B-b160k", filename="open_clip_pytorch_model.bin", local_dir=path_clip_bigG)
            hf_hub_download(repo_id="camenduru/SUPIR", filename="SUPIR-v0Q.ckpt", local_dir=path_SUPIR_cache)

            hf_hub_download(repo_id="RunDiffusion/Juggernaut-XL-Lightning", filename="Juggernaut_RunDiffusionPhoto2_Lightning_4Steps.safetensors", local_dir=path_SDXL_lightning_cache)

        self.opt_file = "generation_models/configs/upscale_config.yaml"
        # Load SUPIR
        self.model, default_setting = create_SUPIR_model(self.opt_file, SUPIR_sign='Q', load_default_setting=True)
        self.model = self.model.half()
    
        self.model.init_tile_vae(encoder_tile_size=512, decoder_tile_size=64)
        self.model.to(self.device)
        self.model.first_stage_model.denoise_encoder_s1 = copy.deepcopy(self.model.first_stage_model.denoise_encoder)
        self.model.current_model = 'v0-Q'
        self.ckpt_Q = load_QF_ckpt(self.opt_file)
        print('load v0-Q')
        self.model.load_state_dict(self.ckpt_Q, strict=False)
        self.model.current_model = 'v0-Q'
        self.config = yaml.load(open(self.opt_file), yaml.FullLoader)

        def stage2_process(input_image, prompt, a_prompt, n_prompt, num_samples, upscale, edm_steps, s_stage1, s_stage2,
                    s_cfg, seed, s_churn, s_noise, color_fix_type, diff_dtype, ae_dtype, gamma_correction,
                    linear_CFG, linear_s_stage2, spt_linear_CFG, spt_linear_s_stage2, model_select, **kwargs):

            input_image = HWC3(input_image)
            input_image = upscale_image(input_image, upscale, max_size_input=self.max_size_input)

            LQ = np.array(input_image) / 255.0
            LQ = np.power(LQ, gamma_correction)
            LQ *= 255.0
            LQ = LQ.round().clip(0, 255).astype(np.uint8)
            LQ = LQ / 255 * 2 - 1
            LQ = torch.tensor(LQ, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0).to(self.device)[:, :3, :, :]
            captions = [prompt]

            self.model.ae_dtype = convert_dtype(ae_dtype)
            self.model.model.dtype = convert_dtype(diff_dtype)

            samples = self.model.batchify_sample(LQ, captions, num_steps=edm_steps, restoration_scale=s_stage1, s_churn=s_churn,
                                            s_noise=s_noise, cfg_scale=s_cfg, control_scale=s_stage2, seed=seed,
                                            num_samples=num_samples, p_p=a_prompt, n_p=n_prompt, color_fix_type=color_fix_type,
                                            use_linear_CFG=linear_CFG, use_linear_control_scale=linear_s_stage2,
                                            cfg_scale_start=spt_linear_CFG, control_scale_start=spt_linear_s_stage2)

            x_samples = (einops.rearrange(samples, 'b c h w -> b h w c') * 127.5 + 127.5).cpu().numpy().round().clip(
                0, 255).astype(np.uint8)
            results = [x_samples[i] for i in range(num_samples)]

            torch.cuda.empty_cache()
            return results[0]
    
        def inference_function(*args, **kwargs) -> Image.Image:
            pipeline_type = kwargs["pipeline_type"]
            if pipeline_type not in self.supporting_pipelines:
                raise ValueError(f"Pipeline type {pipeline_type} is not supported")
            
            input_image = np.array(base64_to_pil_image(kwargs["conditional_image"]))
            
            model_params = self.config["model"]["params"]
            sampler_config = model_params["sampler_config"]["params"]
            kwargs.update({
                "a_prompt": model_params["p_p"],
                "n_prompt": model_params["n_p"],
                "num_samples": 1,
                "upscale": 2,
                "edm_steps": self.config["default_setting"]["edm_steps"],
                "s_stage1": -1.0,
                "s_stage2": 1.0,
                "s_cfg": self.config["default_setting"]["s_cfg_Quality"],
                "s_churn": sampler_config["s_churn"],
                "s_noise": sampler_config["s_noise"],
                "color_fix_type": "Wavelet",
                "diff_dtype": model_params["diffusion_dtype"],
                "ae_dtype": model_params["ae_dtype"],
                "gamma_correction": 1,
                "linear_CFG": True,
                "linear_s_stage2": False,
                "spt_linear_CFG": self.config["default_setting"]["spt_linear_CFG_Quality"],
                "spt_linear_s_stage2": 0.,
                "model_select": "v0-Q"
            })
            
            output = stage2_process(input_image, **kwargs)
            
            if output is None:
                return Image.new("RGB", (512, 512), (255, 255, 255))
            else:
                output = Image.fromarray(output)
            return output

        return inference_function

    