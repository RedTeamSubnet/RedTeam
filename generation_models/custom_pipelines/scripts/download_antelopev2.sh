dest_dir=checkpoints/insightface/models/antelopev2
mkdir -p $dest_dir
wget "https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/1k3d68.onnx?download=true" -P $dest_dir --content-disposition
wget "https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/2d106det.onnx?download=true" -P $dest_dir --content-disposition
wget "https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/genderage.onnx?download=true" -P $dest_dir --content-disposition
wget "https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/glintr100.onnx?download=true" -P $dest_dir --content-disposition
wget "https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/scrfd_10g_bnkps.onnx?download=true" -P $dest_dir --content-disposition
