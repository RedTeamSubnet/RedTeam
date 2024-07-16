from PIL import Image
from .base_model import BaseModel
import json
from generation_models import ComfyUI
import os
import shutil
from pathlib import Path
import random
import socket
import bittensor as bt

def import_from_string(import_str):
    module_name, class_name = import_str.rsplit(".", 1)
    bt.logging.info(f"Import module: {module_name}")
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)

def check_port_in_use(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return False 
        except socket.error:
            return True 

class NicheComfyUI(BaseModel):
    def load_model(
        self, workflow_json_file, update_wf_function, init_setup_function, **kwargs
    ):
        update_wf_function = import_from_string(update_wf_function)
        init_setup_function = import_from_string(init_setup_function)
        random_port = random.randint(10000, 50000) # For automatic bind port when scale up using Ray
        while check_port_in_use(random_port):
            random_port = random.randint(10000, 50000)
        
        self.comfyui = ComfyUI(random_port)
        init_setup_function(self.comfyui, **kwargs)
        self.output_folder = f"generation_models/comfyui_helper/ComfyUI/output_{random_port}"
        self.input_folder = f"generation_models/comfyui_helper/ComfyUI/input_{random_port}"
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.input_folder, exist_ok=True)
        self.comfyui.start_server(self.output_folder.split("/")[-1], self.input_folder.split("/")[-1])
        workflow = json.load(open(workflow_json_file))
        self.comfyui.load_workflow(workflow)

        def inference_function(*args, **kwargs) -> Image.Image:
            self.cleanup(
                self.comfyui, self.output_folder, self.input_folder
            )
            workflow = json.load(open(workflow_json_file))
            update_wf_function(workflow=workflow, input_folder=self.input_folder, **kwargs)
            wf = self.comfyui.load_workflow(workflow)
            self.comfyui.connect()
            self.comfyui.run_workflow(wf)
            files = []
            output_directories = [self.output_folder]

            for directory in output_directories:
                bt.logging.info(f"Contents of {directory}:")
                files.extend(self.log_and_collect_files(directory))
            bt.logging.info(files)
            image = Image.open(files[0])
            return image

        return inference_function

    def __call__(self, *args, **kwargs):
        image: Image.Image = self.inference_function(*args, **kwargs)
        return image

    def cleanup(self, comfyui, output_folder, input_folder):
        bt.logging.info("Cleanup")
        comfyui.clear_queue()
        for directory in [output_folder, input_folder]:
            if os.path.exists(directory):
                shutil.rmtree(directory)
            os.makedirs(directory)

    def log_and_collect_files(self, directory, prefix=""):
        files = []
        for f in os.listdir(directory):
            if f == "__MACOSX":
                continue
            path = os.path.join(directory, f)
            if os.path.isfile(path):
                bt.logging.info(f"{prefix}{f}")
                files.append(Path(path))
            elif os.path.isdir(path):
                bt.logging.info(f"{prefix}{f}/")
                files.extend(self.log_and_collect_files(path, prefix=f"{prefix}{f}/"))
        return files

    def __del__(self):
        """Destructor to release resources when deleting the object.
        Kills the ComfyUI process on its assigned port, clean data, logs and deletes all attributes of the instance.
        """
        import glob
        self.comfyui.kill_process_on_port()
        for directory in [self.output_folder, self.input_folder]:
            if os.path.exists(directory):
                shutil.rmtree(directory)

        log_file_pattern = os.path.join("generation_models/comfyui_helper/ComfyUI", '*.log')
        log_files = glob.glob(log_file_pattern)
        for log_file in log_files:
            os.remove(log_file)

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            del attr